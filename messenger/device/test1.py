from datetime import datetime, timedelta, timezone
from loramobgate import Device, NetPacket, AppID, ContentType, NetPacketDirection
from time import sleep
from queue import Queue
from typing import Union


class MessagePacket:
    def __init__(self, source_packet=None, **kwargs):
        self.source_packet = source_packet
        self._packet = bytearray()
        self.timestamp = kwargs.get('timestamp', 0)
        self.date = kwargs.get('date', datetime.utcnow().replace(tzinfo=timezone.utc))
        self.flags = kwargs.get('flags', 0)
        self.reply_to = kwargs.get('reply_to', bytes())
        self.forwarded_from = kwargs.get('forwarded_from', 0)
        self.content = kwargs.get('content', "")

        # если это уже готовый пакет и его можно распарсить
        if source_packet and len(source_packet) >= 4 and isinstance(source_packet, bytes):
            self.timestamp = int.from_bytes(source_packet[:3], byteorder = "little")
            self.flags = source_packet[3]
            self.reply_to = source_packet[4:4 + (self.flags & 16)]
            self.forwarded_from = int.from_bytes(source_packet[4:4 + (self.flags & 4)], byteorder="little")
            self.content = source_packet[(4 + (self.flags & 4) + (self.flags & 16)):].decode('utf-8')
            self.date = self.convert_my_timestamp(source_packet[:3])
            self.fragmentation = True if len(source_packet) > 100 else False

        if not self.timestamp:
            self.timestamp = self.convert_my_timestamp(self.date)
        else:
            self.date = self.convert_my_timestamp(self.timestamp)

    @property
    def packet(self):
        self.update()
        return self._packet

    @property
    def hash(self):
        return md5(
            self.date.isoformat()[:19].encode('utf-8') +
            pickle.dumps(self.content.encode('utf-8'))
        ).hexdigest()

    def __str__(self) -> str:
        return ".".join([str(el) for el in self.packet])

    def __setattr__(self, key, value):
        if key == "reply_to" and value:
            self.flags |= 16
            self.flags &= ~4
            if isinstance(value, str):
                self.reply_to = bytes.fromhex(value)
                return

        if key == "forwarded_from" and value:
            self.flags |= 4
            self.flags &= ~16

        self.__dict__[key] = value

    def update(self):
        self._packet = bytearray(int.to_bytes(self.timestamp, 3, byteorder="little"))
        self._packet.extend(int.to_bytes(self.flags, 1, byteorder="little"))
        if self.reply_to and self.flags & 16:
            self.forwarded_from = 0
            self._packet.extend(self.reply_to)
        if self.forwarded_from and self.flags & 4:
            self.reply_to = bytes()
            self._packet.extend(self.forwarded_from.to_bytes(4, byteorder="little"))
        self._packet.extend(self.content.encode('utf-8'))
        if len(self._packet) > 100:
            self.fragmentation = True


    @classmethod
    def convert_my_timestamp(cls, obj: Union[datetime, int]):
        if isinstance(obj, datetime):
            point = datetime.utcnow().replace(tzinfo=timezone.utc)
            value = int((obj - point.replace(hour=0,minute=0,second=0,microsecond=0)).\
                        total_seconds()) * 100 + int(obj.microsecond / 10000)
            return value
        elif isinstance(obj, int):
            timestamp = str(obj)
            new_date = datetime.utcnow().replace(hour = 0, minute = 0, second = 0, microsecond = 0, tzinfo=timezone.utc)
            new_date += timedelta(seconds=int(timestamp[:5]), milliseconds=int(timestamp[5:]) * 10)
            now = datetime.utcnow().replace(tzinfo=timezone.utc)
            if new_date > now:
                new_date = new_date.replace(day = now.day - 1)
            return new_date
        return None



if __name__=="__main__":
    mq = Queue()
    dev = Device(messenger_queue = mq)
    while(True):
        message = MessagePacket(content = f"TEST {datetime.now().isoformat()}")
        net_packet = NetPacket(dst_addr = 0xffffffff, app_id = AppID.MESSENGER, content_type = ContentType.TEXT, 
                               raw_data = message.packet, direction = NetPacketDirection.OUT)
        dev.transmit_data(net_packet)
        print(f"{datetime.now().isoformat()} Message sent!")
        sleep(30)

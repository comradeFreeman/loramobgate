from typing import Iterable
from .classes import ContentType, NetPacketDirection, AppID
from struct import pack, unpack
from hashlib import md5

class NetPacket:
	dev_addr = 0
	def __init__(self, source_packet=None, **kwargs):
		self.source_packet = source_packet
		self._packet = bytearray()
		self.src_addr = kwargs.get('src_addr', self.dev_addr)
		self.dst_addr = kwargs.get('dst_addr', 0xffffffff) # broadcast
		self.fragm_c = kwargs.get('fragm_c', 0)
		self.fragment = kwargs.get('fragment', 0)
		self.app_id = kwargs.get('app_id', AppID.UNKNOWN)
		self.content_type = kwargs.get('content_type', ContentType.UNKNOWN)
		self.raw_data = kwargs.get('raw_data', bytes())
		self.pydc = kwargs.get('pydc', len(self.raw_data) + 1)
		self.direction = kwargs.get('direction', NetPacketDirection.IN)

		if source_packet and isinstance(source_packet, Iterable):
			self.src_addr, self.dst_addr, self.fragm_c, self.fragment, self.app_id, self.pydc, self.content_type = \
				unpack("<2I5B", bytes(source_packet[:13]))
			self.raw_data = bytes(source_packet[13:13 + self.pydc])
			self.update()

	def __str__(self) -> str:
		return ".".join([str(el) for el in self.packet])

	def __eq__(self, other) -> bool:
		if isinstance(other, NetPacket):
			return self.packet == other.packet
		return False

	def __hash__(self) -> int:
		return hash(str(self.packet))

	@property
	def hashsum(self) -> bytes:
		return md5(self.packet).digest()

	def __setattr__(self, key, value):
		if key == "content_type" and not isinstance(value, ContentType):
			value = ContentType(value)
		elif key == "app_id" and not isinstance(value, AppID):
			value = AppID(value)
		elif key == "raw_data" and not isinstance(value, bytes):
			value = bytes(value)
			self.pydc = len(value) + 1

		self.__dict__[key] = value

	@property
	def is_default(self) -> bool:
		return not (set(self.packet) == {255, self.dev_addr})
	# проверяет, что это пустой пакет и создан с нуля без аргументов.

	@property
	def is_valid(self) -> bool:
		return self.content_type.value // 10 == self.app_id.value and \
			   self.pydc == len(self.raw_data) + 1 and \
			   self.content_type != ContentType.INVALID and \
			   self.app_id != AppID.INVALID # encrypted_data
	# проверяет, что пакет, созданный из набора байт, является валидным. Грубый способ отделить LoRa

	@property
	def packet(self):# -> list:
		if self.is_valid:
			# если мы успешно спарсили пакет и это пакет нашего формата
			self.update()
			return bytes(self._packet)
		elif self.source_packet:
			# иначе отдаём то, что пришло изначально пришло на вход
			return self.source_packet
		else:
			return bytes() #[]


	@property
	def dict(self) -> dict:
		return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}

	@property
	def is_fragmented(self) -> bool:
		return bool(self.fragm_c)

	def update(self):
		self._packet = bytearray(pack(f"<2I5B", self.src_addr, self.dst_addr, self.fragm_c, self.fragment,
									  self.app_id.value, self.pydc, self.content_type.value))
		self._packet.extend(self.raw_data) # encrypted_data

	def swap_addr(self, from_me = False):
		# меняем местами адреса источника и назначения.
		# если задан адрес этого устройства, то подставляем его в источник
		self.src_addr, self.dst_addr = self.dev_addr if from_me else self.dst_addr, self.src_addr

	def swap_direction(self):
		self.direction = NetPacketDirection(not self.direction.value)

	def duplicate(self):
		return NetPacket(source_packet = self.packet, direction = self.direction)
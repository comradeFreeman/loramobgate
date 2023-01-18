import sys
import os
import traceback
sys.path.insert(0, os.path.join(os.path.dirname(__file__) ,"device"))
import settings
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDTextButton, MDFlatButton, MDRaisedButton, MDRectangleFlatIconButton
from kivymd.uix.label import MDLabel
from kivy.properties import NumericProperty, StringProperty, ListProperty, ObjectProperty
from kivymd.uix.card import MDCard
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.toolbar.toolbar import ActionTopAppBarButton
from kivy.uix.behaviors import ButtonBehavior
from kivy.lang import Builder
from datetime import datetime, timezone
from kivy.core.window import Window
from kivy.metrics import sp,dp, dpi2px
from kivy.utils import platform
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.list import OneLineAvatarIconListItem, IRightBodyTouch
from kivymd.uix.bottomsheet import MDListBottomSheet
import json
from itertools import groupby
from kivy.core.clipboard import Clipboard
from kivymd.uix.dialog import MDDialog
from typing import Union

from audiostream import get_input
from time import sleep
from datetime import datetime, timedelta
from typing import Iterable


from loramobgate import UsbConnection, Device, InternetConnection, NetPacket, RepeatTimer
from models import Message, Content, Chat, db
from classes import ContentType, AppID, NetPacketDirection

import usb.util as u
import declarations as s

import queue
from hashlib import md5
from math import ceil

#from zoneinfo import ZoneInfo
#utc = ZoneInfo('UTC')

localtz = datetime.now().astimezone().tzinfo

if platform == "android":
    from android.permissions import request_permissions, Permission
    request_permissions([Permission.WRITE_EXTERNAL_STORAGE,
                         Permission.READ_EXTERNAL_STORAGE,
                         Permission.RECORD_AUDIO,
                         Permission.INTERNET])
    import usb4a.usb
    #localtz = datetime.now().astimezone().tzinfo
else:
    import usb.core
    #localtz = ZoneInfo('localtime')


class MessagePacket:  # тут будет формирование и хранение сообщений для/с устройства по формату
    def __init__(self, source_packet=None, **kwargs):
        self.source_packet = source_packet
        self._packet = bytearray()
        self.timestamp = kwargs.get('timestamp', 0)
        self.date = kwargs.get('date', datetime.utcnow().replace(tzinfo=timezone.utc))
        self.flags = kwargs.get('flags', 0)
        self.reply_to = kwargs.get('reply_to', bytes())
        self.forwarded_from = kwargs.get('forwarded_from', 0)
        self.content = kwargs.get('content', "")
        self.fragmentation = kwargs.get('fragmentation', False)

        # если это уже готовый пакет и его можно распарсить
        if source_packet and len(source_packet) >= 4 and isinstance(source_packet, Union[bytes, bytearray]):
            self.timestamp = int.from_bytes(source_packet[:3], byteorder = "little")
            self.flags = source_packet[3]
            self.reply_to = source_packet[4:4 + (self.flags & 16)]#.decode('utf-8')
            self.forwarded_from = int.from_bytes(source_packet[4:4 + (self.flags & 4)], byteorder="little")
            self.content = source_packet[(4 + (self.flags & 4) + (self.flags & 16)):].decode('utf-8')
            self.date = self.convert_my_timestamp(source_packet[:3])
            self.fragmentation = True if len(source_packet) > 100 else False


        if not self.timestamp:
            self.timestamp = self.convert_my_timestamp(self.date)
        else:
            self.date = self.convert_my_timestamp(self.timestamp)

    @property
    def packet(self):# -> list:
        self.update()
        return self._packet

    @property
    def fragmentation_needed(self):
        return self.fragmentation

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
            self._packet.extend(self.reply_to) #.encode('utf-8'))
        if self.forwarded_from and self.flags & 4:
            self.reply_to = bytes()
            self._packet.extend(self.forwarded_from.to_bytes(4, byteorder="little"))
        self._packet.extend(self.content.encode('utf-8'))
        if len(self._packet) > 100:
            self.fragmentation = True

    @classmethod
    def convert_my_timestamp(cls, obj: Union[datetime, int]):
        if isinstance(obj, datetime):
            point = datetime.utcnow()#.replace(tzinfo=utc)
            value = int((point - point.replace(hour=0,minute=0,second=0,microsecond=0)).\
                        total_seconds()) * 100 + (point.microsecond % 100)
            return value #value.to_bytes(length=3, byteorder="big")
        elif isinstance(obj, int):#Union[bytes, bytearray]):
            timestamp = str(obj) #int.from_bytes(obj, byteorder='big')
            new_date = datetime.utcnow().replace(hour = 0, minute = 0, second = 0, microsecond = 0)#, tzinfo=utc)
            new_date += timedelta(seconds=int(timestamp[:-2]), milliseconds=(int(timestamp) % 100) * 10)
            now = datetime.utcnow()#.replace(tzinfo=utc)
            if new_date > now:
                new_date = new_date.replace(day = now.day - 1)
            return new_date
        return None


class MessengerRoot(MDScreen):
    def __init__(self, **kwargs):
        self.dev_addr = app.dev_addr
        super(MessengerRoot, self).__init__(**kwargs)
        self.delete_dialog = None
        message_actions = [
            { "viewclass": "Item", "text": "Reply", "left_icon": "message-reply", "height": dp(48),
              "on_release": lambda: self.message_actions_callback("reply"), },
            { "viewclass": "Item", "text": "Copy", "left_icon": "content-copy", "height": dp(48),
              "on_release": lambda: self.message_actions_callback("copy"), },
            { "viewclass": "Item", "text": "Forward", "left_icon": "forward", "height": dp(48),
              "on_release": lambda: self.message_actions_callback("forward"), },
            # { "viewclass": "Item", "text": "Edit", "left_icon": "note-edit", "height": dp(48),
            #   "on_release": lambda: self.message_actions_callback("edit"), },
            { "viewclass": "Item", "text": "Delete", "left_icon": "delete", "height": dp(48),
              "on_release": lambda: self.message_actions_callback("delete"), }

        ]
        chat_actions = [
            { "viewclass": "Item", "text": "Search", "left_icon": "magnify", "height": dp(48),
              "on_release": lambda: self.chat_actions_callback("search",
                            self.ids.screen_manager.get_screen("chat_screen").current_chat), },
            { "viewclass": "Item", "text": "Search date", "left_icon": "calendar", "height": dp(48),
              "on_release": lambda: self.chat_actions_callback("search_date",
                            self.ids.screen_manager.get_screen("chat_screen").current_chat), },
            { "viewclass": "Item", "text": "Change theme", "left_icon": "brush", "height": dp(48),
              "on_release": lambda: self.chat_actions_callback("theme",
                            self.ids.screen_manager.get_screen("chat_screen").current_chat), },
            { "viewclass": "Item", "text": "Delete chat", "left_icon": "delete", "height": dp(48),
              "on_release": lambda: self.chat_actions_callback("delete",
                            self.ids.screen_manager.get_screen("chat_screen").current_chat), },
        ]
        self.message_actions_menu = MDDropdownMenu(
            items = message_actions,
            width_mult = 4,
            max_height=0,
            elevation=4,
            opening_time=0.2
        )
        self.chat_actions_menu = MDDropdownMenu(
            items = chat_actions,
            width_mult = 5,
            max_height=0,
            elevation=4,
            opening_time=0.2
        )

    def load_chats(self, caller):
        self.ids.chats_container.clear_widgets()
        for chat in Chat.select().order_by(Chat.last_message_id.desc()):
            last_message: Message = Message.get_or_none(Message.id == chat.last_message_id)
            self.ids.chats_container.add_widget(ChatCard(
                chat = chat.id,
                display_name = chat.display_name,
                message = last_message.content.get().content.decode('utf-8') if last_message else "",
                avatar = chat.avatar,
                time = last_message.date_received.strftime("%H:%M"
                if last_message.date_received.day == datetime.utcnow().day
                else "%d %b") if last_message else "",
                unread = chat.unread,
                screen_manager = self.ids.screen_manager
            ))

    def load_messages(self, caller, page=1, count=10):
        print("load")
        current_chat = self.ids.screen_manager.get_screen("chat_screen").current_chat
        chat = Chat.get_or_create(id = current_chat,
                                  defaults={"participants": {self.dev_addr: self.dev_addr,
                                                             current_chat: current_chat},
                                            "id": current_chat,
                                            "display_name": hex(current_chat)})[0]
        if isinstance(caller, MDScreen):
            self.ids.messages_container.clear_widgets()
            #self.ids.messages_container.add_widget(LoadPreviousPane(on_release=self.load_messages))
            self.ids.messages_container.add_widget(MDLabel()) # заглушка, относительно которой цепляются другие виджеты
            chat.unread = 0
            chat.save()
        else:
            self.ids.screen_manager.get_screen("chat_screen").current_page += 1
        current_page = self.ids.screen_manager.get_screen("chat_screen").current_page
        messages = chat.messages.select().order_by(Message.date_received.desc()).paginate(current_page, count)
        self.ids.toolbar_chat.title = chat.display_name
        for date, grouped_by_day in groupby(messages, key=lambda msg: msg.date_received.date()):
            top_headers = [el for el in self.ids.messages_container.children if isinstance(el, ChatDateHeader)]
            if top_headers and top_headers[0].ids.content.date == date:
                self.ids.messages_container.remove_widget(top_headers[0])
            for message in grouped_by_day:
                self.draw_message(message)
            self.ids.messages_container.add_widget(ChatDateHeader(date = date), -1)


    def calc_width(self, len_text):
        factor = sp(12) * len_text / self.width
        reply_symbols = int(self.width * factor / sp(15))
        if factor <= .9:
            return factor, reply_symbols
        else:
            return .75, reply_symbols

    def draw_message(self, message: Message, pos = -1):
        message_header = ""
        message_content_obj = message.content.get()
        if message_content_obj.ready:
            message_content = message_content_obj.content.decode('utf-8')
            card = MessageCardRight if message.sender == self.dev_addr else MessageCardLeft
            preferred_factor, reply_symbols = self.calc_width(len(message_content))
            if r:= message.reply_to:
                message_header = f"[ref=replied][b]> {message.chat.participants[Message.get(Message.id == r).sender]}[/b]\n" \
                                 f"[i]> {Message.get(Message.id == r).content.get().content.decode('utf-8')[:reply_symbols]}...[/i][/ref]\n\n"
            elif f:= message.forwarded_from:
                message_header = f"Forwarded from [b] {f}[/b]\n\n"
            #message.date_received = message.date_received.astimezone(localtz))
            self.ids.messages_container.add_widget(card(
                message_header = message_header,
                message_content = message_content,
                #time = (message.date_received.astimezone(localtz)).strftime("%H:%M"),
                full_date = (message.date_received.astimezone(localtz)),
                size_hint_x = preferred_factor,
                message_actions_menu = self.message_actions_menu,
                reply_to = message.reply_to,
                forwarded_from = message.forwarded_from,
                messages_scroll = self.ids.messages_scroll,
                id = message.id
            ), pos)


    # def on_text(self, text):
    #     if text: self.ids.send_message.icon = "send"
    #     else: self.ids.send_message.icon = "microphone-plus"

    def message_actions_callback(self, action):
        self.message_actions_menu.dismiss()
        if action == "reply":
            if not [c for c in self.ids.chat_area.children if isinstance(c, ReplyMessagePane)]:
                #(self.ids.chat_area.children) == 1: # упрощение. там должен быть только скролбокс, отсюда и пляшем
                self.ids.chat_area.add_widget(ReplyMessagePane(text = self.message_actions_menu.caller.message_content,
                                                               msgid = self.message_actions_menu.caller.id))
        elif action == "copy":
            Clipboard.copy(self.message_actions_menu.caller.message_content)
        elif action == "forward":
            forward_menu = MDListBottomSheet()
            with open('assets/test/data/chats.json') as f_obj:
                chats = json.load(f_obj)
            for chat in chats.keys():
                forward_menu.add_item(f"{chats[chat]['display_name']} ({chat})", lambda x, y=chat: self.forward_actions_callback(y))
            forward_menu.open()
            # case "edit":
            #     pass
        elif action == "delete":
            self.delete_dialog = MDDialog(
                title="Delete message?",
                text="This message will be deleted forever and it would be impossible to recover it since messages are stored only on clients devices!",
                type="alert",
                buttons=[
                    MDRaisedButton(text="CANCEL", on_release=self.delete_message),
                    MDFlatButton(text="DELETE", on_release=self.delete_message),
                ],
            )
            self.delete_dialog.open()
            #TODO remove affected replied messages bindings
        #print(action, self.message_actions_menu.caller)
        #print(self.message_actions_menu.caller.ids.message.text)

    def delete_message(self, caller):
        if caller.text == "DELETE" and (widgets:= [el for el in self.ids.messages_container.children if el.id == self.message_actions_menu.caller.id]):
            self.ids.messages_container.remove_widget(widgets[0])
        self.delete_dialog.dismiss()

    def chat_actions_callback(self, action, chat):
        self.chat_actions_menu.dismiss()
        print(action, chat)

    def chat_actions_menu_callback(self, caller):
        self.chat_actions_menu.caller = caller
        self.chat_actions_menu.open()

    def forward_actions_callback(self, chat):
        print(chat)

    def record_audio_message(self, data):
        self.ids.messages_container.add_widget(ChatDateHeader(date = len(data))) # TODO

    def send(self, reply_to = 0, forwarded_from = 0):
        if content := self.ids.input_field.text:
            self.ids.input_field.text = ""
            current_chat = self.ids.screen_manager.get_screen("chat_screen").current_chat
            if _:= [c for c in self.ids.chat_area.children if isinstance(c, ReplyMessagePane)]:
                reply_to = _[0].msgid
            if chat:= Chat.get_or_none(Chat.id == current_chat):
                m = Message.create(sender = self.dev_addr, recipient = current_chat, forwarded_from = forwarded_from,
                                   reply_to = reply_to, chat = chat, message_hash = md5(content.encode('utf-8')).hexdigest())
                c = Content.create(message = m, content_type = ContentType.TEXT, content = content.encode('utf-8')) # TODO?
                m.save()
                c.save()
                if Message.get(chat.last_message_id).date_received.day != m.date_received.day:
                    self.ids.messages_container.add_widget(ChatDateHeader(date = m.date_received))
                chat.last_message_id = m.get_id()
                chat.save()
                self.draw_message(m, pos=0)
                app.send_message(m.get_id())
        else:
            pass
            # micro

        # mic = get_input(callback=self.record_audio_message)
        # mic.start()


    def scroll_bottom(self, caller):
        if self.ids.messages_container.children:
            self.ids.messages_scroll.scroll_to(self.ids.messages_container.children[0])

    def new_chat(self, caller):
        print(self.ids.new_chat_id.text)
        self.ids.screen_manager.get_screen("chat_screen").current_chat = int(self.ids.new_chat_id.text)
        self.ids.screen_manager.get_screen("chat_screen").current_page = 1
        self.ids.screen_manager.current = "chat_screen"



class ChatCard(MDCard, ButtonBehavior):
    chat = NumericProperty(0xffffffff)
    display_name = StringProperty("Anonymous")
    message = StringProperty("Message")
    avatar = StringProperty()
    time = StringProperty("01.01.1970")
    unread = NumericProperty(1)
    screen_manager = ObjectProperty()


    def open_chat(self, caller):
        self.screen_manager.get_screen("chat_screen").current_chat = caller.chat
        self.screen_manager.get_screen("chat_screen").current_page = 1
        self.screen_manager.current = "chat_screen"


class MessageCardBase(MDCard, ButtonBehavior):
    size_hint_x = NumericProperty()
    message_header = StringProperty()
    message_content = StringProperty()
    #time = StringProperty()
    full_date = ObjectProperty()
    message_actions_menu = ObjectProperty()
    #
    reply_to = NumericProperty()
    forwarded_from = NumericProperty()
    messages_scroll = ObjectProperty()
    id = NumericProperty()

    def messagecard_callback(self, caller):
        self.message_actions_menu.caller = caller
        self.message_actions_menu.open()

    def scroll_replied(self, caller: MDLabel):
        try:
            self.messages_scroll.scroll_to([c for c in self.parent.children if c.id == caller.reply_to][0])
        except:
            pass


class MessageCardLeft(MessageCardBase):
    pass
class MessageCardRight(MessageCardBase):
    pass


class ReplyMessagePane(MDBoxLayout):
    text = StringProperty()
    msgid = NumericProperty()


class ChatDateHeader(MDBoxLayout):
    date = ObjectProperty()
    #text = StringProperty()

class LoadPreviousPane(MDRectangleFlatIconButton):
    text = "Load previous messages"
    icon = "message-text-clock"
    pos_hint = {"center_x": .5}

class RightContentCls(IRightBodyTouch, MDBoxLayout):
    icon = StringProperty()
    text = StringProperty()


class Item(OneLineAvatarIconListItem):
    left_icon = StringProperty()
    right_icon = StringProperty()
    right_text = StringProperty()


class MessengerApp(MDApp):
    def __init__(self, **kwargs):
        super(MessengerApp,self).__init__(**kwargs)
        Window.bind(on_keyboard = self.keyboard_events)
        Window.softinput_mode = "pan"

        self._messenger_queue = queue.Queue()
        self._process_delay = settings.PROCESS_DELAY
        self._inet = InternetConnection()
        self._device: Device = None
        self._check_msg_thread = RepeatTimer(self._process_delay, self._process_messages)
        #
        # self._ui_queue = queue.Queue
        # self._ui_monitor_thread = RepeatTimer(self._process_delay, self._ui_monitor)
        # self._ui_monitor_thread.start()

    @property
    def dev_addr(self):
        return self._device.dev_addr if self._device else 0xabcdf987 #0xacde73bf #None # TODO подумать

    def on_start(self):
        Builder.load_file('chatcard.kv')
        Builder.load_file('messagecard.kv')
        self.root.load_chats(None)
        self._device = Device(messenger_queue = self._messenger_queue, inet = self._inet)
        self._check_msg_thread.start()

    def on_stop(self):
        print("1")
        self._check_msg_thread.cancel()
        print("2")
        self._device.stop()
        print("999")
        db.close()
        sys.exit(0)


    def do(self, caller: ActionTopAppBarButton):
        print(caller)
        a: MDTopAppBar = self.root.ids.toolbar_messenger
        print(a.right_action_items)
        print(type(a.right_action_items))

    def do2(self, caller):
        connection = UsbConnection()
        if connection:
            self.root.ids.settings_label1.text = f"{self._device.send_command(command=s.USB_GET_MODULE)}"
        self.root.ids.settings_label2.text = f"{sys.path}"
        self.root.ids.settings_label3.text = f"{self._device.dev_addr}"
        self.root.ids.settings_label5.text = f"{self._device.dev_info}"

    # def do3(self, caller):
    #     if sum(caller.vbar) == 1.0:
    #         self.root.


    def open_chat(self, caller):
        self.root.current_chat = caller.chat
        #self.root.ids.screen_manager.get_screen("chat_screen").current_chat = str(caller.chat)
        self.root.ids.screen_manager.current = "chat_screen"

    def keyboard_events(self, window, key, *largs):
        #if self.manager_open and key in (1001, 27):
        #    self.file_manager.back()
        if key == 27: #elif
            self.root.ids.screen_manager.current = "messenger_screen"
        return True

    # def _ui_monitor(self):
    #     try:
    #         while not self._ui_queue.empty():
    #             pass
    #     except:
    #         print(traceback.format_exc())

    def send_message(self, msg_id: int):
        message_db: Message = Message.get(Message.id == msg_id)
        message_rp = None
        if message_db.reply_to:
            message_rp = Message.get_or_none(Message.id == message_db.reply_to)
        message = MessagePacket(reply_to = message_rp.message_hash if message_rp else "",
                                forwarded_from = message_db.forwarded_from,
                                content = message_db.content.get().content.decode('utf-8'))
        #self._device.transmit_data(
        #if encrypted:= self._device.encrypt(message_db.recipient, message.packet):
        #if message.fragmentation_needed:
        parts = ceil(len(message.packet) / 100) if len(message.packet) > 100 else 0
        for i, j in enumerate(range(0, len(message.packet), 100)):
            a = NetPacket(dst_addr = message_db.recipient, fragm_c = parts, fragment = i,
                          app_id = AppID.MESSENGER, content_type = ContentType.TEXT,
                          direction = NetPacketDirection.OUT, raw_data = message.packet[j:j+100])
            print("send_message fragment", a.packet)
            self._device.add_packet(a)
        #TODO

    def _process_messages(self):
        try:
            while not self._messenger_queue.empty():
                packet: NetPacket = self._messenger_queue.get()
                #if packet.dst_addr == settings.BROADCAST:

                # TODO А что если сделать два подтипа пакета сообщения: который получен из Лоры и который получен из сети
                # Тогда в последнем случае можно было бы добавить дополнительную информацию (время отправки или "ответ_на")
                # Хотя это усложняет пакет, причём очень сильно
                print(packet.packet)
                #if decrypted:= self._device.decrypt(packet.src_addr, packet.raw_data):
                message = MessagePacket(source_packet = packet.raw_data)#decrypted)
                    #flags = decrypted[3]
                    #data = decrypted[(3 + (flags & 4) + (flags & 16)):]
                chat = Chat.get_or_create(id = packet.src_addr,
                                              defaults={"participants": {packet.src_addr: packet.src_addr,
                                                                         packet.dst_addr: packet.dst_addr},
                                                        "id": packet.src_addr,
                                                        "display_name": str(packet.src_addr)})[0] # TODO read docs
                m = Message.create(sender = packet.src_addr, recipient = packet.dst_addr, date_sent = message.date,
                                       forwarded_from = message.forwarded_from, reply_to = message.reply_to, chat = chat,
                                       message_hash = md5(message.content.encode('utf-8')).hexdigest())
                c = Content.create(message = m, content_type = packet.content_type, content = message.content.encode('utf-8')) # TODO?
                m.save()
                c.save()
                if m.recipient == self.dev_addr:
                    chat.unread += 1
                chat.last_message_id = m.get_id()
                chat.save()
                if self.root.ids.screen_manager.get_screen("chat_screen").current_chat == chat.id:
                    self.root.draw_message(m, pos=0)


                #else: # если мы отправителя/получателя не знаем, то выше отправлен сразу запрос ключа, а этот пакет складываем в конец
                #    self._messenger_queue.put(packet)

        except Exception:
            print(traceback.format_exc())


if __name__ == "__main__":
    app = MessengerApp()
    app.run()


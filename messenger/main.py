import pickle
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
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.snackbar import Snackbar
from typing import Union
from kivy.clock import Clock

from audiostream import get_input
from time import sleep
from datetime import datetime, timedelta
from typing import Iterable
from kivy.core.text import FontContextManager

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
    request_permissions([Permission.INTERNET,
                         Permission.ACCESS_NETWORK_STATE,
                         Permission.ACCESS_WIFI_STATE,
                         Permission.WRITE_EXTERNAL_STORAGE,
                         Permission.READ_EXTERNAL_STORAGE,
                         Permission.RECORD_AUDIO])
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

        # если это уже готовый пакет и его можно распарсить
        if source_packet and len(source_packet) >= 4 and isinstance(source_packet, bytes):
            self.timestamp = int.from_bytes(source_packet[:3], byteorder = "little")
            self.flags = source_packet[3]
            self.reply_to = source_packet[4:4 + (self.flags & 16)]#.decode('utf-8')
            self.forwarded_from = int.from_bytes(source_packet[4:4 + (self.flags & 4)], byteorder="little")
            self.content = source_packet[(4 + (self.flags & 4) + (self.flags & 16)):].decode('utf-8')
            self.date = self.convert_my_timestamp(source_packet[:3])
            self.fragmentation = True if len(source_packet) > 100 else False
            print("Repl_to: ", self.reply_to.hex())

        if not self.timestamp:
            self.timestamp = self.convert_my_timestamp(self.date)
        else:
            self.date = self.convert_my_timestamp(self.timestamp)

    @property
    def packet(self):# -> list:
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
            point = datetime.utcnow().replace(tzinfo=timezone.utc)
            print("point ", point, point.microsecond / 10000)
            print("obj", obj)
            value = int((obj - point.replace(hour=0,minute=0,second=0,microsecond=0)).\
                        total_seconds()) * 100 + int(obj.microsecond / 10000)
            print("dt to timestamp: ", obj, value)
            return value #value.to_bytes(length=3, byteorder="big")
        elif isinstance(obj, int):#Union[bytes, bytearray]):
            timestamp = str(obj) #int.from_bytes(obj, byteorder='big')
            new_date = datetime.utcnow().replace(hour = 0, minute = 0, second = 0, microsecond = 0, tzinfo=timezone.utc)
            new_date += timedelta(seconds=int(timestamp[:5]), milliseconds=int(timestamp[5:]) * 10)
            now = datetime.utcnow().replace(tzinfo=timezone.utc)
            print(new_date, now)
            if new_date > now:
                new_date = new_date.replace(day = now.day - 1)
            print("timestamp to dt: ", str(obj), new_date)
            return new_date
        return None


class MessengerRoot(MDScreen):
    def __init__(self, **kwargs):
        self.dev_addr = None
        super(MessengerRoot, self).__init__(**kwargs)
        self.delete_dialog = None
        #self.list_chats_changed = True
        self.action_msg_id = None
        message_actions = [
            { "viewclass": "Item", "text": "Reply", "left_icon": "message-reply", "height": dp(48),
              "on_release": lambda: self.message_actions_callback("reply"), },# ,
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
        Clock.schedule_interval(lambda x: self.load_messages(load_new=True), settings.LOAD_MESSAGES_PERIOD)
        Clock.schedule_interval(lambda x: self.load_chats(), settings.LOAD_CHATS_PERIOD)

    def load_chats(self, caller = None, force = False):
        chats_db = Chat.select().order_by(Chat.last_message_id.desc())
        if not self.ids.chats_container.children or force:
            self.ids.chats_container.clear_widgets()
            for chat in chats_db:
                last_message: Message = Message.get_or_none(Message.id == chat.last_message_id)
                self.ids.chats_container.add_widget(ChatCard(
                        chat = chat.id,
                        display_name = chat.display_name,
                        message = last_message.content.get().content.decode('utf-8') if last_message else "",
                        avatar = chat.avatar,
                        time = last_message.date_received.astimezone(localtz).strftime("%H:%M"
                        if last_message.date_received.day == datetime.utcnow().day
                        else "%d %b") if last_message else "",
                        unread = chat.unread,
                        screen_manager = self.ids.screen_manager,
                        last_message_id = chat.last_message_id or -1
                    ))
        else:
            changed = []
            for chat_db in chats_db:
                if chat_ui:= [el for el in self.ids.chats_container.children if el.chat == chat_db.id]:
                    chat_ui = chat_ui[0]
                    chat_ui.unread = chat_db.unread
                    if (chat_ui.last_message_id != chat_db.last_message_id) and (last_message:= Message.get_or_none(Message.id == chat_db.last_message_id)):
                        chat_ui.last_message_id = chat_db.last_message_id
                        if last_message.content.get().ready:
                            chat_ui.message = last_message.content.get().content.decode('utf-8')
                        chat_ui.time = last_message.date_received.astimezone(localtz).strftime("%H:%M" if last_message.date_received.day == datetime.utcnow().day else "%d %b")
                        #chat_ui.unread = chat_db.unread
                    if self.ids.chats_container.children.index(chat_ui) != list(chats_db)[::-1].index(chat_db): # разница в нумерации
                        changed.append(chat_ui)
                else:
                    pos = -1 - len([chat for chat in self.ids.chats_container.children if chat.last_message_id > chat_db.id])
                    last_message: Message = Message.get_or_none(Message.id == chat_db.last_message_id)
                    self.ids.chats_container.add_widget(ChatCard(
                        chat = chat_db.id,
                        display_name = chat_db.display_name,
                        message = last_message.content.get().content.decode('utf-8') if last_message else "",
                        avatar = chat_db.avatar,
                        time = last_message.date_received.astimezone(localtz).strftime("%H:%M"
                                                                                       if last_message.date_received.day == datetime.utcnow().day
                                                                                       else "%d %b") if last_message else "",
                        unread = chat_db.unread,
                        screen_manager = self.ids.screen_manager,
                        last_message_id = chat_db.last_message_id or -1
                    ), pos)
                    # TODO test
                    #self.load_chats(force=True)

            # print(changed)
            for item in changed[::-1]: # начинаем с добавления наверх "более" старых новых сообщений
                self.ids.chats_container.remove_widget(item)
                self.ids.chats_container.add_widget(item, -1)


    def load_messages(self, caller = None, page=1, count=10, load_new = False):
        current_chat = self.ids.screen_manager.get_screen("chat_screen").current_chat
        if current_chat:
            chat = Chat.get_or_create(id = current_chat,
                                      defaults={"participants": {self.dev_addr: self.dev_addr,
                                                                 current_chat: current_chat},
                                                "id": current_chat,
                                                "display_name": hex(current_chat)})[0]
            if isinstance(caller, MDScreen):
                self.ids.messages_container.clear_widgets()
                #self.ids.messages_container.add_widget(LoadPreviousPane(on_release=self.load_messages))
                self.ids.messages_container.add_widget(MDLabel()) # заглушка, относительно которой цепляются другие виджеты
                self.ids.toolbar_chat.title = chat.display_name
                chat.unread = 0
                chat.save()
            else:
                self.ids.screen_manager.get_screen("chat_screen").current_page += 1
            current_page = self.ids.screen_manager.get_screen("chat_screen").current_page

            if load_new: # load new
                if last_shown_messages:= [el for el in self.ids.messages_container.children if isinstance(el, MessageCardBase)]:
                    for message in Message.select().where((Message.id > last_shown_messages[0].id) & (Message.chat == current_chat)):
                       self.draw_message(message, pos = 0)
            else: # load previous
                messages = chat.messages.select().order_by(Message.date_received.desc()).paginate(current_page, count)
                for date, grouped_by_day in groupby(messages, key=lambda msg: msg.date_received.date()):
                    top_headers = [el for el in self.ids.messages_container.children if isinstance(el, ChatDateHeader)]
                    if top_headers and top_headers[0].ids.content.date == date:
                        self.ids.messages_container.remove_widget(top_headers[0])
                    for message in grouped_by_day:
                        self.draw_message(message)
                    self.ids.messages_container.add_widget(ChatDateHeader(date = date), -1)


    def calc_width(self, len_text):
        #print(self.width, len_text)
        factor = (sp(12) * len_text + (90 if platform == "android" else 30))/ self.width
        reply_symbols = int((self.width - 6*sp(12)) * factor / sp(12))
        if factor <= .9:
            return factor, reply_symbols
        else:
            return .75, reply_symbols

    def draw_message(self, message: Message, pos = -1):
        # TODO определить тип сообщения и уже в зависимости от типа его рисовать
        message_header = ""
        message_content_obj = message.content.get()
        if message_content_obj.ready:
            #message_content = f"[font=Roboto-Regular-Emoji]{message_content_obj.content.decode('utf-8')}[/font]"
            message_content = message_content_obj.content.decode('utf-8')
            card = MessageCardRight if message.sender == self.dev_addr else MessageCardLeft
            preferred_factor, reply_symbols = self.calc_width(len(message_content))
            if r:= message.reply_to:
                message_header = f"[ref=replied][b]> {message.chat.participants[Message.get(Message.id == r).sender]}[/b]\n" \
                                 f"[i]> {Message.get(Message.id == r).content.get().content.decode('utf-8')[:reply_symbols]}...[/i][/ref]\n\n"
            elif f:= message.forwarded_from:
                message_header = f"> Forwarded from [b] {f}[/b]\n\n"

            self.ids.messages_container.add_widget(card(
                message_header = message_header,
                message_content = message_content,
                full_date = message.date_received.astimezone(localtz),
                size_hint_x = preferred_factor,
                message_actions_menu = self.message_actions_menu,
                reply_to = message.reply_to,
                forwarded_from = message.forwarded_from,
                messages_scroll = self.ids.messages_scroll,
                id = message.id
            ), pos)

    def message_actions_callback(self, action):
        self.message_actions_menu.dismiss()
        if action == "reply":
            if not [c for c in self.ids.chat_area.children if isinstance(c, ReplyMessagePane)]:
                self.ids.chat_area.add_widget(ReplyMessagePane(text = self.message_actions_menu.caller.message_content,
                                                               msgid = self.message_actions_menu.caller.id))
        elif action == "copy":
            Clipboard.copy(self.message_actions_menu.caller.message_content)
        elif action == "forward":
            forward_menu = MDListBottomSheet()
            for chat in Chat.select().order_by(Chat.last_message_id.desc()):
                forward_menu.add_item(f"{chat.display_name} ({chat.id})", lambda x, y = chat: self.forward_callback(x, y))
            forward_menu.open()
            print(self.action_msg_id)
            # case "edit":
            #     pass
        elif action == "delete":
            self.delete_dialog = MDDialog(
                title="Delete message?",
                text="This message will be deleted forever and it would be impossible to recover it since messages are stored only on clients devices!",
                type="alert",
                buttons=[
                    MDRaisedButton(text="CANCEL", on_release=self.delete_message_callback),
                    MDFlatButton(text="DELETE", on_release=self.delete_message_callback),
                ],
            )
            self.delete_dialog.open()


    def delete_message_callback(self, caller):
        if caller.text == "DELETE" and (widgets:= [el for el in self.ids.messages_container.children
                                                   if el.id == self.message_actions_menu.caller.id and
                                                   isinstance(el, MessageCardBase)]):
            if target := Message.get_or_none(Message.id == widgets[0].id):
                for message in Message.select().where(Message.reply_to == target.id):
                    message.reply_to = 0
                    message.save()
                if target.chat.last_message_id == target.id:
                    target.chat.last_message_id = target.chat.messages.select().where(Message.id != target.id).order_by(Message.id.desc()).get_or_none()
                    target.chat.save()
                Message.delete_by_id(target.id)
            self.ids.messages_container.remove_widget(widgets[0])
        self.delete_dialog.dismiss()

    def chat_actions_callback(self, action, chat):
        self.chat_actions_menu.dismiss()
        print(action, chat)

    def chat_actions_menu_callback(self, caller):
        self.chat_actions_menu.caller = caller
        self.chat_actions_menu.open()

    def forward_callback(self, x, c):
        if c and (m:= Message.get_or_none(Message.id == self.action_msg_id)):
            nm = Message.create(sender = self.dev_addr, recipient = c.get_id(), forwarded_from = m.forwarded_from or m.chat.get_id(),
                                reply_to = 0, chat = c, message_hash = "")
            nc = Content.create(message = nm, content_type = ContentType.TEXT, content = m.content.get().content) # TODO?
            nm.save()
            nc.save()
            app.send_message(nm.get_id())
        self.action_msg_id = None

    def record_audio_message(self, data):
        self.ids.messages_container.add_widget(ChatDateHeader(date = len(data))) # TODO

    def send(self, reply_to = 0, forwarded_from = 0):
        if content := self.ids.input_field.text:
            self.ids.input_field.text = ""
            current_chat = self.ids.screen_manager.get_screen("chat_screen").current_chat
            if _:= [c for c in self.ids.chat_area.children if isinstance(c, ReplyMessagePane)]:
                reply_to = _[0].msgid
                self.ids.chat_area.remove_widget(_[0])
            if chat:= Chat.get_or_none(Chat.id == current_chat):
                m = Message.create(sender = self.dev_addr, recipient = current_chat, forwarded_from = forwarded_from,
                                   reply_to = reply_to, chat = chat, message_hash = "")
                c = Content.create(message = m, content_type = ContentType.TEXT, content = content.encode('utf-8')) # TODO?
                m.save()
                c.save()
                if Message.get(chat.last_message_id).date_received.day != m.date_received.day:
                    self.ids.messages_container.add_widget(ChatDateHeader(date = m.date_received))
                #chat.last_message_id = m.get_id()
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
        chat = 0
        try: chat = int(self.ids.new_chat_id.text, 0)
        except: pass
        else:
            self.ids.new_chat_id.text = ""
            self.ids.screen_manager.get_screen("chat_screen").current_chat = chat
            self.ids.screen_manager.get_screen("chat_screen").current_page = 1
            self.ids.screen_manager.current = "chat_screen"

    def check_id(self, caller, text):
        try:
            val = int(text or "1", 0)
            if val <= 0 or val >= 0xffffffff or val == self.dev_addr:
                raise
        except: caller.error = True
        else: caller.error = False

    # def open_chat(self, caller, chat = None):
    #     print(caller, chat)
    #     self.current_chat = chat if chat else caller.chat
    #     self.ids.screen_manager.current = "chat_screen"

class ChatCard(MDCard, ButtonBehavior):
    chat = NumericProperty(0xffffffff)
    display_name = StringProperty("Anonymous")
    message = StringProperty("Message")
    avatar = StringProperty()
    time = StringProperty("01.01.1970")
    unread = NumericProperty(1)
    screen_manager = ObjectProperty()
    #
    last_message_id = NumericProperty(-1)


    def open_chat(self, caller):
        self.screen_manager.get_screen("chat_screen").current_chat = caller.chat
        self.screen_manager.get_screen("chat_screen").current_page = 1
        self.screen_manager.current = "chat_screen"
        # chat = Chat.get_or_none(Chat.id == caller.chat)
        # chat.unread = 0
        # chat.save()


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

    def messagecard_callback(self, caller, msg_id):
        self.message_actions_menu.caller = caller
        self.message_actions_menu.open()
        app.set_action_msg_id(msg_id)
        #self.parent.root.action_msg_id = msg_id

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
        #self._monitor_conn_thread = RepeatTimer(self._process_delay, self._connection_monitor)

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
        self.root.dev_addr = self.dev_addr
        self.root.ids.nav_profile.text = hex(self.dev_addr)
        self._check_msg_thread.start()
        Clock.schedule_interval(self._connection_monitor, self._process_delay)

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
            self.root.ids.settings_label1.text = f"{self._device.send_command(command=s.USB_GET_DEVINFO)}"
        self.root.ids.settings_label2.text = f"{sys.path}"
        self.root.ids.settings_label3.text = f"{self._device.dev_addr}"
        self.root.ids.settings_label5.text = f"{self._device.dev_info}"

    def do3(self, caller):
        print(caller.vbar)

    def set_action_msg_id(self, msg_id):
        if isinstance(msg_id, int) and 0 <= msg_id < 0xffffffff:
            self.root.action_msg_id = msg_id

    def _connection_monitor(self, dt):
        a = self.root.ids.toolbar_messenger.right_action_items
        if self._inet.available: a[0][0] = "assets/icons/conn_inet.png"
        else: a[0][0] = "assets/icons/conn_inet_no.png"
        if self._device.device_available: a[1][0] = "assets/icons/conn_lora.png"
        else: a[1][0] = "assets/icons/conn_lora_no.png"
        self.root.ids.toolbar_messenger.update_action_bar(self.root.ids.toolbar_messenger.children[1].children[0], a)
        #TODO paths


    # def open_chat(self, caller, chat = None):
    #     print(caller, chat)
    #     self.root.current_chat = chat if chat else caller.chat
    #     self.root.ids.screen_manager.current = "chat_screen"

    def keyboard_events(self, window, key, *largs):
        #if self.manager_open and key in (1001, 27):
        #    self.file_manager.back()
        if key == 27: #elif
            self.root.ids.screen_manager.current = "messenger_screen"
        return True

    def send_message(self, msg_id: int):
        message_db: Message = Message.get(Message.id == msg_id)
        message_rp = None
        if message_db.reply_to:
            message_rp = Message.get_or_none(Message.id == message_db.reply_to)
        print("send_message date.sent: ", message_db.date_sent)
        message = MessagePacket(reply_to = message_rp.message_hash if message_rp else "",
                                forwarded_from = message_db.forwarded_from,
                                content = message_db.content.get().content.decode('utf-8'),
                                date = message_db.date_sent)

        parts = ceil(len(message.packet) / 100) if len(message.packet) > 100 else 0
        for i, j in enumerate(range(0, len(message.packet), 100)):
            print(message_db.recipient)
            a = NetPacket(dst_addr = message_db.recipient, fragm_c = parts, fragment = i,
                          app_id = AppID.MESSENGER, content_type = ContentType.TEXT,
                          direction = NetPacketDirection.OUT,
                          raw_data = bytes.fromhex(message_db.message_hash if parts else '') + message.packet[j:j+100])
            # если фрагментация, то нужно как-то убедиться, что пакеты фрагменты принадлежат одному сообщению
            # TODO проверить
            print("send_message fragment", a.packet)
            self._device.add_packet(a)

    def _process_messages(self):
        try:
            while not self._messenger_queue.empty():
                packet: NetPacket = self._messenger_queue.get()
                #if packet.dst_addr == settings.BROADCAST:
                print(packet.packet)
                if packet.content_type == ContentType.TEXT:
                    message = MessagePacket(source_packet = packet.raw_data)
                    chat = Chat.get_or_create(id = packet.src_addr,
                                              defaults={"participants": {packet.src_addr: packet.src_addr,
                                                                         packet.dst_addr: packet.dst_addr},
                                                        "id": packet.src_addr,
                                                        "display_name": hex(packet.src_addr)})[0] # TODO read docs
                    reply_to = 0
                    if message.reply_to and (m_rp:= Message.get_or_none((Message.message_hash == message.reply_to.hex()) & (Message.chat == chat))):
                        reply_to = m_rp.id
                    print("HASH UI: ", message.hash)
                    if not Message.select().where(Message.message_hash == message.hash):
                        m = Message.create(sender = packet.src_addr, recipient = packet.dst_addr, date_sent = message.date,
                                           forwarded_from = message.forwarded_from, reply_to = reply_to, chat = chat,
                                           message_hash = "")
                        #if not packet.is_fragmented:
                        c = Content.create(message = m, content_type = packet.content_type, content = message.content.encode('utf-8')) # TODO?
                        # else:
                        #     if not (c:= m.content.get_or_none()):
                        #         c = Content.create(message = m, content_type = packet.content_type, content = pickle.dumps([0]*packet.fragm_c), ready = False)
                        #     l = pickle.loads(c.content)
                        #     l[packet.fragment] = message.content.encode('utf-8')
                        #     c.content = pickle.dumps(l)
                        #     if all([bool(fr) for fr in l]):
                        #         c.ready = True
                        #         c.content = b''.join(c.content)
                        m.save()
                        c.save()
                        if m.recipient == self.dev_addr:
                            chat.unread += 1
                        chat.save()

                        a = NetPacket(dst_addr = packet.src_addr, app_id = AppID.NETWORK, content_type = ContentType.L3CNFRP,
                                      direction = NetPacketDirection.OUT, raw_data = packet.hashsum)
                        print("SEND CONFIRMATION", a.packet)
                        self._device.add_packet(a)
                    else:
                        print("IGNORE")
                elif packet.content_type == ContentType.MESSAGE_OPTIONS:
                    pass
                    # определяем требуемое действие. возможно, нужно переотправить какое-то сообщение (фрагмент)
                elif packet.content_type == ContentType.MESSAGE_STATUS:
                    pass
                    # обновляем статус


                #else: # если мы отправителя/получателя не знаем, то выше отправлен сразу запрос ключа, а этот пакет складываем в конец
                #    self._messenger_queue.put(packet)

        except Exception:
            print(traceback.format_exc())


if __name__ == "__main__":
    app = MessengerApp()
    app.run()


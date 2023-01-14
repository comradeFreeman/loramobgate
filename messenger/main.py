import sys
import os

import settings
import traceback
sys.path.insert(0, os.path.join(os.path.dirname(__file__) ,"device"))
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDTextButton, MDFlatButton, MDRaisedButton
from kivymd.uix.label import MDLabel
from kivy.properties import NumericProperty, StringProperty, ListProperty, ObjectProperty
from kivymd.uix.card import MDCard
from kivymd.uix.widget import MDWidget
from kivymd.uix.navigationdrawer import MDNavigationLayout
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.toolbar.toolbar import ActionTopAppBarButton
from kivymd.uix.textfield import MDTextField
from kivy.uix.behaviors import ButtonBehavior
from kivy.lang import Builder
from datetime import datetime
from random import choice
from kivy.core.window import Window
from kivy.metrics import sp,dp, dpi2px
from kivymd.toast import toast
from kivymd.uix.filemanager import MDFileManager
from kivy.utils import platform
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.list import OneLineAvatarIconListItem, ImageLeftWidget, IRightBodyTouch
from kivymd.uix.tooltip import MDTooltip
from kivymd.uix.bottomsheet import MDListBottomSheet
import json
from itertools import groupby
from dateutil import parser
from kivy.utils import escape_markup
from kivy.core.clipboard import Clipboard
from kivymd.uix.dialog import MDDialog
from typing import Union

from kivymd.icon_definitions import md_icons
from audiostream import get_input
from time import sleep
from datetime import datetime, timedelta


from loramobgate import UsbConnection, Device, InternetConnection, NetPacket, RepeatTimer
from models import Message, Content, Chat
from classes import ContentType

import usb.util as u
import declarations as s

import queue
from hashlib import md5

if platform == "android":
    from android.permissions import request_permissions, Permission
    request_permissions([Permission.WRITE_EXTERNAL_STORAGE,
                         Permission.READ_EXTERNAL_STORAGE,
                         Permission.RECORD_AUDIO,
                         Permission.INTERNET])
    import usb4a.usb
else:
    import usb.core

class MessengerRoot(MDScreen):
    def __init__(self, **kwargs):
        self.dev_addr = 0xacde73bf
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
            elevation=2,
            opening_time=0
        )
        self.chat_actions_menu = MDDropdownMenu(
            items = chat_actions,
            width_mult = 5,
            max_height=0,
            elevation=2,
            opening_time=0
        )


    def load_chats(self, caller):
        self.ids.chats_container.clear_widgets()
        for chat in Chat.select().order_by(Chat.last_message_id):
            last_message: Message = Message.get(Message.id == chat.last_message_id)
            #content = last_message.content.get()
            #content.content = content.content.decode('unicode_escape').encode('utf-8')
            #content.save()
            # print(type(last_message), last_message.content.get().content)
            # if isinstance(last_message.content.get().content, str):
            #     c = last_message.content.get()
            #     c.content = c.content.encode('utf-8')
            #     c.save()
            self.ids.chats_container.add_widget(ChatCard(
                chat = chat.id,
                display_name = chat.display_name,
                message = last_message.content.get().content.decode('utf-8'),
                avatar = chat.avatar,
                time = last_message.date_received.strftime("%H:%M"
                if last_message.date_received.day == datetime.utcnow().day
                else "%d %b"),
                unread = chat.unread,
                screen_manager = self.ids.screen_manager
            ))

        # with open('assets/test/data/chats.json') as f_obj:
        #     chats = json.load(f_obj)
        #
        #     for chat in chats:
        #         self.ids.chats_container.add_widget(ChatCard(
        #             chat = int(chat, 16),
        #             display_name = chats[chat]['display_name'],
        #             message = chats[chat]['last_message'],
        #             avatar = chats[chat]['avatar'],
        #             time = chats[chat]['time'],
        #             unread = chats[chat]['unread'],
        #             screen_manager = self.ids.screen_manager
        #         ))

    def calc_width(self, len_text):
        factor = sp(12) * len_text / self.width
        reply_symbols = int(self.width * factor / sp(15))
        if factor <= .9:
            return factor, reply_symbols
        else:
            return .75, reply_symbols

    def load_messages(self, caller):
        self.ids.messages_container.clear_widgets()
        chat = Chat.get(Chat.id == caller.current_chat)
        messages = chat.messages.select().order_by(Message.date_received)
        self.ids.toolbar_chat.title = chat.display_name

        for date, grouped_by_day in groupby(messages, key=lambda msg: msg.date_received.date()):
            self.ids.messages_container.add_widget(ChatDateHeader(text = date.strftime("%a, %d %b")))
            for message in grouped_by_day:
                message_header = ""
                #print(type(message.content.get().content), )
                # if isinstance(message.content.get().content, str):
                #     c = message.content.get()
                #     c.content = c.content.encode('utf-8')
                #     c.save()
                message_content = message.content.get().content.decode('utf-8')
                print(message.sender, self.dev_addr)
                card = MessageCardRight if message.sender == self.dev_addr else MessageCardLeft
                preferred_factor, reply_symbols = self.calc_width(len(message_content))
                if r:= message.reply_to:
                    message_header = f"[ref=replied][b]> {chat.participants[Message.get(Message.id == r).sender]}[/b]\n" \
                                  f"[i]> {Message.get(Message.id == r).content.get().content.decode('utf-8')[:reply_symbols]}...[/i][/ref]\n\n"
                elif f:= message.forwarded_from:
                    message_header = f"Forwarded from [b] {f}[/b]\n\n"


                self.ids.messages_container.add_widget(card(
                        message_header = message_header,
                        message_content = message_content,
                        time = message.date_received.strftime("%H:%M"),
                        full_date = message.date_received,
                        size_hint_x = preferred_factor,
                        message_actions_menu = self.message_actions_menu,
                        reply_to = message.reply_to,
                        forwarded_from = message.forwarded_from,
                        messages_scroll = self.ids.messages_scroll,
                        id = message.id
                ))
        # with open('assets/test/data/chats.json') as f_obj:
        #     chat = json.load(f_obj)[hex(caller.current_chat)]
        #     messages = chat['messages']
        #     self.ids.toolbar_chat.title = chat['display_name']
        #     for date, grouped_by_day in groupby(messages, key=lambda i: messages[i]['timestamp'][:11]):
        #         self.ids.messages_container.add_widget(ChatDateHeader(text = parser.parse(date).strftime("%a, %d %b")))
        #         for j in grouped_by_day:
        #             message_header = ""
        #             card = MessageCardRight if messages[j]['from'] == app.dev_addr else MessageCardLeft
        #             date_obj = parser.parse(messages[j]['timestamp'])
        #             preferred_factor, reply_symbols = self.calc_width(len(messages[j]['message']))
        #             if "reply_to" in messages[j].keys():
        #                 message_header = f"[ref=replied][b]> {chat['participants'][messages[messages[j]['reply_to']]['from']]}[/b]\n" \
        #                           f"[i]> {messages[messages[j]['reply_to']]['message'][:reply_symbols]}...[/i][/ref]\n\n"
        #             elif "forwarded_from" in messages[j]:
        #                 message_header = f"Forwarded from [b] {messages[j]['forwarded_from']}[/b]\n\n"
        #             self.ids.messages_container.add_widget(card(
        #                 message_header = message_header,
        #                 message_content = messages[j]['message'],
        #                 time = date_obj.strftime("%H:%M"),
        #                 full_date = date_obj,
        #                 size_hint_x = preferred_factor,
        #                 message_actions_menu = self.message_actions_menu,
        #                 reply_to = messages[j].get("reply_to", ""),
        #                 forwarded_from = messages[j].get("forwarded_from", ""),
        #                 messages_scroll = self.ids.messages_scroll,
        #                 id = j
        #             ))

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
        self.ids.messages_container.add_widget(ChatDateHeader(text = len(data)))

    def send(self):
        if message := self.ids.input_field.text:
            if _:= [c for c in self.ids.chat_area.children if isinstance(c, ReplyMessagePane)]:
                reply_pane = _[0]
                print(reply_pane.msgid)
                app.send_message_ui(message, reply_pane.msgid)
            print(message)
            app.send_message_ui(message)
        else:
            pass
            # micro

        # mic = get_input(callback=self.record_audio_message)
        # mic.start()


class ChatCard(MDCard, ButtonBehavior):
    chat = NumericProperty(0xffffffff)
    display_name = StringProperty("Anonymous")
    message = StringProperty("Message")
    avatar = StringProperty()
    time = StringProperty("01.01.1970")
    unread = NumericProperty(1)
    screen_manager = ObjectProperty()

    def open_chat(self, caller):
        print(f"chat {caller.chat}")
        self.screen_manager.get_screen("chat_screen").current_chat = caller.chat
        self.screen_manager.current = "chat_screen"


class MessageCardBase(MDCard, ButtonBehavior):
    size_hint_x = NumericProperty()
    message_header = StringProperty()
    message_content = StringProperty()
    time = StringProperty()
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
    msgid = StringProperty()


class ChatDateHeader(MDBoxLayout):
    text = StringProperty()


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

    @property
    def dev_addr(self):
        return self._device.dev_addr if self._device else None # TODO подумать

    def on_start(self):
        Builder.load_file('chatcard.kv')
        Builder.load_file('messagecard.kv')
        self.root.load_chats(None)
        self._device = Device(messenger_queue = self._messenger_queue, inet = self._inet)
        self._check_msg_thread.start()

    def on_stop(self):
        self._device.stop()


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

    def convert_my_timestamp(self, obj: Union[datetime, bytes]):
        if isinstance(obj, datetime):
            point = datetime.utcnow()
            value = int((point - point.replace(hour=0,minute=0,second=0,microsecond=0)).\
                        total_seconds()) * 100 + (point.microsecond % 100)
            return value.to_bytes(length=3, byteorder="big")
        elif isinstance(obj, bytes):
            timestamp = str(int.from_bytes(obj, byteorder='big'))
            new_date = datetime.utcnow().replace(hour = 0, minute = 0, second = 0, microsecond = 0)
            new_date += timedelta(seconds=int(timestamp[:-2]), milliseconds=(int(timestamp) % 100) * 10)
            now = datetime.utcnow()
            if new_date > now:
                new_date = new_date.replace(day = now.day - 1)
            return new_date
        return None


    def send_message_ui(self, text, reply_to = 0, forwarded_from = 0):
        current_chat = self.root.ids.screen_manager.get_screen("chat_screen").current_chat
        print(current_chat)
        if chat:= Chat.get_or_none(Chat.id == current_chat):
            m = Message.create(sender = self.dev_addr,
                               recipient = current_chat,
                               timestamp_sent = self.convert_my_timestamp(datetime.utcnow()),
                               forwarded_from = forwarded_from,
                               reply_to = reply_to,
                               chat = chat,
                               message_hash = md5(text.encode('utf-8')).hexdigest())
            c = Content.create(message = m,
                               content_type = ContentType.TEXT,
                               content = text) # TODO?
            m.save()
            c.save()
            chat.last_message_id = m.get_id()
            chat.save()
        else:
            print("Давай по новой, Миша, всё хуйня! (с)")


    def open_chat(self, caller):
        print(caller.chat)
        self.root.current_chat = caller.chat
        #self.root.ids.screen_manager.get_screen("chat_screen").current_chat = str(caller.chat)
        self.root.ids.screen_manager.current = "chat_screen"

    def keyboard_events(self, window, key, *largs):
        #if self.manager_open and key in (1001, 27):
        #    self.file_manager.back()
        if key == 27: #elif
            self.root.ids.screen_manager.current = "messenger_screen"
        return True

    def _process_messages(self):
        try:
            while not self._messenger_queue.empty():
                packet: NetPacket = self._messenger_queue.get()
                #if packet.dst_addr == settings.BROADCAST:
                #	pass
                # TODO А что если сделать два подтипа пакета сообщения: который получен из Лоры и который получен из сети
                # Тогда в последнем случае можно было бы добавить дополнительную информацию (время отправки или "ответ_на")
                # Хотя это усложняет пакет, причём очень сильно
                print(packet.packet)
                if decrypted:= self._device.decrypt(packet.src_addr, packet.raw_data):
                    flags = decrypted[3]
                    data = decrypted[(3 + (flags & 4) + (flags & 16)):]
                    chat = Chat.get_or_create(Chat.id == packet.src_addr,
                                              defaults={"participants": {packet.src_addr: packet.src_addr,
                                                                         packet.dst_addr: packet.dst_addr},
                                                        "id": packet.src_addr,
                                                        "display_name": str(packet.src_addr)})[0] # TODO read docs
                    m = Message.create(sender = packet.src_addr,
                                       recipient = packet.dst_addr,
                                       date_sent = self.convert_my_timestamp(decrypted[:3]),
                                       #timestamp_sent = int.from_bytes(decrypted[:3], byteorder='big'),
                                       forwarded_from = decrypted[3:3 + (flags & 4)] or 0,
                                       reply_to = decrypted[3:3 + (flags & 16)] or 0,
                                       chat = chat,
                                       message_hash = md5(data.encode('utf-8')).hexdigest())
                    c = Content.create(message = m,
                                       content_type = packet.content_type,
                                       content = data) # TODO?
                    m.save()
                    c.save()
                    if m.recipient == self.dev_addr:
                        chat.unread += 1
                    chat.last_message_id = m.get_id()
                    chat.save()


                else: # если мы отправителя/получателя не знаем, то выше отправлен сразу запрос ключа, а этот пакет складываем в конец
                    self._messenger_queue.put(packet)

        except Exception:
            print(traceback.format_exc())


if __name__ == "__main__":
    app = MessengerApp()
    app.run()


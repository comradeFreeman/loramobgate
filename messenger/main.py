import sys
import os
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

from kivymd.icon_definitions import md_icons
from audiostream import get_input
from time import sleep


from device.loramobgate import UsbConnection

import usb.util as u

#import usb.core

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
        self.dev_addr = "0xacde73bf"
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
        with open('assets/test/data/chats.json') as f_obj:
            chats = json.load(f_obj)

            for chat in chats:
                self.ids.chats_container.add_widget(ChatCard(
                    chat = int(chat, 16),
                    display_name = chats[chat]['display_name'],
                    message = chats[chat]['last_message'],
                    avatar = chats[chat]['avatar'],
                    time = chats[chat]['time'],
                    unread = chats[chat]['unread'],
                    screen_manager = self.ids.screen_manager
                ))

    def calc_width(self, len_text):
        factor = sp(12) * len_text / self.width
        reply_symbols = int(self.width * factor / sp(15))
        if factor <= .9:
            return factor, reply_symbols
        else:
            return .75, reply_symbols

    def load_messages(self, caller):
        self.ids.messages_container.clear_widgets()
        with open('assets/test/data/chats.json') as f_obj:
            chat = json.load(f_obj)[hex(caller.current_chat)]
            messages = chat['messages']
            self.ids.toolbar_chat.title = chat['display_name']
            for date, grouped_by_day in groupby(messages, key=lambda i: messages[i]['timestamp'][:11]):
                self.ids.messages_container.add_widget(ChatDateHeader(text = parser.parse(date).strftime("%a, %d %b")))
                for j in grouped_by_day:
                    message_header = ""
                    card = MessageCardRight if messages[j]['from'] == self.dev_addr else MessageCardLeft
                    date_obj = parser.parse(messages[j]['timestamp'])
                    preferred_factor, reply_symbols = self.calc_width(len(messages[j]['message']))
                    if "reply_to" in messages[j].keys():
                        message_header = f"[ref=replied][b]> {chat['participants'][messages[messages[j]['reply_to']]['from']]}[/b]\n" \
                                  f"[i]> {messages[messages[j]['reply_to']]['message'][:reply_symbols]}...[/i][/ref]\n\n"
                    elif "forwarded_from" in messages[j]:
                        message_header = f"Forwarded from [b] {messages[j]['forwarded_from']}[/b]\n\n"
                    self.ids.messages_container.add_widget(card(
                        message_header = message_header,
                        message_content = messages[j]['message'],
                        time = date_obj.strftime("%H:%M"),
                        full_date = date_obj,
                        size_hint_x = preferred_factor,
                        message_actions_menu = self.message_actions_menu,
                        reply_to = messages[j].get("reply_to", ""),
                        forwarded_from = messages[j].get("forwarded_from", ""),
                        messages_scroll = self.ids.messages_scroll,
                        id = j
                    ))

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
            print(message)

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
    reply_to = StringProperty()
    forwarded_from = StringProperty()
    messages_scroll = ObjectProperty()
    id = StringProperty()

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
        #self.manager_open = False
        #self.file_manager = MDFileManager(exit_manager = self.exit_manager,
        #                                  select_path = self.select_path)

    def on_start(self):
        Builder.load_file('chatcard.kv')
        Builder.load_file('messagecard.kv')
        self.root.load_chats(None)

    # def add_attachment(self):
    #     if platform == "android":
    #         from android.permissions import request_permissions, Permission
    #         from android.storage import primary_external_storage_path
    #         request_permissions([Permission.WRITE_EXTERNAL_STORAGE, Permission.READ_EXTERNAL_STORAGE])
    #         #self.file_manager.show(primary_external_storage_path())
    #         self.file_manager.show(self.user_data_dir)
    #     else:
    #         self.file_manager.show(os.path.expanduser("~"))
    #     self.manager_open = True

    # def select_path(self, path: str):
    #     self.exit_manager()
    #     toast(path)
    #
    # def exit_manager(self, *args):
    #     self.manager_open = False
    #     self.file_manager.close()

    def do(self, caller: ActionTopAppBarButton):
        print(caller)
        a: MDTopAppBar = self.root.ids.toolbar_messenger
        print(a.right_action_items)
        print(type(a.right_action_items))
        #caller.icon = "dots-vertical" # менять иконку в зависимости от типа соединения

    def do1(self, caller):
        buffer = bytearray(b'\0'*16)
        manager = usb4a.usb.get_usb_manager()
        usb_device_list = usb4a.usb.get_usb_device_list()
        usb_device_name_list = [device.getDeviceName() for device in usb_device_list]
        if usb_device_name_list:
            self.root.ids.settings_label1.text = usb_device_list[0].getDeviceName()
            my_device = usb4a.usb.get_usb_device(usb_device_list[0].getDeviceName())
            self.root.ids.settings_label2.text = f"{my_device}"
            if not usb4a.usb.has_usb_permission(my_device):
                usb4a.usb.request_usb_permission(my_device)
            else:
                connection = manager.openDevice(my_device)
                self.root.ids.settings_label3.text = f"{connection}"
                received = connection.controlTransfer(64 | 0 | 128, 209, 0, 0, buffer, len(buffer), 5000)
                self.root.ids.settings_label4.text = f"{received}: {buffer}"
        else:
            self.root.ids.settings_label6.text = "No :("

    def do2(self, caller):
        connection = UsbConnection()
        if connection:
            self.root.ids.settings_label1.text = f"{connection.send_to_device(209)}"
        self.root.ids.settings_label2.text = f"{sys.path}"


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


if __name__ == "__main__":
    app = MessengerApp()
    app.run()
#    messenger = Messenger()


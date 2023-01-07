from kivy.lang import Builder
from kivy.properties import ObjectProperty
from kivymd.app import MDApp
from kivymd.uix.scrollview import MDScrollView
KV = '''
<ContentNavigationDrawer>
    MDList:
        OneLineListItem:
            text: "Screen 1"
            on_press:
                root.nav_drawer.set_state("close")
                root.screen_manager.current = "scr 1"
        OneLineListItem:
            text: "Screen 2"
            on_press:
                root.nav_drawer.set_state("close")
                root.screen_manager.current = "scr 2"
MDScreen:
    MDTopAppBar:
        pos_hint: {"top": 1}
        elevation: 4
        title: "MDNavigationDrawer"
        left_action_items: [["menu", lambda x: nav_drawer.set_state("open")]]
    MDNavigationLayout:
        MDScreenManager:
            id: screen_manager
            MDScreen:
                name: "scr 1"
                MDBoxLayout:
                    orientation: 'vertical'
                    MDLabel:
                        text: "Screen 1"
                        halign: "center"
                    ScrollView:
                        MDBoxLayout:
                            id: chats_container
                            orientation: 'vertical'
                            padding: "10dp", "6dp", "10dp", "10dp"
                            spacing: "1dp"
                            adaptive_height: True

            MDScreen:
                name: "scr 2"
                MDLabel:
                    text: "Screen 2"
                    halign: "center"
    MDNavigationDrawer:
        id: nav_drawer
        radius: (0, 16, 16, 0)
        MDNavigationDrawerMenu:
            MDNavigationDrawerHeader:
                title: "Header"
                text: "Header text"
                spacing: "4dp"
                padding: "12dp", 0, 0, "56dp"
            MDNavigationDrawerItem:
                icon: "gmail"
                right_text: "+99"
                text: "Inbox"
            MDNavigationDrawerDivider:
            MDNavigationDrawerLabel:
                text: "Labels"
        ContentNavigationDrawer:
            screen_manager: screen_manager
            nav_drawer: nav_drawer
'''


class ContentNavigationDrawer(MDScrollView):
    screen_manager = ObjectProperty()
    nav_drawer = ObjectProperty()
    
class Example(MDApp):
    def build(self):
        self.theme_cls.primary_palette = "Orange"
        self.theme_cls.theme_style = "Dark"
        return Builder.load_string(KV)
Example().run()

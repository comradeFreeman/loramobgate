 
from kivy.lang import Builder
from kivymd.app import MDApp
KV = '''
<DrawerClickableItem@MDNavigationDrawerItem>
    focus_color: "#e7e4c0"
    text_color: "#4a4939"
    icon_color: "#4a4939"
    ripple_color: "#c5bdd2"
    selected_color: "#0c6c4d"
<DrawerLabelItem@MDNavigationDrawerItem>
    text_color: "#4a4939"
    icon_color: "#4a4939"
    focus_behavior: False
    selected_color: "#4a4939"
    _no_ripple_effect: True
    
MDScreen:
    MDNavigationLayout:
        MDScreenManager:
            id: screen_manager
            MDScreen:
                MDTopAppBar:
                    title: "Navigation Drawer"
                    elevation: 4
                    pos_hint: {"top": 1}
                    md_bg_color: "#e7e4c0"
                    specific_text_color: "#4a4939"
                    left_action_items: [["menu", lambda x: nav_drawer.set_state("open")]]

        MDNavigationDrawer:
            id: nav_drawer
            type: "modal"
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
                DrawerClickableItem:
                    icon: "send"
                    text: "Outbox"
                MDNavigationDrawerDivider:
                MDNavigationDrawerLabel:
                    text: "Labels"
                DrawerLabelItem:
                    icon: "information-outline"
                    text: "Label"
                DrawerLabelItem:
                    icon: "information-outline"
                    text: "Label"
'''

class Example(MDApp):
    def build(self):
        self.theme_cls.theme_style = "Dark"
        return Builder.load_string(KV)
Example().run()


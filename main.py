from kivymd.app import MDApp
from kivymd.uix.button import MDRaisedButton

class TestApp(MDApp):
    def build(self):
        return MDRaisedButton(
            text="TEST KIVYMD",
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )

if __name__ == '__main__':
    TestApp().run()
# managers/input_handler.py
"""
Handles user input during code execution
"""
import threading
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup

from ide_core.themes import ThemeManager
from utils.screen_utils import get_screen_category


class InputHandler:
    """Обрабатывает ввод пользователя во время выполнения кода"""

    def __init__(self, app):
        self.app = app

    def handle_input(self, prompt=""):
        """Обрабатывает запрос input() от выполняемого кода"""
        self.app.code_executor.clear_input()
        input_result = [None]
        input_event = threading.Event()

        def show_popup(dt):
            theme = ThemeManager.get_theme()
            tr = self.app.tr

            content = BoxLayout(orientation='vertical', padding=dp(5), spacing=dp(4))

            # Метка с приглашением
            content.add_widget(Label(
                text=prompt or tr.get('input_prompt', 'Enter value:'),
                color=theme['text_color'], font_size=dp(14), font_name='SourceBold',
                size_hint_y=None, height=dp(25)
            ))

            # Поле ввода
            text_input = TextInput(
                multiline=False, font_size=dp(14), font_name='SourceBold',
                background_color=theme['input_bg'], foreground_color=theme['input_text'],
                cursor_color=theme['input_cursor'], hint_text=tr.get('input_hint', 'Enter text...'),
                hint_text_color=theme['hint_text'], size_hint_y=None, height=dp(35),
                padding=(dp(5), dp(5))
            )
            self.app.current_input_widget = text_input
            content.add_widget(text_input)

            # Кнопки
            buttons = BoxLayout(size_hint_y=None, height=dp(30), spacing=dp(5))

            def on_ok(*args):
                value = text_input.text.strip()
                input_result[0] = value if value else ""
                self.app.code_executor.provide_input(value if value else "")
                self.app.current_input_widget = None
                popup.dismiss()
                input_event.set()

            def on_cancel(*args):
                input_result[0] = ""
                self.app.code_executor.provide_input("")
                self.app.current_input_widget = None
                popup.dismiss()
                input_event.set()

            btn_cancel = Button(
                text=tr.get('cancel', 'Cancel'), font_name='SourceBold',
                background_color=theme['widget_bg'], background_normal='', background_down='',
                color=theme['text_color'], font_size=dp(12), on_release=on_cancel
            )

            btn_ok = Button(
                text=tr.get('ok', 'OK'), font_name='SourceBold',
                background_color=theme['widget_bg'], background_normal='', background_down='',
                color=theme['text_color'], font_size=dp(12), on_release=on_ok
            )

            buttons.add_widget(btn_cancel)
            buttons.add_widget(btn_ok)
            content.add_widget(buttons)

            # Размер попапа
            category = get_screen_category()
            if category == 'tablet':
                size_hint = (0.80, 0.40)
            elif category == 'large_phone':
                size_hint = (0.88, 0.42)
            else:
                size_hint = (0.93, 0.45)

            popup = Popup(
                title=tr.get('input_title', 'Input'), title_color=theme['popup_title'],
                background='', background_color=theme.get('popup_bg', (1.0, 1.0, 1.0, 1)),
                content=content, size_hint=size_hint, pos_hint={'top': 0.95}, auto_dismiss=False
            )
            popup.bind(on_dismiss=lambda *args: input_event.set())

            # ДОБАВИТЬ ОБЁРТКУ КНОПОК
            if hasattr(self.app, 'wrap_widget_buttons'):
                self.app.wrap_widget_buttons(content)

            popup.open()

            def focus_input(dt):
                if text_input and text_input.parent:
                    text_input.focus = True

            Clock.schedule_once(focus_input, 0.3)

        Clock.schedule_once(show_popup, 0.1)
        input_event.wait(timeout=180)
        return input_result[0] if input_result[0] is not None else ""
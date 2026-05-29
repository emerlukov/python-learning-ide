# ui/menus.py
"""
Menu components: Language, Theme, Editor Settings, Syntax Highlight
"""
import os
import time
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.dropdown import DropDown
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, Rectangle, Line
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.core.window import Window

from core import SettingsManager, ThemeManager, SyntaxStyleManager, TRANSLATIONS
from utils.screen_utils import get_screen_category
from widgets.dialogs import ThemedPopup


class LanguageSelectMenu:
    """Подменю выбора языка"""
    LANGUAGE_NAMES = {'ru': 'Русский', 'en': 'English'}

    def __init__(self, app):
        self.app = app
        self._dropdown = None

    def show(self, parent_button):
        theme = ThemeManager.get_theme()
        btn_bg = theme.get('action_bar_bg', theme['widget_bg'])
        self._dropdown = DropDown()
        self._dropdown.auto_width = False
        self._dropdown.width = dp(167)

        from kivy.uix.behaviors import ButtonBehavior

        class MenuItem(ButtonBehavior, BoxLayout):
            pass

        for lang_code in sorted(TRANSLATIONS.keys()):
            lang_name = self.LANGUAGE_NAMES.get(lang_code, lang_code.upper())
            display_text = f"✓ {lang_name}" if lang_code == self.app.current_language else f"    {lang_name}"
            icon_text = lang_code.upper()

            box = MenuItem(orientation='horizontal', size_hint_y=None, height=dp(30),
                           padding=(dp(8), 0), spacing=dp(5))

            icon_lbl = Label(text=icon_text, color=theme['text_color'], font_size=dp(11),
                             font_name='SourceBold', size_hint_x=None, width=dp(17),
                             halign='center', valign='middle')
            box.add_widget(icon_lbl)

            lbl = Label(text=display_text, color=theme['text_color'], font_size=dp(15),
                        font_name='SourceBold', halign='left', valign='middle')
            box.add_widget(lbl)

            box.canvas.before.clear()
            with box.canvas.before:
                Color(*btn_bg)
                Rectangle(pos=box.pos, size=box.size)
                Color(btn_bg[0] + 0.08, btn_bg[1] + 0.08, btn_bg[2] + 0.08, 1)
                Line(rectangle=(box.pos[0], box.pos[1], box.size[0], box.size[1]), width=dp(0.5))

            box.bind(pos=lambda inst, val, bg=btn_bg: self._update_btn_bg(inst, bg),
                     size=lambda inst, val, bg=btn_bg: self._update_btn_bg(inst, bg))
            box.bind(on_release=lambda instance, code=lang_code: self._on_language_select(code))
            self._dropdown.add_widget(box)

        Clock.schedule_once(lambda dt: self._dropdown.open(parent_button), 0.1)
        self._adjust_position(parent_button)

    def _on_language_select(self, lang_code):
        if hasattr(self.app, 'vibrate_short'):
            self.app.vibrate_short()

        if self._dropdown:
            try:
                self._dropdown.dismiss()
            except:
                pass

        if lang_code != self.app.current_language:
            self.app.current_language = lang_code
            self.app.tr = TRANSLATIONS[lang_code]
            SettingsManager.save_language(lang_code)
            self.app._update_ui_language()
            self.app.show_result_popup(
                f"{self.app.tr.get('language', 'Language')}: {self.LANGUAGE_NAMES.get(lang_code, lang_code.upper())}")

    def _adjust_position(self, parent_button):
        def adjust(*args):
            win_width, win_height = Window.size
            if self._dropdown and self._dropdown.parent:
                if self._dropdown.x + self._dropdown.width > win_width:
                    self._dropdown.x = win_width - self._dropdown.width - dp(3)
                if self._dropdown.y < 0:
                    self._dropdown.y = parent_button.y + parent_button.height
                elif self._dropdown.y + self._dropdown.height > win_height:
                    self._dropdown.y = parent_button.y - self._dropdown.height

        Clock.schedule_once(adjust, 0.15)

    def _update_btn_bg(self, instance, bg_color):
        if not hasattr(instance, 'canvas'):
            return
        instance.canvas.before.clear()
        with instance.canvas.before:
            Color(*bg_color)
            Rectangle(pos=instance.pos, size=instance.size)
            Color(bg_color[0] + 0.08, bg_color[1] + 0.08, bg_color[2] + 0.08, 1)
            Line(rectangle=(instance.pos[0], instance.pos[1], instance.size[0], instance.size[1]), width=dp(0.5))


class ThemeSelectMenu:
    """Подменю выбора темы"""

    def __init__(self, app):
        self.app = app
        self._dropdown = None

    def show(self, parent_button):
        theme = ThemeManager.get_theme()
        btn_bg = theme.get('action_bar_bg', theme['widget_bg'])
        self._dropdown = DropDown()
        self._dropdown.auto_width = False
        self._dropdown.width = dp(167)

        from kivymd.uix.label import MDIcon
        from kivy.uix.behaviors import ButtonBehavior

        class MenuItem(ButtonBehavior, BoxLayout):
            pass

        available_themes = ThemeManager.get_available_themes()
        current_theme_name = ThemeManager.get_theme_name()
        theme_icons = {'dark': 'weather-night', 'light': 'weather-sunny'}

        for theme_id, theme_title in available_themes.items():
            display_text = f"✓ {theme_title}" if theme_id == current_theme_name else f"    {theme_title}"
            icon_name = theme_icons.get(theme_id, 'circle')

            box = MenuItem(orientation='horizontal', size_hint_y=None, height=dp(30),
                           padding=(dp(8), 0), spacing=dp(5))

            icon = MDIcon(icon=icon_name, font_size=f"{dp(10)}sp", theme_text_color="Custom",
                          text_color=theme['text_color'], size_hint_x=None, width=dp(17))
            box.add_widget(icon)

            lbl = Label(text=display_text, color=theme['text_color'], font_size=dp(15),
                        font_name='SourceBold', halign='left', valign='middle')
            box.add_widget(lbl)

            box.canvas.before.clear()
            with box.canvas.before:
                Color(*btn_bg)
                Rectangle(pos=box.pos, size=box.size)
                Color(btn_bg[0] + 0.08, btn_bg[1] + 0.08, btn_bg[2] + 0.08, 1)
                Line(rectangle=(box.pos[0], box.pos[1], box.size[0], box.size[1]), width=dp(0.5))

            box.bind(pos=lambda inst, val, bg=btn_bg: self._update_btn_bg(inst, bg),
                     size=lambda inst, val, bg=btn_bg: self._update_btn_bg(inst, bg))
            box.bind(on_release=lambda instance, tid=theme_id: self._on_theme_select(tid))
            self._dropdown.add_widget(box)

        Clock.schedule_once(lambda dt: self._dropdown.open(parent_button), 0.1)
        self._adjust_position(parent_button)

    def _on_theme_select(self, theme_id):
        if hasattr(self.app, 'vibrate_short'):
            self.app.vibrate_short()

        if self._dropdown:
            try:
                self._dropdown.dismiss()
            except:
                pass

        if theme_id != ThemeManager.get_theme_name():
            success = ThemeManager.switch_theme(theme_id)
            new_style = SyntaxStyleManager.get_default_style_for_theme(theme_id)
            SyntaxStyleManager.save_current_style(new_style)
            if success:
                self._show_restart_dialog(theme_id)

    def _show_restart_dialog(self, theme_id):
        tr = self.app.tr
        new_theme = ThemeManager.get_theme()
        available_themes = ThemeManager.get_available_themes()
        theme_title = available_themes.get(theme_id, theme_id)

        content = BoxLayout(orientation='vertical', padding=dp(7), spacing=dp(5))
        message = (f"{tr.get('theme_settings', 'Theme')}: {theme_title}\n\n"
                   f"{tr.get('restart_for_syntax', 'Restart app to fully apply syntax highlighting?')}\n"
                   f"{tr.get('restart_info', 'All tabs will be saved and restored.')}")

        lbl = Label(text=message, font_name='SourceBold', color=new_theme['text_color'],
                    font_size=dp(10), halign='center', valign='middle', size_hint_y=0.7)
        lbl.bind(width=lambda instance, value: setattr(instance, 'text_size', (value, None)))
        content.add_widget(lbl)

        btn_layout = BoxLayout(size_hint_y=0.3, spacing=dp(4))

        popup = ThemedPopup(
            title=tr.get('theme_settings', 'Theme'),
            title_color=new_theme['popup_title'],
            title_bg=new_theme.get('popup_title_bg', new_theme['widget_bg']),
            popup_bg=new_theme.get('popup_bg', new_theme['widget_bg']),
            separator_color=new_theme.get('popup_separator', (0.25, 0.25, 0.25, 1)),
            content=content, size_hint=(0.85, 0.35), auto_dismiss=False
        )

        btn_restart = Button(text=tr.get('restart_btn', 'Restart'), font_name='SourceBold',
                             background_color=(0.2, 0.5, 0.2, 1), background_normal='', background_down='',
                             color=new_theme['text_color'], font_size=dp(9),
                             on_release=lambda x: self._do_restart(popup))
        btn_later = Button(text=tr.get('later_btn', 'Later'), font_name='SourceBold',
                           background_color=new_theme['widget_bg'], background_normal='', background_down='',
                           color=new_theme['text_color'], font_size=dp(9),
                           on_release=lambda x: popup.dismiss())

        btn_layout.add_widget(btn_later)
        btn_layout.add_widget(btn_restart)
        content.add_widget(btn_layout)
        popup.open()

    def _do_restart(self, popup):
        popup.dismiss()
        if hasattr(self.app, 'tab_manager'):
            self.app.tab_manager.save_all_tabs()
        if hasattr(self.app, '_save_autosave'):
            self.app._save_autosave()
        self.app.stop()

    def _adjust_position(self, parent_button):
        def adjust(*args):
            win_width, win_height = Window.size
            if self._dropdown and self._dropdown.parent:
                if self._dropdown.x + self._dropdown.width > win_width:
                    self._dropdown.x = win_width - self._dropdown.width - dp(3)
                if self._dropdown.y < 0:
                    self._dropdown.y = parent_button.y + parent_button.height
                elif self._dropdown.y + self._dropdown.height > win_height:
                    self._dropdown.y = parent_button.y - self._dropdown.height

        Clock.schedule_once(adjust, 0.15)

    def _update_btn_bg(self, instance, bg_color):
        if not hasattr(instance, 'canvas'):
            return
        instance.canvas.before.clear()
        with instance.canvas.before:
            Color(*bg_color)
            Rectangle(pos=instance.pos, size=instance.size)
            Color(bg_color[0] + 0.08, bg_color[1] + 0.08, bg_color[2] + 0.08, 1)
            Line(rectangle=(instance.pos[0], instance.pos[1], instance.size[0], instance.size[1]), width=dp(0.5))


class EditorSettingsMenu:
    """Подменю настроек редактора"""

    def __init__(self, app):
        self.app = app
        self._dropdown = None
        self._font_menu = None

    def show(self, parent_button):
        theme = ThemeManager.get_theme()
        btn_bg = theme.get('action_bar_bg', theme['widget_bg'])
        self._dropdown = DropDown()
        self._dropdown.auto_width = False
        self._dropdown.width = dp(167)

        from kivymd.uix.label import MDIcon
        from kivy.uix.behaviors import ButtonBehavior

        class MenuItem(ButtonBehavior, BoxLayout):
            pass

        menu_items = [
            ('format-font', self.app.tr.get('editor_font', 'Шрифт'), self._open_font_submenu),
        ]

        for icon_name, text, handler in menu_items:
            box = MenuItem(orientation='horizontal', size_hint_y=None, height=dp(30),
                           padding=(dp(8), 0), spacing=dp(5))

            icon = MDIcon(icon=icon_name, font_size=f"{dp(10)}sp", theme_text_color="Custom",
                          text_color=theme['text_color'], size_hint_x=None, width=dp(17))
            box.add_widget(icon)

            lbl = Label(text=text, color=theme['text_color'], font_size=dp(15),
                        font_name='SourceBold', halign='left', valign='middle')
            box.add_widget(lbl)

            box.canvas.before.clear()
            with box.canvas.before:
                Color(*btn_bg)
                Rectangle(pos=box.pos, size=box.size)
                Color(btn_bg[0] + 0.08, btn_bg[1] + 0.08, btn_bg[2] + 0.08, 1)
                Line(rectangle=(box.pos[0], box.pos[1], box.size[0], box.size[1]), width=dp(0.5))

            box.bind(pos=lambda inst, val, bg=btn_bg: self._update_btn_bg(inst, bg),
                     size=lambda inst, val, bg=btn_bg: self._update_btn_bg(inst, bg))
            box.bind(on_release=lambda instance, h=handler: self._on_item_click(h, parent_button))
            self._dropdown.add_widget(box)

        Clock.schedule_once(lambda dt: self._dropdown.open(parent_button), 0.1)
        self._adjust_position(parent_button)

    def _on_item_click(self, handler, parent_button):
        if hasattr(self.app, 'vibrate_short'):
            self.app.vibrate_short()

        if self._dropdown:
            try:
                self._dropdown.dismiss()
            except:
                pass

        if handler == self._open_font_submenu:
            handler(parent_button)

    def _open_font_submenu(self, parent_button):
        if self._font_menu is None:
            from ui.menus import FontSelectMenu
            self._font_menu = FontSelectMenu(self.app)
        self._font_menu.show(parent_button)

    def _adjust_position(self, parent_button):
        def adjust(*args):
            win_width, win_height = Window.size
            if self._dropdown and self._dropdown.parent:
                if self._dropdown.x + self._dropdown.width > win_width:
                    self._dropdown.x = win_width - self._dropdown.width - dp(3)
                if self._dropdown.y < 0:
                    self._dropdown.y = parent_button.y + parent_button.height
                elif self._dropdown.y + self._dropdown.height > win_height:
                    self._dropdown.y = parent_button.y - self._dropdown.height

        Clock.schedule_once(adjust, 0.15)

    def _update_btn_bg(self, instance, bg_color):
        if not hasattr(instance, 'canvas'):
            return
        instance.canvas.before.clear()
        with instance.canvas.before:
            Color(*bg_color)
            Rectangle(pos=instance.pos, size=instance.size)
            Color(bg_color[0] + 0.08, bg_color[1] + 0.08, bg_color[2] + 0.08, 1)
            Line(rectangle=(instance.pos[0], instance.pos[1], instance.size[0], instance.size[1]), width=dp(0.5))


class FontSelectMenu:
    """Подменю для выбора шрифта редактора кода"""

    FONT_NAMES = {
        'JetBrainsMono': 'JetBrains Mono',
        'FiraCode': 'Fira Code',
        'CascadiaCode': 'Cascadia Code',
        'IBMPlexMono': 'IBM Plex Mono',
        'NotoSansMono': 'Noto Sans Mono',
        'SourceCodePro': 'Source Code Pro',
        'DroidMono': 'Droid Sans Mono',
    }

    FONT_ICONS = {
        'JetBrainsMono': 'language-python',
        'FiraCode': 'code-braces',
        'CascadiaCode': 'code-tags',
        'IBMPlexMono': 'code-parentheses',
        'NotoSansMono': 'format-font',
        'SourceCodePro': 'code-json',
        'DroidMono': 'android',
    }

    def __init__(self, app):
        self.app = app
        self._dropdown = None

    def show(self, parent_button):
        theme = ThemeManager.get_theme()
        self._dropdown = DropDown()
        self._dropdown.auto_width = False
        self._dropdown.width = dp(167)

        from kivymd.uix.label import MDIcon
        from kivy.uix.behaviors import ButtonBehavior

        class MenuItem(ButtonBehavior, BoxLayout):
            pass

        current_font = SettingsManager.get_font()
        btn_bg = theme.get('action_bar_bg', theme['widget_bg'])

        font_order = ['JetBrainsMono', 'FiraCode', 'CascadiaCode', 'IBMPlexMono', 'NotoSansMono', 'SourceCodePro',
                      'DroidMono']

        for font_key in font_order:
            font_name = self.FONT_NAMES.get(font_key, font_key)
            icon_name = self.FONT_ICONS.get(font_key, 'circle')
            display_text = f"✓ {font_name}" if font_key == current_font else f"    {font_name}"

            box = MenuItem(orientation='horizontal', size_hint_y=None, height=dp(30),
                           padding=(dp(8), 0), spacing=dp(5))

            icon = MDIcon(icon=icon_name, font_size=f"{dp(10)}sp", theme_text_color="Custom",
                          text_color=theme['text_color'], size_hint_x=None, width=dp(17))
            box.add_widget(icon)

            lbl = Label(text=display_text, color=theme['text_color'], font_size=dp(15),
                        font_name='SourceBold', halign='left', valign='middle')
            box.add_widget(lbl)

            box.canvas.before.clear()
            with box.canvas.before:
                Color(*btn_bg)
                Rectangle(pos=box.pos, size=box.size)
                Color(btn_bg[0] + 0.08, btn_bg[1] + 0.08, btn_bg[2] + 0.08, 1)
                Line(rectangle=(box.pos[0], box.pos[1], box.size[0], box.size[1]), width=dp(0.5))

            box.bind(pos=lambda inst, val, bg=btn_bg: self._update_btn_bg(inst, bg),
                     size=lambda inst, val, bg=btn_bg: self._update_btn_bg(inst, bg))
            box.bind(on_release=lambda instance, fk=font_key: self._on_font_select(fk))
            self._dropdown.add_widget(box)

        Clock.schedule_once(lambda dt: self._dropdown.open(parent_button), 0.1)
        self._adjust_position(parent_button)

    def _on_font_select(self, font_key):
        if self._dropdown:
            try:
                self._dropdown.dismiss()
            except:
                pass

        if font_key != SettingsManager.get_font():
            SettingsManager.save_font(font_key)
            self._apply_font(font_key)
            font_name = self.FONT_NAMES.get(font_key, font_key)
            self.app.show_result_popup(f"✓ Шрифт: {font_name}")

    def _apply_font(self, font_key):
        font_files = {
            'DroidMono': 'DroidMono',
            'JetBrainsMono': 'JetBrainsMono',
            'FiraCode': 'FiraCode',
            'CascadiaCode': 'CascadiaCode',
            'IBMPlexMono': 'IBMPlexMono',
            'NotoSansMono': 'NotoSansMono',
            'SourceCodePro': 'SourceCodePro',
        }

        if not hasattr(self.app, 'tab_manager'):
            return

        for tab in self.app.tab_manager.tabs:
            editor = tab.get('editor')
            if editor and hasattr(editor, 'text_input'):
                editor.text_input.font_name = font_files.get(font_key, 'DroidMono')
                if hasattr(editor, 'force_full_font_reset'):
                    from kivy.clock import Clock
                    Clock.schedule_once(editor.force_full_font_reset, 0.15)

    def _adjust_position(self, parent_button):
        def adjust(*args):
            win_width, win_height = Window.size
            if self._dropdown and self._dropdown.parent:
                if self._dropdown.x + self._dropdown.width > win_width:
                    self._dropdown.x = win_width - self._dropdown.width - dp(3)
                if self._dropdown.y < 0:
                    self._dropdown.y = parent_button.y + parent_button.height
                elif self._dropdown.y + self._dropdown.height > win_height:
                    self._dropdown.y = parent_button.y - self._dropdown.height

        Clock.schedule_once(adjust, 0.15)

    def _update_btn_bg(self, instance, bg_color):
        if not hasattr(instance, 'canvas'):
            return
        instance.canvas.before.clear()
        with instance.canvas.before:
            Color(*bg_color)
            Rectangle(pos=instance.pos, size=instance.size)
            Color(bg_color[0] + 0.08, bg_color[1] + 0.08, bg_color[2] + 0.08, 1)
            Line(rectangle=(instance.pos[0], instance.pos[1], instance.size[0], instance.size[1]), width=dp(0.5))


class SyntaxHighlightMenu:
    """Меню выбора стиля подсветки"""

    def __init__(self, app):
        self.app = app
        self._popup = None
        self._preview_popup = None
        self._preview_bg_rect = None
        self._current_menu_button = None

    def show(self, parent_button):
        self._current_menu_button = parent_button
        self._destroy_all_windows()

        theme = ThemeManager.get_theme()
        tr = self.app.tr
        current_theme = ThemeManager.get_theme_name()
        styles = SyntaxStyleManager.get_styles_by_theme(current_theme)
        style_info = SyntaxStyleManager.get_style_display_info()
        current_style = SyntaxStyleManager.get_current_style()

        content = BoxLayout(orientation='vertical', padding=dp(5), spacing=dp(3))
        header_text = tr.get('syntax_header', 'Выберите стиль подсветки:')
        content.add_widget(Label(text=header_text, size_hint_y=None, height=dp(30),
                                 color=theme.get('text_color', (0, 0, 0, 1)),
                                 font_size=dp(17), halign='left', valign='middle'))

        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False, do_scroll_y=True)
        styles_list = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(1.5), padding=[0, dp(2)])
        styles_list.bind(minimum_height=styles_list.setter('height'))

        from kivymd.uix.label import MDIcon
        from kivy.uix.behaviors import ButtonBehavior

        btn_bg = theme.get('popup_bg', (1.0, 1.0, 1.0, 1))

        for style_name in styles:
            info = style_info.get(style_name, {'name': style_name.replace('_', ' ').title(), 'type': 'unknown'})
            prefix = '✓ ' if style_name == current_style else '  '
            display_name = f"{prefix}{info['name']}"

            class MenuItem(ButtonBehavior, BoxLayout):
                pass

            box = MenuItem(orientation='horizontal', size_hint_y=None, height=dp(30),
                           padding=(dp(8), 0), spacing=dp(4))

            icon = MDIcon(icon='weather-night' if info['type'] == 'dark' else 'weather-sunny',
                          font_size=f"{dp(7)}sp", theme_text_color="Custom",
                          text_color=theme.get('text_color', (0, 0, 0, 1)),
                          size_hint_x=None, width=dp(13))
            box.add_widget(icon)

            lbl = Label(text=display_name, color=theme.get('text_color', (0, 0, 0, 1)),
                        font_size=dp(15), font_name='SourceBold', halign='left', valign='middle')
            box.add_widget(lbl)

            box.canvas.before.clear()
            with box.canvas.before:
                Color(*btn_bg)
                Rectangle(pos=box.pos, size=box.size)
                Color(btn_bg[0] + 0.05, btn_bg[1] + 0.05, btn_bg[2] + 0.05, 1)
                Line(rectangle=(box.pos[0], box.pos[1], box.size[0], box.size[1]), width=dp(0.3))

            box.bind(pos=lambda inst, val, bg=btn_bg: self._update_btn_bg(inst, bg),
                     size=lambda inst, val, bg=btn_bg: self._update_btn_bg(inst, bg))
            box.bind(on_release=lambda instance, sn=style_name: self._open_preview_after_close(sn))
            styles_list.add_widget(box)

        scroll.add_widget(styles_list)
        content.add_widget(scroll)

        close_text = tr.get('close', 'Закрыть')
        btn_close = Button(text=close_text, size_hint_y=None, height=dp(40),
                           background_color=theme.get('widget_bg', (0.843, 0.816, 1.0, 1)),
                           background_normal='', background_down='',
                           color=theme.get('text_color', (0, 0, 0, 1)),
                           font_size=dp(13), on_release=lambda x: self._destroy_all_windows())
        content.add_widget(btn_close)

        title = tr.get('syntax_menu_title', 'Стиль подсветки')
        self._popup = Popup(
            title=title, title_color=theme.get('popup_title', (0, 0, 0, 1)),
            separator_color=theme.get('popup_separator', (0.25, 0.25, 0.25, 1)),
            background='', background_color=theme.get('popup_bg', (1.0, 1.0, 1.0, 1)),
            content=content, size_hint=(0.92, 0.85), auto_dismiss=False
        )
        self._popup.open()

    def _open_preview_after_close(self, style_name):
        self._close_menu()
        Clock.schedule_once(lambda dt: self._open_preview(style_name), 0.3)

    def _open_preview(self, style_name):
        self._close_preview()
        theme = ThemeManager.get_theme()
        tr = self.app.tr
        info = SyntaxStyleManager.get_style_display_info()
        style_info = info.get(style_name, {'name': style_name.replace('_', ' ').title(), 'type': 'unknown'})

        demo_code = f'''# Предпросмотр: {style_info['name']}
def fibonacci(n):
    """Вычисляет числа Фибоначчи"""
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(n - 1):
        a, b = b, a + b
    return b

class Calculator:
    def __init__(self, name="Calc"):
        self.name = name
        self._value = 0
    def add(self, x):
        self._value += x
        return self._value

calc = Calculator("Калькулятор")
result = calc.add(10)
print(f"{{calc.name}}: {{result}}")
print(f"Fib(10) = {{fibonacci(10)}}")
items = ["хлеб", "молоко", "яйца"]
for item in items:
    print(f"- {{item}}")
'''

        highlighted_text = self._highlight_code(demo_code, style_name, theme)
        content = BoxLayout(orientation='vertical', padding=dp(5), spacing=dp(3))

        from kivymd.uix.label import MDIcon

        header_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(20), spacing=dp(3))
        icon = MDIcon(icon='weather-night' if style_info['type'] == 'dark' else 'weather-sunny',
                      font_size=f"{dp(11)}sp", theme_text_color="Custom",
                      text_color=theme.get('text_color', (0.85, 0.88, 0.90, 1)),
                      size_hint_x=None, width=dp(20))
        header_box.add_widget(icon)

        type_str = 'Тёмный стиль' if style_info['type'] == 'dark' else 'Светлый стиль'
        header_lbl = Label(text=f"[b]{style_info['name']}[/b] — {type_str}", markup=True,
                           color=theme.get('text_color', (0.85, 0.88, 0.90, 1)),
                           font_size=dp(13), font_name='SourceBold', halign='left', valign='middle')
        header_box.add_widget(header_lbl)
        content.add_widget(header_box)

        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False, do_scroll_y=True)

        from kivy.uix.floatlayout import FloatLayout
        editor_bg_color = theme.get('editor_bg', (1.0, 1.0, 1.0, 1))
        preview_box = FloatLayout(size_hint=(1, None))
        with preview_box.canvas.before:
            Color(*editor_bg_color)
            self._preview_bg_rect = Rectangle(pos=preview_box.pos, size=preview_box.size)
        preview_box.bind(pos=self._update_preview_bg, size=self._update_preview_bg)

        from kivy.uix.label import Label as KivyLabel
        preview_label = KivyLabel(
            text=highlighted_text, markup=True, font_size=dp(13),
            font_name='DejaVuSans', color=theme.get('editor_text', (0, 0, 0, 1)),
            size_hint=(1, None), padding=(dp(5), dp(5)), halign='left', valign='top',
            text_size=(None, None)
        )
        preview_label.bind(texture_size=lambda instance, value: setattr(instance, 'height', value[1] + dp(10)))
        preview_label.bind(texture_size=lambda instance, value: setattr(preview_box, 'height', value[1] + dp(10)))

        preview_box.add_widget(preview_label)
        scroll.add_widget(preview_box)
        content.add_widget(scroll)

        btn_layout = BoxLayout(size_hint_y=None, height=dp(33), spacing=dp(4))
        apply_text = tr.get('apply', 'Применить')
        cancel_text = tr.get('cancel', 'Отмена')
        back_text = tr.get('back', '← Назад')

        btn_back = Button(text=back_text, font_name='DejaVuSans',
                          background_color=theme.get('widget_bg', (0.14, 0.14, 0.15, 1)),
                          background_normal='', background_down='',
                          color=theme.get('text_color', (0, 0, 0, 1)),
                          font_size=dp(13), on_release=lambda x: self._back_to_menu())
        btn_cancel = Button(text=cancel_text,
                            background_color=theme.get('widget_bg', (0.14, 0.14, 0.15, 1)),
                            background_normal='', background_down='',
                            color=theme.get('text_color', (0, 0, 0, 1)),
                            font_size=dp(13), on_release=lambda x: self._destroy_all_windows())
        btn_apply = Button(text=apply_text,
                           background_color=theme.get('btn_success_bg', (0.2, 0.5, 0.2, 1)),
                           background_normal='', background_down='',
                           color=(1, 1, 1, 1), font_size=dp(13),
                           on_release=lambda x: self._apply_style(style_name))

        btn_layout.add_widget(btn_back)
        btn_layout.add_widget(btn_cancel)
        btn_layout.add_widget(btn_apply)
        content.add_widget(btn_layout)

        title = tr.get('syntax_preview', 'Предпросмотр: ') + style_info['name']
        popup_bg_color = theme.get('editor_bg', (1.0, 1.0, 1.0, 1))

        self._preview_popup = Popup(
            title=title, title_color=theme.get('popup_title', (0, 0, 0, 1)),
            separator_color=theme.get('popup_separator', (0.25, 0.25, 0.25, 1)),
            background='', background_color=popup_bg_color,
            content=content, size_hint=(0.95, 0.88), auto_dismiss=False
        )
        self._preview_popup.open()

    def _update_preview_bg(self, instance, value):
        if hasattr(self, '_preview_bg_rect') and self._preview_bg_rect:
            self._preview_bg_rect.pos = instance.pos
            self._preview_bg_rect.size = instance.size

    def _highlight_code(self, code, style_name, theme):
        try:
            from pygments.lexers import PythonLexer as PL
            from pygments.styles import get_style_by_name as gsbn
            try:
                style = gsbn(style_name)
            except:
                style = gsbn('monokai')
            lexer = PL()
            tokens = list(lexer.get_tokens(code))
            result = []
            for token_type, text in tokens:
                if text == '':
                    continue
                text = text.replace('[', '&bl;').replace(']', '&br;')
                try:
                    style_info = style.style_for_token(token_type)
                    if style_info.get('color'):
                        result.append(f"[color=#{style_info['color']}]{text}[/color]")
                    elif style_info.get('bold'):
                        result.append(f'[b]{text}[/b]')
                    elif style_info.get('italic'):
                        result.append(f'[i]{text}[/i]')
                    else:
                        result.append(text)
                except:
                    result.append(text)
            return ''.join(result)
        except:
            return code.replace('[', '&bl;').replace(']', '&br;')

    def _apply_style(self, style_name):
        self._destroy_all_windows()
        SyntaxStyleManager.save_current_style(style_name)
        if hasattr(self.app, 'tab_manager'):
            self.app.tab_manager.save_all_tabs()
        info = SyntaxStyleManager.get_style_display_info()
        style_display = info.get(style_name, {}).get('name', style_name)
        self._show_restart_dialog(style_display)

    def _show_restart_dialog(self, style_display):
        tr = self.app.tr
        theme = ThemeManager.get_theme()

        content = BoxLayout(orientation='vertical', padding=dp(7), spacing=dp(5))
        message = (f"{tr.get('syntax_highlight', 'Подсветка')}: {style_display}\n\n"
                   f"{tr.get('restart_for_syntax', 'Перезапустить приложение для полной смены подсветки синтаксиса?')}\n"
                   f"{tr.get('restart_info', 'Все вкладки будут сохранены и восстановлены.')}")

        lbl = Label(text=message, font_name='SourceBold', color=theme.get('text_color', (0, 0, 0, 1)),
                    font_size=dp(10), halign='center', valign='middle', size_hint_y=0.7)
        lbl.bind(width=lambda instance, value: setattr(instance, 'text_size', (value, None)))
        content.add_widget(lbl)

        btn_layout = BoxLayout(size_hint_y=0.3, spacing=dp(4))

        popup = Popup(
            title=tr.get('syntax_menu_title', 'Стиль подсветки'),
            title_color=theme.get('popup_title', (0, 0, 0, 1)),
            separator_color=theme.get('popup_separator', (0.25, 0.25, 0.25, 1)),
            background='', background_color=theme.get('popup_bg', (1.0, 1.0, 1.0, 1)),
            content=content, size_hint=(0.85, 0.35), auto_dismiss=False
        )

        btn_restart = Button(text=tr.get('restart_btn', 'Перезапустить'), font_name='SourceBold',
                             background_color=theme.get('btn_success_bg', (0.2, 0.5, 0.2, 1)),
                             background_normal='', background_down='', color=(1, 1, 1, 1),
                             font_size=dp(9), on_release=lambda x: self._do_restart(popup))
        btn_later = Button(text=tr.get('later_btn', 'Позже'), font_name='SourceBold',
                           background_color=theme.get('widget_bg', (0.843, 0.816, 1.0, 1)),
                           background_normal='', background_down='',
                           color=theme.get('text_color', (0, 0, 0, 1)), font_size=dp(9),
                           on_release=lambda x: popup.dismiss())

        btn_layout.add_widget(btn_later)
        btn_layout.add_widget(btn_restart)
        content.add_widget(btn_layout)
        popup.open()

    def _do_restart(self, popup):
        popup.dismiss()
        if hasattr(self.app, 'tab_manager'):
            self.app.tab_manager.save_all_tabs()
        if hasattr(self.app, 'stop'):
            self.app.stop()

    def _back_to_menu(self):
        self._close_preview()
        if self._current_menu_button:
            self.show(self._current_menu_button)
        elif hasattr(self.app, 'menu_button'):
            self.show(self.app.menu_button)

    def _close_menu(self):
        if self._popup:
            try:
                self._popup.dismiss()
            except:
                pass
            self._popup = None

    def _close_preview(self):
        if self._preview_popup:
            try:
                self._preview_popup.dismiss()
            except:
                pass
            self._preview_popup = None

    def _destroy_all_windows(self):
        self._close_menu()
        self._close_preview()

    def _update_btn_bg(self, instance, bg_color):
        if not hasattr(instance, 'canvas'):
            return
        instance.canvas.before.clear()
        with instance.canvas.before:
            Color(*bg_color)
            Rectangle(pos=instance.pos, size=instance.size)
            Color(bg_color[0] + 0.05, bg_color[1] + 0.05, bg_color[2] + 0.05, 1)
            Line(rectangle=(instance.pos[0], instance.pos[1], instance.size[0], instance.size[1]), width=dp(0.3))


class SettingsMenu:
    """Выпадающее меню настроек"""

    def __init__(self, app):
        self.app = app
        self._dropdown = None
        self._language_menu = LanguageSelectMenu(app)
        self._theme_menu = ThemeSelectMenu(app)
        self._editor_menu = EditorSettingsMenu(app)
        self._syntax_menu = SyntaxHighlightMenu(app)

    def show(self, parent_button):
        if hasattr(self.app, '_menu_dropdown') and self.app._menu_dropdown:
            try:
                self.app._menu_dropdown.dismiss()
            except:
                pass

        theme = ThemeManager.get_theme()
        btn_bg = theme.get('action_bar_bg', theme['widget_bg'])
        self._dropdown = DropDown()
        self._dropdown.auto_width = False
        self._dropdown.width = dp(167)

        from kivymd.uix.label import MDIcon
        from kivy.uix.behaviors import ButtonBehavior

        class MenuItem(ButtonBehavior, BoxLayout):
            pass

        menu_items = [
            ('translate', 'select_language', lambda: self._open_language_submenu(parent_button)),
            ('theme-light-dark', 'theme_settings', lambda: self._open_theme_submenu(parent_button)),
            ('palette', 'syntax_highlight', lambda: self._open_syntax_submenu(parent_button)),
            ('tune', 'editor_settings', lambda: self._open_editor_submenu(parent_button)),
        ]

        for icon_name, item_key, handler in menu_items:
            box = MenuItem(orientation='horizontal', size_hint_y=None, height=dp(30),
                           padding=(dp(8), 0), spacing=dp(5))

            icon = MDIcon(icon=icon_name, font_size=f"{dp(10)}sp", theme_text_color="Custom",
                          text_color=theme['text_color'], size_hint_x=None, width=dp(17))
            box.add_widget(icon)

            lbl = Label(text=self.app.tr.get(item_key, item_key), color=theme['text_color'],
                        font_size=dp(15), font_name='SourceBold', halign='left', valign='middle')
            box.add_widget(lbl)

            box.canvas.before.clear()
            with box.canvas.before:
                Color(*btn_bg)
                Rectangle(pos=box.pos, size=box.size)
                Color(btn_bg[0] + 0.08, btn_bg[1] + 0.08, btn_bg[2] + 0.08, 1)
                Line(rectangle=(box.pos[0], box.pos[1], box.size[0], box.size[1]), width=dp(0.5))

            box.bind(pos=lambda inst, val, bg=btn_bg: self._update_btn_bg(inst, bg),
                     size=lambda inst, val, bg=btn_bg: self._update_btn_bg(inst, bg))
            box.bind(on_release=lambda instance, h=handler: self._on_item_click(h))
            self._dropdown.add_widget(box)

        Clock.schedule_once(lambda dt: self._dropdown.open(parent_button), 0.1)
        self._adjust_position(parent_button)

    def _on_item_click(self, handler):
        if self._dropdown:
            try:
                self._dropdown.dismiss()
            except:
                pass
        handler()

    def _open_language_submenu(self, parent_button):
        if hasattr(self.app, 'vibrate_short'):
            self.app.vibrate_short()
        self._language_menu.show(parent_button)

    def _open_theme_submenu(self, parent_button):
        if hasattr(self.app, 'vibrate_short'):
            self.app.vibrate_short()
        self._theme_menu.show(parent_button)

    def _open_syntax_submenu(self, parent_button):
        if hasattr(self.app, 'vibrate_short'):
            self.app.vibrate_short()
        self._syntax_menu.show(parent_button)

    def _open_editor_submenu(self, parent_button):
        if hasattr(self.app, 'vibrate_short'):
            self.app.vibrate_short()
        self._editor_menu.show(parent_button)

    def _adjust_position(self, parent_button):
        def adjust(*args):
            win_width, win_height = Window.size
            if self._dropdown and self._dropdown.parent:
                if self._dropdown.x + self._dropdown.width > win_width:
                    self._dropdown.x = win_width - self._dropdown.width - dp(3)
                if self._dropdown.y < 0:
                    self._dropdown.y = parent_button.y + parent_button.height
                elif self._dropdown.y + self._dropdown.height > win_height:
                    self._dropdown.y = parent_button.y - self._dropdown.height

        Clock.schedule_once(adjust, 0.15)

    def _update_btn_bg(self, instance, bg_color):
        if not hasattr(instance, 'canvas'):
            return
        instance.canvas.before.clear()
        with instance.canvas.before:
            Color(*bg_color)
            Rectangle(pos=instance.pos, size=instance.size)
            Color(bg_color[0] + 0.08, bg_color[1] + 0.08, bg_color[2] + 0.08, 1)
            Line(rectangle=(instance.pos[0], instance.pos[1], instance.size[0], instance.size[1]), width=dp(0.5))
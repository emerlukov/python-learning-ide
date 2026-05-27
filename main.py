"""
Python Learning IDE
Версия: 1.0.0

Полноценная среда разработки Python для Android с богатым функционалом:

=== ОСНОВНЫЕ ВОЗМОЖНОСТИ ===
✓ Редактор кода с подсветкой синтаксиса (Pygments)
✓ Автодополнение кода и список ключевых слов Python
✓ Нумерация строк и направляющие отступов
✓ Множество вкладок для работы с несколькими файлами
✓ Поддержка светлой и тёмной тем оформления
✓ Русский и английский языки интерфейса
✓ Адаптивный UI под разные размеры экранов

=== РАБОТА С ФАЙЛАМИ ===
✓ Файловый менеджер с поддержкой сортировки
✓ Открытие, сохранение, переименование, удаление файлов
✓ Поддержка多种 кодировок (UTF-8, CP1251, Latin-1 и др.)
✓ Асинхронная загрузка/сохранение (UI не блокируется)
✓ Автосохранение и восстановление вкладок

=== РЕДАКТОР И КОД ===
✓ Форматирование кода через autopep8
✓ Поиск и замена текста
✓ Переход к строке
✓ Undo/Redo (отмена/повтор действий)
✓ Копировать/Вырезать/Вставить
✓ Выделить весь код
✓ Очистка всего кода с подтверждением
✓ Видимая табуляция (4 пробела)

=== ВЫПОЛНЕНИЕ КОДА ===
✓ Запуск Python-кода прямо в приложении
✓ Обработка пользовательского ввода (input())
✓ Отображение результата в отдельном окне
✓ Защита от повторного запуска
✓ Обрезание слишком длинного вывода

=== AI АССИСТЕНТ ===
✓ Интеграция с Google Gemini API
✓ Помощь в написании кода
✓ Ответы на вопросы по Python

=== ПРОЧЕЕ ===
✓ Анимированная заставка при запуске
✓ Вибрация при нажатии на кнопки
✓ Выбор шрифта для редактора (JetBrains Mono, Fira Code и др.)
✓ Выбор стиля подсветки синтаксиса (Monokai, Dracula и др.)
✓ Копирование результатов в буфер обмена
✓ История выполнения кода
✓ Полная поддержка Android (через jnius и androidstorage)

=== ИСПРАВЛЕНИЯ И ОПТИМИЗАЦИЯ ===
✓ Прогрев Pygments при старте (нет первого фриза)
✓ Плавный набор текста в редакторе
✓ Оптимизированная работа с большими файлами
✓ Устранены микро-фризы
✓ Исправлено дёрганье клавиатуры
✓ Удалён мусор из кода (refactoring)

Версия 1.0.0 — первый стабильный релиз
"""

# ====================== ИМПОРТ СТАНДАРТНЫХ БИБЛИОТЕК ======================
import sys
import json
import os
import io
import threading
import traceback
import urllib.request
import urllib.error
import ssl
import time
import re
import builtins
import uuid
from datetime import datetime
from plyer import vibrator
# После остальных импортов, добавьте:
from file_manager import FileManager, FileBrowserPopup

# ====================== ИМПОРТ СТОРОННИХ БИБЛИОТЕК ======================
try:
    import autopep8

    HAS_AUTOPEP8 = True
    print("[INFO] autopep8 успешно загружен")
except ImportError:
    autopep8 = None
    HAS_AUTOPEP8 = False
    print("[WARNING] autopep8 не найден — будет использоваться базовое форматирование")

# ====================== ИМПОРТ БИБЛИОТЕК ANVPY (ANDROID) ======================
try:
    import anv
    from android import request_permissions, Permission

    try:
        import androidstorage
    except ImportError:
        androidstorage = None
    ANV_AVAILABLE = True
except ImportError:
    ANV_AVAILABLE = False
    androidstorage = None
    print("Внимание: Запуск не в среде AnvPy. Некоторые функции могут не работать.")

# ====================== ИМПОРТ БИБЛИОТЕК PLYER ======================
try:
    from plyer import storagepath

    PLYER_AVAILABLE = True
except:
    PLYER_AVAILABLE = False

# ====================== ИМПОРТ КОМПОНЕНТОВ KIVY ======================
from kivy.app import App
from kivymd.app import MDApp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.dropdown import DropDown
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle, Ellipse, Line
from kivy.core.clipboard import Clipboard
from kivy.core.window import Window
from kivy.core.text import LabelBase
from kivy.config import Config
from kivy.clock import Clock
from kivy.properties import ColorProperty, ListProperty, StringProperty
from kivy.lang import Builder
from kivy.utils import platform
from kivy.metrics import dp, sp
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from animated_splash import AnimatedSplashScreen
from kivymd.uix.button import MDRectangleFlatButton, MDFlatButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.label import MDIcon

# ====================== НОВЫЕ КОРОТКИЕ ИМПОРТЫ ======================
from utils import (
    DEBUG, log_error,
    get_screen_category, reset_screen_cache, adaptive_dp, adaptive_sp, get_tab_count,
    patched_excepthook, android_copy
)
from core import (
    SettingsManager, ThemeManager, SyntaxStyleManager, DARK_THEME, LIGHT_THEME,
    TRANSLATIONS
)
from widgets import (
    LineNumberTextInput, MyActionBar, MySymbolScrollBar,
    ThemedPopup, ThemedSpinner, AIAssistantPopup,
    SearchOnlyPopup, SearchReplacePopup, GotoLinePopup
)
from managers import AutoCompleteWidget, CodeExecutor, TabManager

# ====================== ИМПОРТ JNIUS ======================
try:
    from jnius import autoclass, cast
    JNIUS_AVAILABLE = True
except ImportError:
    JNIUS_AVAILABLE = False
    autoclass = None
    cast = None
    print("[INFO] jnius not available (running on desktop)")


# Переменные для хранения callback
_pending_file_callback = None
_pending_save_callback = None


# ====================== ПРОВЕРКА НАЛИЧИЯ PYGMENTS (ПОДСВЕТКА СИНТАКСИСА) ======================
try:
    from pygments.lexers import PythonLexer
    from pygments.styles import get_style_by_name

    HAS_PYGMENTS = True
except ImportError:
    PythonLexer = None
    HAS_PYGMENTS = False

# ====================== РЕГИСТРАЦИЯ ШРИФТОВ ТОЛЬКО ИЗ ПАПКИ ======================
from kivy.core.text import LabelBase

fonts_dir = os.path.join(os.path.dirname(__file__), 'fonts')

# 1. Регистрируем SourceBold (основной шрифт интерфейса)
source_bold_path = os.path.join(fonts_dir, 'SourceSansPro-Bold.ttf')
if os.path.exists(source_bold_path):
    LabelBase.register(name='SourceBold', fn_regular=source_bold_path)
else:
    # Fallback на другой шрифт из папки
    fallback_path = os.path.join(fonts_dir, 'NotoSans-Regular.ttf')
    if os.path.exists(fallback_path):
        LabelBase.register(name='SourceBold', fn_regular=fallback_path)

# 2. Регистрируем DejaVuSans для спецсимволов
dejavu_path = os.path.join(fonts_dir, 'DejaVuSans.ttf')
if os.path.exists(dejavu_path):
    LabelBase.register(name='DejaVuSans', fn_regular=dejavu_path)

# 3. Регистрируем моноширинные шрифты для редактора
mono_fonts = {
    'JetBrainsMono': 'JetBrainsMono.ttf',
    'FiraCode': 'FiraCode-Regular.ttf',
    'CascadiaCode': 'CascadiaCode.ttf',
    'IBMPlexMono': 'IBMPlexMono-Regular.ttf',
    'NotoSansMono': 'NotoSansMono.ttf',
    'SourceCodePro': 'SourceCodePro-Regular.otf',
    'DroidMono': 'NotoSansMono.ttf',
}

for font_name, font_file in mono_fonts.items():
    font_path = os.path.join(fonts_dir, font_file)
    if os.path.exists(font_path):
        LabelBase.register(name=font_name, fn_regular=font_path)

# 4. Регистрируем Roboto как основной (если нужен)
noto_path = os.path.join(fonts_dir, 'NotoSans-Regular.ttf')
if os.path.exists(noto_path):
    LabelBase.register(name='Roboto', fn_regular=noto_path)

# ====================== НАСТРОЙКИ KIVY ======================
Config.set('graphics', 'maxfps', '30')
Config.set('kivy', 'window_icon', '')
Config.set('kivy', 'window_title', 'Python Learning IDE')
Config.set('kivy', 'exit_on_escape', '0')

# === ИСПРАВЛЕНИЕ ДЁРГАНЬЯ КЛАВИАТУРЫ ===
Config.set('kivy', 'keyboard_mode', 'system')  # ← изменил
Window.softinput_mode = 'below_target'  # ← лучший режим для анимаций
Window.keyboard_anim_args = {'d': 0, 't': 'linear'}  # отключаем анимацию клавиатуры

Config.set('kivy', 'default_font', 'SourceBold')
Window.allow_screensaver = True


#Устанавливает обработчик ошибок
sys.excepthook = patched_excepthook



# ====================== ЭКСПОРТ ГЛОБАЛЬНЫХ ПЕРЕМЕННЫХ ======================
__all__ = ['HAS_PYGMENTS', 'PythonLexer', 'ThemeManager', 'SettingsManager']


class LanguageSelectMenu:
    """Подменю выбора языка"""
    LANGUAGE_NAMES = {
        'ru': 'Русский',
        'en': 'English',
    }

    def __init__(self, app):
        self.app = app
        self._dropdown = None

    def show(self, parent_button):
        theme = ThemeManager.get_theme()
        btn_bg = theme.get('action_bar_bg', theme['widget_bg'])
        self._dropdown = DropDown()
        self._dropdown.auto_width = False
        self._dropdown.width = dp(167)

        def style_container(dropdown, theme):
            if hasattr(dropdown, 'container'):
                container = dropdown.container
                container.canvas.before.clear()
                with container.canvas.before:
                    Color(*theme.get('action_bar_bg', theme['widget_bg']))
                    Rectangle(pos=container.pos, size=container.size)
                container.bind(
                    pos=lambda inst, val: self._update_container_bg(inst, theme),
                    size=lambda inst, val: self._update_container_bg(inst, theme)
                )

        self._dropdown.bind(on_open=lambda *args: style_container(self._dropdown, theme))

        from kivy.uix.behaviors import ButtonBehavior
        class MenuItem(ButtonBehavior, BoxLayout):
            pass

        for lang_code in sorted(TRANSLATIONS.keys()):
            lang_name = self.LANGUAGE_NAMES.get(lang_code, lang_code.upper())
            display_text = f"✓ {lang_name}" if lang_code == self.app.current_language else f"    {lang_name}"
            icon_text = lang_code.upper()
            box = MenuItem(orientation='horizontal', size_hint_y=None, height=dp(30), padding=(dp(8), 0), spacing=dp(5))
            icon_lbl = Label(text=icon_text, color=theme['text_color'], font_size=dp(11), font_name='SourceBold',
                             size_hint_x=None, width=dp(17), halign='center', valign='middle')
            box.add_widget(icon_lbl)
            lbl = Label(text=display_text, color=theme['text_color'], font_size=dp(15), font_name='SourceBold',
                        halign='left', valign='middle')
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

        def adjust_position(*args):
            win_width, win_height = Window.size
            if self._dropdown and self._dropdown.parent:
                if self._dropdown.x + self._dropdown.width > win_width:
                    self._dropdown.x = win_width - self._dropdown.width - dp(3)
                if self._dropdown.y < 0:
                    self._dropdown.y = parent_button.y + parent_button.height
                elif self._dropdown.y + self._dropdown.height > win_height:
                    self._dropdown.y = parent_button.y - self._dropdown.height

        Clock.schedule_once(adjust_position, 0.15)

    def _on_language_select(self, lang_code):
        # ВИБРАЦИЯ
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
            self.app._examples_cache = None
            try:
                with open(os.path.join(os.getcwd(), 'language.txt'), 'w') as f:
                    f.write(lang_code)
            except:
                pass
            SettingsManager.save_language(lang_code)
            self.app._update_ui_language()
            self.app.show_result_popup(
                f"{self.app.tr.get('language', 'Language')}: {self.LANGUAGE_NAMES.get(lang_code, lang_code.upper())}")

    def _update_container_bg(self, instance, theme):
        if not hasattr(instance, 'canvas'):
            return
        instance.canvas.before.clear()
        with instance.canvas.before:
            Color(*theme.get('action_bar_bg', theme['widget_bg']))
            Rectangle(pos=instance.pos, size=instance.size)

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

        def style_container(dropdown, theme_colors):
            if hasattr(dropdown, 'container'):
                container = dropdown.container
                container.canvas.before.clear()
                with container.canvas.before:
                    Color(*theme_colors.get('action_bar_bg', theme_colors['widget_bg']))
                    Rectangle(pos=container.pos, size=container.size)
                container.bind(
                    pos=lambda inst, val: self._update_container_bg(inst, theme_colors),
                    size=lambda inst, val: self._update_container_bg(inst, theme_colors)
                )

        self._dropdown.bind(on_open=lambda *args: style_container(self._dropdown, theme))

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
            box = MenuItem(orientation='horizontal', size_hint_y=None, height=dp(30), padding=(dp(8), 0), spacing=dp(5))
            icon = MDIcon(icon=icon_name, font_size=f"{dp(10)}sp", theme_text_color="Custom",
                          text_color=theme['text_color'], size_hint_x=None, width=dp(17))
            box.add_widget(icon)
            lbl = Label(text=display_text, color=theme['text_color'], font_size=dp(15), font_name='SourceBold',
                        halign='left', valign='middle')
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

        def adjust_position(*args):
            win_width, win_height = Window.size
            if self._dropdown and self._dropdown.parent:
                if self._dropdown.x + self._dropdown.width > win_width:
                    self._dropdown.x = win_width - self._dropdown.width - dp(3)
                if self._dropdown.y < 0:
                    self._dropdown.y = parent_button.y + parent_button.height
                elif self._dropdown.y + self._dropdown.height > win_height:
                    self._dropdown.y = parent_button.y - self._dropdown.height

        Clock.schedule_once(adjust_position, 0.15)

    def _on_theme_select(self, theme_id):
        # ВИБРАЦИЯ
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
                new_theme = ThemeManager.get_theme()
                Window.clearcolor = new_theme['window_bg']
                if hasattr(self.app, '_menu_dropdown'):
                    try:
                        self.app._create_menu_items(new_theme)
                    except:
                        pass
                self._show_restart_dialog(theme_id)

    def _show_restart_dialog(self, theme_id):
        tr = self.app.tr
        new_theme = ThemeManager.get_theme()
        available_themes = ThemeManager.get_available_themes()
        theme_title = available_themes.get(theme_id, theme_id)
        content = BoxLayout(orientation='vertical', padding=dp(7), spacing=dp(5))
        message = (
            f"{tr.get('theme_settings', 'Theme')}: {theme_title}\n\n"
            f"{tr.get('restart_for_syntax', 'Restart app to fully apply syntax highlighting?')}\n"
            f"{tr.get('restart_info', 'All tabs will be saved and restored.')}"
        )
        lbl = Label(text=message, font_name='SourceBold', color=new_theme['text_color'], font_size=dp(10),
                    halign='center', valign='middle', size_hint_y=0.7)
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
                           color=new_theme['text_color'], font_size=dp(9), on_release=lambda x: popup.dismiss())
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

    def _update_container_bg(self, instance, theme_colors):
        if not hasattr(instance, 'canvas'):
            return
        instance.canvas.before.clear()
        with instance.canvas.before:
            Color(*theme_colors.get('action_bar_bg', theme_colors['widget_bg']))
            Rectangle(pos=instance.pos, size=instance.size)

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
        self._font_menu = FontSelectMenu(app)

    def show(self, parent_button):
        theme = ThemeManager.get_theme()
        btn_bg = theme.get('action_bar_bg', theme['widget_bg'])
        self._dropdown = DropDown()
        self._dropdown.auto_width = False
        self._dropdown.width = dp(167)

        def style_container(dropdown, theme_colors):
            if hasattr(dropdown, 'container'):
                container = dropdown.container
                container.canvas.before.clear()
                with container.canvas.before:
                    Color(*theme_colors.get('action_bar_bg', theme_colors['widget_bg']))
                    Rectangle(pos=container.pos, size=container.size)
                container.bind(
                    pos=lambda inst, val: self._update_container_bg(inst, theme_colors),
                    size=lambda inst, val: self._update_container_bg(inst, theme_colors)
                )

        self._dropdown.bind(on_open=lambda *args: style_container(self._dropdown, theme))

        from kivymd.uix.label import MDIcon
        from kivy.uix.behaviors import ButtonBehavior
        class MenuItem(ButtonBehavior, BoxLayout):
            pass

        menu_items = [
            ('format-font', self.app.tr.get('editor_font', 'Шрифт'), lambda: self._open_font_submenu(parent_button)),
        ]

        for icon_name, text, handler in menu_items:
            box = MenuItem(orientation='horizontal', size_hint_y=None, height=dp(30), padding=(dp(8), 0), spacing=dp(5))
            icon = MDIcon(icon=icon_name, font_size=f"{dp(10)}sp", theme_text_color="Custom",
                          text_color=theme['text_color'], size_hint_x=None, width=dp(17))
            box.add_widget(icon)
            lbl = Label(text=text, color=theme['text_color'], font_size=dp(15), font_name='SourceBold', halign='left',
                        valign='middle')
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

        def adjust_position(*args):
            win_width, win_height = Window.size
            if self._dropdown and self._dropdown.parent:
                if self._dropdown.x + self._dropdown.width > win_width:
                    self._dropdown.x = win_width - self._dropdown.width - dp(3)
                if self._dropdown.y < 0:
                    self._dropdown.y = parent_button.y + parent_button.height
                elif self._dropdown.y + self._dropdown.height > win_height:
                    self._dropdown.y = parent_button.y - self._dropdown.height

        Clock.schedule_once(adjust_position, 0.15)

    def _on_item_click(self, handler):
        # ВИБРАЦИЯ
        if hasattr(self.app, 'vibrate_short'):
            self.app.vibrate_short()

        if self._dropdown:
            try:
                self._dropdown.dismiss()
            except:
                pass
        handler()

    def _open_font_submenu(self, parent_button):
        self._font_menu.show(parent_button)

    def _update_container_bg(self, instance, theme_colors):
        if not hasattr(instance, 'canvas'):
            return
        instance.canvas.before.clear()
        with instance.canvas.before:
            Color(*theme_colors.get('action_bar_bg', theme_colors['widget_bg']))
            Rectangle(pos=instance.pos, size=instance.size)

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
    """
    Подменю для выбора шрифта редактора кода.
    """

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

    FONT_FILES = {
        'JetBrainsMono': 'JetBrainsMono',
        'FiraCode': 'FiraCode',
        'CascadiaCode': 'CascadiaCode',
        'IBMPlexMono': 'IBMPlexMono',
        'NotoSansMono': 'NotoSansMono',
        'SourceCodePro': 'SourceCodePro',
        'DroidMono': 'DroidMono',
    }

    def __init__(self, app):
        self.app = app
        self._dropdown = None

    def show(self, parent_button):
        theme = ThemeManager.get_theme()
        tr = self.app.tr

        self._dropdown = DropDown()
        self._dropdown.auto_width = False
        self._dropdown.width = dp(167)

        def style_container(dropdown, theme):
            if hasattr(dropdown, 'container'):
                container = dropdown.container
                container.canvas.before.clear()
                with container.canvas.before:
                    Color(*theme.get('action_bar_bg', theme['widget_bg']))
                    Rectangle(pos=container.pos, size=container.size)
                container.bind(
                    pos=lambda inst, val: self._update_container_bg(inst, theme),
                    size=lambda inst, val: self._update_container_bg(inst, theme)
                )

        self._dropdown.bind(
            on_open=lambda *args: style_container(self._dropdown, theme))

        current_font = SettingsManager.get_font()
        btn_bg = theme.get('action_bar_bg', theme['widget_bg'])

        font_order = ['JetBrainsMono', 'FiraCode', 'CascadiaCode', 'IBMPlexMono', 'NotoSansMono', 'SourceCodePro',
                      'DroidMono']

        for font_key in font_order:
            font_name = self.FONT_NAMES.get(font_key, font_key)
            icon_name = self.FONT_ICONS.get(font_key, 'circle')

            if font_key == current_font:
                display_text = f"✓ {font_name}"
            else:
                display_text = f"    {font_name}"

            from kivymd.uix.label import MDIcon
            from kivy.uix.behaviors import ButtonBehavior

            class MenuItem(ButtonBehavior, BoxLayout):
                pass

            box = MenuItem(
                orientation='horizontal',
                size_hint_y=None,
                height=dp(30),
                padding=(dp(8), 0),
                spacing=dp(5),
            )

            icon = MDIcon(
                icon=icon_name,
                font_size=f"{dp(10)}sp",
                theme_text_color="Custom",
                text_color=theme['text_color'],
                size_hint_x=None,
                width=dp(17),
            )
            box.add_widget(icon)

            lbl = Label(
                text=display_text,
                color=theme['text_color'],
                font_size=dp(15),
                font_name='SourceBold',
                halign='left',
                valign='middle',
            )
            box.add_widget(lbl)

            box.canvas.before.clear()
            with box.canvas.before:
                Color(*btn_bg)
                Rectangle(pos=box.pos, size=box.size)
                Color(btn_bg[0] + 0.08, btn_bg[1] + 0.08, btn_bg[2] + 0.08, 1)
                Line(rectangle=(box.pos[0], box.pos[1],
                                box.size[0], box.size[1]), width=dp(0.5))

            box.bind(
                pos=lambda inst, val, bg=btn_bg: self._update_btn_bg(inst, bg),
                size=lambda inst, val, bg=btn_bg: self._update_btn_bg(inst, bg)
            )

            box.bind(on_release=lambda instance,
                                       fk=font_key: self._on_font_select(fk))
            self._dropdown.add_widget(box)

        Clock.schedule_once(lambda dt: self._dropdown.open(parent_button), 0.1)

        def adjust_position(*args):
            win_width, win_height = Window.size
            if self._dropdown and self._dropdown.parent:
                if self._dropdown.x + self._dropdown.width > win_width:
                    self._dropdown.x = win_width - self._dropdown.width - dp(3)
                if self._dropdown.y < 0:
                    self._dropdown.y = parent_button.y + parent_button.height
                elif self._dropdown.y + self._dropdown.height > win_height:
                    self._dropdown.y = parent_button.y - self._dropdown.height

        Clock.schedule_once(adjust_position, 0.15)

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
        font_file = self.FONT_FILES.get(font_key, 'DroidMono')

        if not hasattr(self.app, 'tab_manager'):
            return

        for tab in self.app.tab_manager.tabs:
            editor = tab.get('editor')
            if editor and hasattr(editor, 'text_input'):
                editor.text_input.font_name = font_file
                if hasattr(editor, 'force_full_font_reset'):
                    Clock.schedule_once(editor.force_full_font_reset, 0.15)

        SettingsManager.save_font(font_key)
        self.app.show_result_popup(
            f"✓ Шрифт изменён: {self.FONT_NAMES.get(font_key, font_key)}")

    def _update_container_bg(self, instance, theme):
        if not hasattr(instance, 'canvas'):
            return
        instance.canvas.before.clear()
        with instance.canvas.before:
            Color(*theme.get('action_bar_bg', theme['widget_bg']))
            Rectangle(pos=instance.pos, size=instance.size)

    def _update_btn_bg(self, instance, bg_color):
        if not hasattr(instance, 'canvas'):
            return
        instance.canvas.before.clear()
        with instance.canvas.before:
            Color(*bg_color)
            Rectangle(pos=instance.pos, size=instance.size)
            Color(bg_color[0] + 0.08, bg_color[1] +
                  0.08, bg_color[2] + 0.08, 1)
            Line(rectangle=(instance.pos[0], instance.pos[1],
                            instance.size[0], instance.size[1]), width=dp(0.5))


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
        theme = ThemeManager.get_theme()  # ← НАПРЯМУЮ
        tr = self._get_translations()
        current_theme = ThemeManager.get_theme_name()
        styles = SyntaxStyleManager.get_styles_by_theme(current_theme)
        style_info = SyntaxStyleManager.get_style_display_info()
        current_style = SyntaxStyleManager.get_current_style()

        content = BoxLayout(orientation='vertical', padding=dp(5), spacing=dp(3))
        header_text = tr.get('syntax_header', 'Выберите стиль подсветки:')
        content.add_widget(
            Label(text=header_text, size_hint_y=None, height=dp(30), color=theme.get('text_color', (0, 0, 0, 1)),
                  font_size=dp(17), halign='left', valign='middle'))

        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False, do_scroll_y=True)
        styles_list = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(1.5), padding=[0, dp(2)])
        styles_list.bind(minimum_height=styles_list.setter('height'))

        from kivymd.uix.label import MDIcon
        from kivy.uix.behaviors import ButtonBehavior
        btn_bg = theme.get('popup_bg', (1.0, 1.0, 1.0, 1))  # ← фон как у попапа

        for style_name in styles:
            info = style_info.get(style_name, {'name': style_name.replace('_', ' ').title(), 'type': 'unknown'})
            prefix = '✓ ' if style_name == current_style else '  '
            display_name = f"{prefix}{info['name']}"

            class MenuItem(ButtonBehavior, BoxLayout):
                pass

            box = MenuItem(orientation='horizontal', size_hint_y=None, height=dp(30), padding=(dp(8), 0), spacing=dp(4))
            icon = MDIcon(icon='weather-night' if info['type'] == 'dark' else 'weather-sunny', font_size=f"{dp(7)}sp",
                          theme_text_color="Custom", text_color=theme.get('text_color', (0, 0, 0, 1)), size_hint_x=None,
                          width=dp(13))
            box.add_widget(icon)
            lbl = Label(text=display_name, color=theme.get('text_color', (0, 0, 0, 1)), font_size=dp(15),
                        font_name='SourceBold', halign='left', valign='middle')
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
                           background_color=theme.get('widget_bg', (0.843, 0.816, 1.0, 1)), background_normal='',
                           background_down='', color=theme.get('text_color', (0, 0, 0, 1)), font_size=dp(13),
                           on_release=lambda x: self._destroy_all_windows())
        content.add_widget(btn_close)

        title = tr.get('syntax_menu_title', 'Стиль подсветки')
        self._popup = Popup(
            title=title,
            title_color=theme.get('popup_title', (0, 0, 0, 1)),
            separator_color=theme.get('popup_separator', (0.25, 0.25, 0.25, 1)),
            background='',
            background_color=theme.get('popup_bg', (1.0, 1.0, 1.0, 1)),
            content=content,
            size_hint=(0.92, 0.85),
            auto_dismiss=False
        )
        self._popup.open()

    def _open_preview_after_close(self, style_name):
        self._close_menu()
        Clock.schedule_once(lambda dt: self._open_preview(style_name), 0.3)

    def _open_preview(self, style_name):
        self._close_preview()
        theme = ThemeManager.get_theme()  # ← НАПРЯМУЮ из ThemeManager
        tr = self._get_translations()
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
                      text_color=theme.get('text_color', (0.85, 0.88, 0.90, 1)), size_hint_x=None, width=dp(20))
        header_box.add_widget(icon)
        type_str = 'Тёмный стиль' if style_info['type'] == 'dark' else 'Светлый стиль'
        header_lbl = Label(text=f"[b]{style_info['name']}[/b] — {type_str}", markup=True,
                           color=theme.get('text_color', (0.85, 0.88, 0.90, 1)), font_size=dp(13),
                           font_name='SourceBold', halign='left', valign='middle')
        header_box.add_widget(header_lbl)
        content.add_widget(header_box)

        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False, do_scroll_y=True)

        # Обёртка с фоном редактора
        editor_bg_color = theme.get('editor_bg', (1.0, 1.0, 1.0, 1))
        preview_box = FloatLayout(size_hint=(1, None))
        with preview_box.canvas.before:
            Color(*editor_bg_color)
            self._preview_bg_rect = Rectangle(pos=preview_box.pos, size=preview_box.size)
        preview_box.bind(pos=self._update_preview_bg, size=self._update_preview_bg)

        preview_label = Label(
            text=highlighted_text,
            markup=True,
            font_size=dp(13),
            font_name='DejaVuSans',
            color=theme.get('editor_text', (0, 0, 0, 1)),
            size_hint=(1, None),
            padding=(dp(5), dp(5)),
            halign='left',
            valign='top',
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
                          background_normal='', background_down='', color=theme.get('text_color', (0, 0, 0, 1)),
                          font_size=dp(13), on_release=lambda x: self._back_to_menu())
        btn_cancel = Button(text=cancel_text, background_color=theme.get('widget_bg', (0.14, 0.14, 0.15, 1)),
                            background_normal='', background_down='', color=theme.get('text_color', (0, 0, 0, 1)),
                            font_size=dp(13), on_release=lambda x: self._destroy_all_windows())
        btn_apply = Button(text=apply_text, background_color=theme.get('btn_success_bg', (0.2, 0.5, 0.2, 1)),
                           background_normal='', background_down='', color=(1, 1, 1, 1), font_size=dp(13),
                           on_release=lambda x: self._apply_style(style_name))
        btn_layout.add_widget(btn_back)
        btn_layout.add_widget(btn_cancel)
        btn_layout.add_widget(btn_apply)
        content.add_widget(btn_layout)

        title = tr.get('syntax_preview', 'Предпросмотр: ') + style_info['name']

        popup_bg_color = theme.get('editor_bg', (1.0, 1.0, 1.0, 1))
        self._preview_popup = Popup(
            title=title,
            title_color=theme.get('popup_title', (0, 0, 0, 1)),
            separator_color=theme.get('popup_separator', (0.25, 0.25, 0.25, 1)),
            background='',
            background_color=popup_bg_color,
            content=content,
            size_hint=(0.95, 0.88),
            auto_dismiss=False
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
        if hasattr(self.app, '_save_autosave'):
            self.app._save_autosave()
        info = SyntaxStyleManager.get_style_display_info()
        style_display = info.get(style_name, {}).get('name', style_name)
        self._show_restart_dialog(style_display)

    def _show_restart_dialog(self, style_display):
        tr = self._get_translations()
        theme = ThemeManager.get_theme()  # ← НАПРЯМУЮ
        content = BoxLayout(orientation='vertical', padding=dp(7), spacing=dp(5))
        message = (
            f"{tr.get('syntax_highlight', 'Подсветка')}: {style_display}\n\n"
            f"{tr.get('restart_for_syntax', 'Перезапустить приложение для полной смены подсветки синтаксиса?')}\n"
            f"{tr.get('restart_info', 'Все вкладки будут сохранены и восстановлены.')}"
        )
        lbl = Label(text=message, font_name='SourceBold', color=theme.get('text_color', (0, 0, 0, 1)), font_size=dp(10),
                    halign='center', valign='middle', size_hint_y=0.7)
        lbl.bind(width=lambda instance, value: setattr(instance, 'text_size', (value, None)))
        content.add_widget(lbl)
        btn_layout = BoxLayout(size_hint_y=0.3, spacing=dp(4))
        popup = Popup(
            title=tr.get('syntax_menu_title', 'Стиль подсветки'),
            title_color=theme.get('popup_title', (0, 0, 0, 1)),
            separator_color=theme.get('popup_separator', (0.25, 0.25, 0.25, 1)),
            background='',
            background_color=theme.get('popup_bg', (1.0, 1.0, 1.0, 1)),
            content=content,
            size_hint=(0.85, 0.35),
            auto_dismiss=False
        )
        btn_restart = Button(text=tr.get('restart_btn', 'Перезапустить'), font_name='SourceBold',
                             background_color=theme.get('btn_success_bg', (0.2, 0.5, 0.2, 1)), background_normal='',
                             background_down='', color=(1, 1, 1, 1), font_size=dp(9),
                             on_release=lambda x: self._do_restart(popup))
        btn_later = Button(text=tr.get('later_btn', 'Позже'), font_name='SourceBold',
                           background_color=theme.get('widget_bg', (0.843, 0.816, 1.0, 1)), background_normal='',
                           background_down='', color=theme.get('text_color', (0, 0, 0, 1)), font_size=dp(9),
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

    def _get_theme(self):
        try:
            if hasattr(self.app, 'get_theme'):
                return ThemeManager.get_theme()
        except:
            pass
        return {'widget_bg': (0.141, 0.145, 0.149, 1), 'text_color': (0.85, 0.88, 0.90, 1),
                'editor_bg': (0.188, 0.204, 0.251, 1), 'editor_text': (0.95, 0.95, 0.95, 1),
                'popup_title': (0.85, 0.88, 0.90, 1), 'popup_separator': (0.25, 0.25, 0.25, 1),
                'popup_bg': (0.188, 0.204, 0.251, 1), 'btn_success_bg': (0.2, 0.5, 0.2, 1)}

    def _get_translations(self):
        if hasattr(self.app, 'tr'):
            return self.app.tr
        return {}

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

        def style_container(dropdown, theme_colors):
            if hasattr(dropdown, 'container'):
                container = dropdown.container
                container.canvas.before.clear()
                with container.canvas.before:
                    Color(*theme_colors.get('action_bar_bg', theme_colors['widget_bg']))
                    Rectangle(pos=container.pos, size=container.size)
                container.bind(
                    pos=lambda inst, val: self._update_container_bg(inst, theme_colors),
                    size=lambda inst, val: self._update_container_bg(inst, theme_colors)
                )

        self._dropdown.bind(on_open=lambda *args: style_container(self._dropdown, theme))

        from kivymd.uix.label import MDIcon
        from kivy.uix.behaviors import ButtonBehavior
        class MenuItem(ButtonBehavior, BoxLayout):
            pass

        menu_items = [
            ('translate', 'select_language', lambda: self._open_language_submenu(parent_button)),
            ('theme-light-dark', 'theme_settings', lambda: self._open_theme_submenu(parent_button)),
            ('palette', 'syntax_highlight', lambda: self._open_syntax_submenu(parent_button)),
            # ('key', 'api_settings', lambda: self._open_api_settings()),
            ('tune', 'editor_settings', lambda: self._open_editor_submenu(parent_button)),
        ]

        for icon_name, item_key, handler in menu_items:
            box = MenuItem(orientation='horizontal', size_hint_y=None, height=dp(30), padding=(dp(8), 0), spacing=dp(5))
            icon = MDIcon(icon=icon_name, font_size=f"{dp(10)}sp", theme_text_color="Custom",
                          text_color=theme['text_color'], size_hint_x=None, width=dp(17))
            box.add_widget(icon)
            lbl = Label(text=self.app.tr.get(item_key, item_key), color=theme['text_color'], font_size=dp(15),
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
            box.bind(on_release=lambda instance, h=handler: self._on_item_click(h))
            self._dropdown.add_widget(box)

        Clock.schedule_once(lambda dt: self._dropdown.open(parent_button), 0.1)

        def adjust_position(*args):
            win_width, win_height = Window.size
            if self._dropdown and self._dropdown.parent:
                if self._dropdown.x + self._dropdown.width > win_width:
                    self._dropdown.x = win_width - self._dropdown.width - dp(3)
                if self._dropdown.y < 0:
                    self._dropdown.y = parent_button.y + parent_button.height
                elif self._dropdown.y + self._dropdown.height > win_height:
                    self._dropdown.y = parent_button.y - self._dropdown.height

        Clock.schedule_once(adjust_position, 0.15)

    def _on_item_click(self, handler):
        if self._dropdown:
            try:
                self._dropdown.dismiss()
            except:
                pass
        handler()

    def _open_language_submenu(self, parent_button):
        # ВИБРАЦИЯ
        if hasattr(self.app, 'vibrate_short'):
            self.app.vibrate_short()

        self._language_menu.show(parent_button)

    def _open_theme_submenu(self, parent_button):
        # ВИБРАЦИЯ
        if hasattr(self.app, 'vibrate_short'):
            self.app.vibrate_short()

        self._theme_menu.show(parent_button)

    def _open_syntax_submenu(self, parent_button):
        # ВИБРАЦИЯ
        if hasattr(self.app, 'vibrate_short'):
            self.app.vibrate_short()

        if not hasattr(self, '_syntax_menu'):
            self._syntax_menu = SyntaxHighlightMenu(self.app)
        self._syntax_menu.show(parent_button)

    def _open_editor_submenu(self, parent_button):
        # ВИБРАЦИЯ
        if hasattr(self.app, 'vibrate_short'):
            self.app.vibrate_short()

        self._editor_menu.show(parent_button)

    def _open_api_settings(self):
        # ВИБРАЦИЯ
        if hasattr(self.app, 'vibrate_short'):
            self.app.vibrate_short()

        self.app.show_api_key_settings()

    def _update_container_bg(self, instance, theme_colors):
        if not hasattr(instance, 'canvas'):
            return
        instance.canvas.before.clear()
        with instance.canvas.before:
            Color(*theme_colors.get('action_bar_bg', theme_colors['widget_bg']))
            Rectangle(pos=instance.pos, size=instance.size)

    def _update_btn_bg(self, instance, bg_color):
        if not hasattr(instance, 'canvas'):
            return
        instance.canvas.before.clear()
        with instance.canvas.before:
            Color(*bg_color)
            Rectangle(pos=instance.pos, size=instance.size)
            Color(bg_color[0] + 0.08, bg_color[1] + 0.08, bg_color[2] + 0.08, 1)
            Line(rectangle=(instance.pos[0], instance.pos[1], instance.size[0], instance.size[1]), width=dp(0.5))


class ActivityResultHandler:
    """Обработчик результатов активности для Android"""

    @staticmethod
    def start_activity_for_result(intent, request_code, callback):
        """Запускает активность и сохраняет callback"""
        global _pending_file_callback

        try:
            from jnius import autoclass, cast
            from android import activity

            PythonActivity = autoclass('org.kivy.android.PythonActivity')

            # Сохраняем callback
            _pending_file_callback = callback

            # Запускаем активность
            current_activity = cast('android.app.Activity', PythonActivity.mActivity)
            current_activity.startActivityForResult(intent, request_code)

            # Привязываем обработчик к активности
            ActivityResultHandler._bind_result_handler()

        except Exception as e:
            log_error(f"startActivityForResult error: {e}")
            if callback:
                callback(None, None, None)

    @staticmethod
    def _bind_result_handler():
        """Привязывает обработчик результата к активности"""
        try:
            from jnius import autoclass, PythonJavaClass, java_method, cast
            from android import activity

            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            current_activity = cast('android.app.Activity', PythonActivity.mActivity)

            # Создаём слушатель
            class ActivityResultListener(PythonJavaClass):
                __javainterfaces__ = ['android/content/DialogInterface$OnClickListener']

                @java_method('(Landroid/content/DialogInterface;I)V')
                def onClick(self, dialog, which):
                    pass

            # Проверяем, есть ли уже обработчик
            if not hasattr(current_activity, '_kivy_result_handler'):
                # Создаём и сохраняем обработчик
                handler = ActivityResultListener()
                current_activity._kivy_result_handler = handler

        except Exception as e:
            log_error(f"Bind result handler error: {e}")


class PythonLearningApp(MDApp):
    """Главный класс приложения Python Learning App"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_language = self._load_language()
        self.tr = TRANSLATIONS[self.current_language]
        self.history = []
        self._max_history = 20
        self._popup = None
        self._current_popup_type = None
        self._exit_popup = None
        self.current_input_widget = None
        self.search_popup = None
        self.saved_api_key = ''
        self.current_theme_name = 'dark'
        self.code_executor = CodeExecutor()
        self.tab_manager = TabManager()
        self.tab_manager.app = self
        self._settings_menu = None
        self._current_file = None
        self._last_autosave_time = 0
        self._has_unsaved_changes = False
        self._original_title = "Python Learning App"
        self.title = self._original_title
        self._autosave_file = self._get_autosave_path()
        self._restore_on_start = True
        self._examples_cache = None
        self._examples_loading = False
        self._ui_ready = False
        self._pending_operations = []
        self._cleanup_scheduled = False
        self._code_running = False
        self._current_file_operation = None
        # Инициализация файлового менеджера
        self.file_manager = FileManager(self)
        self._current_file_popup = None

        # === НОВОЕ: Инициализация пути для файлового менеджера ===
        self.current_path = self.get_external_storage_path()

        ThemeManager.apply_saved_theme()
        ThemeManager.register(self)
        self._load_api_key_async()
        self.splash_finished = False

    def get_external_storage_path(self):
        """Возвращает путь к основному хранилищу на Android"""
        if platform == 'android':
            try:
                # Импортируем только на Android
                from android.storage import primary_external_storage_path
                path = primary_external_storage_path()
                if path and os.path.exists(path):
                    return path
            except Exception as e:
                log_error(f"primary_external_storage_path failed: {e}")

            # Fallback пути
            fallback_paths = [
                '/storage/emulated/0',
                '/sdcard',
                '/storage/emulated/0/Download',
                '/storage/emulated/0/Documents'
            ]
            for p in fallback_paths:
                if os.path.exists(p):
                    return p

            return '/storage/emulated/0'

        # Для ПК / тестирования
        return os.path.expanduser('~')

    def _load_language(self):
        try:
            lang_file = os.path.join(os.getcwd(), 'language.txt')
            if os.path.exists(lang_file):
                with open(lang_file, 'r') as f:
                    lang = f.read().strip()
                    if lang in ['ru', 'en']:
                        return lang
        except:
            pass
        try:
            lang = SettingsManager.get_language()
            if lang in ['ru', 'en']:
                return lang
        except:
            pass
        return 'en'

    def build(self):
        main_widget = self._create_main_widget()
        sm = ScreenManager()

        splash = AnimatedSplashScreen(self, name='splash')
        sm.add_widget(splash)

        main_screen = Screen(name='main')
        main_screen.add_widget(main_widget)
        sm.add_widget(main_screen)

        sm.current = 'splash'

        Window.bind(on_resize=self.on_resize)

        # Только ОДИН РАЗ привязываем обработчик
        if platform == 'android':
            try:
                from android import activity
                activity.bind(on_activity_result=self.on_activity_result)
            except Exception as e:
                print(f"[ERROR] Failed to bind: {e}")

        # ===== ПРОГРЕВ ПОДСВЕТКИ СИНТАКСИСА (убираем первый фриз) =====
        def warmup_pygments(dt):
            try:
                from pygments.lexers import PythonLexer
                from pygments.styles import get_style_by_name
                # Загружаем стиль по умолчанию в фоне
                default_style = ThemeManager.get_syntax_style()
                get_style_by_name(default_style)
                # Создаём временный лексер (он закеширует RegexLexer)
                lexer = PythonLexer()
                # Простейшая проверка, чтобы Pygments "прогрелся"
                list(lexer.get_tokens("def foo(): pass"))
                print("[OK] Pygments warmed up successfully")
            except Exception as e:
                print(f"[WARN] Pygments warmup failed: {e}")

        # Запускаем прогрев через 0.5 секунды после старта приложения
        Clock.schedule_once(warmup_pygments, 0.5)
        # =============================================================

        return sm

    def _create_main_widget(self):
        self._load_fonts()
        self._request_android_permissions()
        self._request_storage_permission()
        self.check_and_request_manage_storage()
        Window.keyboard_anim_args = {'d': 0.2, 't': 'in_out_quad'}
        Window.bind(on_key_down=self._keyboard_handler)
        theme = ThemeManager.get_theme()
        main_layout = BoxLayout(orientation='vertical', padding=dp(3), spacing=dp(3))

        with main_layout.canvas.before:
            self.bg_color = Color(*theme['app_bg'])
            self.bg_rect = Rectangle(size=main_layout.size, pos=main_layout.pos)
        main_layout.bind(size=self._update_bg, pos=self._update_bg)

        self.top_section = self._create_top_bar(theme)
        main_layout.add_widget(self.top_section)

        self.action_bar = MyActionBar(None)
        self.action_bar.app = self
        main_layout.add_widget(self.action_bar)

        self.symbol_bar = MySymbolScrollBar(None)
        self.symbol_bar.app = self
        main_layout.add_widget(self.symbol_bar)

        tab_bar = self.tab_manager.create_tab_bar(theme)
        main_layout.add_widget(tab_bar)

        Clock.schedule_once(self._apply_saved_syntax_style, 0.5)

        self.autocomplete = AutoCompleteWidget()
        self.autocomplete.code_input = None
        main_layout.add_widget(self.autocomplete)

        tabs_loaded = self.tab_manager.load_all_tabs()
        if not tabs_loaded:
            self.editor = self.tab_manager.add_tab(title=self.tr.get('untitled_tab', 'New'), text="")
            self.code_input = self.editor.text_input
            self.action_bar.text_input = self.code_input
            self.symbol_bar.text_input = self.code_input
            self.autocomplete.code_input = self.code_input
            self._set_initial_empty_lines()
            self._restore_on_start = True
            saved_font = SettingsManager.get_font()
            font_files = {
                'DroidMono': 'DroidMono',
                'JetBrainsMono': 'JetBrainsMono',
                'FiraCode': 'FiraCode',
                'CascadiaCode': 'CascadiaCode',
                'IBMPlexMono': 'IBMPlexMono',
                'NotoSansMono': 'NotoSansMono',
                'SourceCodePro': 'SourceCodePro',
            }
            if saved_font in font_files:
                self.code_input.font_name = font_files[saved_font]

            def set_cursor_to_first_line(dt):
                try:
                    if hasattr(self, 'code_input') and self.code_input:
                        self.code_input.cursor = (0, 0)
                        self.code_input.focus = True
                except:
                    pass

            Clock.schedule_once(set_cursor_to_first_line, 0.5)
            Clock.schedule_once(set_cursor_to_first_line, 0.7)
        else:
            self.editor = self.tab_manager.get_active_editor()
            self.code_input = self.editor.text_input
            self.action_bar.text_input = self.code_input
            self.symbol_bar.text_input = self.code_input
            self.autocomplete.code_input = self.code_input
            self._current_file = self.tab_manager.get_active_file()
            self._has_unsaved_changes = False
            self._update_title_saved()
            self._restore_on_start = False
            saved_font = SettingsManager.get_font()
            font_files = {
                'DroidMono': 'DroidMono',
                'JetBrainsMono': 'JetBrainsMono',
                'FiraCode': 'FiraCode',
                'CascadiaCode': 'CascadiaCode',
                'IBMPlexMono': 'IBMPlexMono',
                'NotoSansMono': 'NotoSansMono',
                'SourceCodePro': 'SourceCodePro',
            }
            if saved_font in font_files:
                self.code_input.font_name = font_files[saved_font]

            def set_cursor_to_first_line(dt):
                try:
                    if hasattr(self, 'code_input') and self.code_input:
                        self.code_input.cursor = (0, 0)
                        self.code_input.focus = True
                except:
                    pass

            Clock.schedule_once(set_cursor_to_first_line, 0.5)
            Clock.schedule_once(set_cursor_to_first_line, 0.7)

        self.editor_container = BoxLayout()
        self.editor_container.add_widget(self.editor)
        main_layout.add_widget(self.editor_container)

        self._setup_autosave()
        self._ui_ready = True
        self._process_pending_operations()

        main_layout.bind(on_touch_down=self._on_main_touch_down)
        Clock.schedule_once(self._apply_saved_syntax_style, 0.5)

        root_layout = FloatLayout()
        root_layout.add_widget(main_layout)

        from kivymd.uix.label import MDIcon
        from kivy.uix.behaviors import ButtonBehavior
        category = get_screen_category()
        if category == 'tablet':
            run_btn_size = dp(90)
            margin_right = dp(12)
            margin_bottom = dp(90)
            icon_size = dp(32)
        elif category == 'large_phone':
            run_btn_size = dp(78)
            margin_right = dp(10)
            margin_bottom = dp(78)
            icon_size = dp(28)
        else:
            run_btn_size = dp(67)
            margin_right = dp(8)
            margin_bottom = dp(67)
            icon_size = dp(23)

        class RunButton(ButtonBehavior, FloatLayout):
            pass

        self.run_btn = RunButton(size_hint=(None, None), size=(run_btn_size, run_btn_size))
        self.run_btn.always_release = True

        if theme.get('name') == 'dark':
            bg_color = theme.get('run_btn_bg', (0.85, 0.88, 0.90, 1))
            icon_color = theme.get('run_btn_text', (0.18, 0.18, 0.19, 1))
        else:
            bg_color = theme.get('run_btn_bg', (0.596, 0.486, 1.0, 1))
            icon_color = theme.get('run_btn_text', (0, 0, 0, 1))

        def draw_round_btn(btn, *args):
            btn.canvas.before.clear()
            with btn.canvas.before:
                Color(*bg_color)
                Ellipse(pos=btn.pos, size=btn.size)

        self.run_btn.bind(pos=draw_round_btn, size=draw_round_btn)
        play_icon = MDIcon(icon='play', font_size=f"{dp(icon_size)}sp", theme_text_color="Custom",
                           text_color=icon_color,
                           pos_hint={"center_x": 0.5, "center_y": 0.5})
        self.run_btn.add_widget(play_icon)

        def set_btn_pos(instance, value):
            x = root_layout.width - run_btn_size - margin_right
            y = margin_bottom
            self.run_btn.pos = (x, y)

        root_layout.bind(size=set_btn_pos, pos=set_btn_pos)
        Clock.schedule_once(lambda dt: set_btn_pos(None, None), 0.3)
        self.run_btn.bind(on_press=self.run_code)
        root_layout.add_widget(self.run_btn)

        if platform == 'android':
            def lock_window_position(dt):
                try:
                    Window.top = 0
                    Window.update_viewport()
                except:
                    pass

            Clock.schedule_once(lock_window_position, 0.2)
            Clock.schedule_once(lock_window_position, 0.5)
            Clock.schedule_once(lock_window_position, 1.0)

        Clock.schedule_once(self._fix_layout_on_start, 0.5)

        return root_layout

    def on_splash_finished(self):
        """Вызывается, когда заставка завершила работу"""
        self.splash_finished = True
        print("✓ Splash screen finished, app ready")

    def _request_android_permissions(self):
        try:
            from android.permissions import request_permissions, Permission
            permissions = [Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE]
            # MANAGE_EXTERNAL_STORAGE может не быть, добавляем осторожно
            if hasattr(Permission, 'MANAGE_EXTERNAL_STORAGE'):
                permissions.append(Permission.MANAGE_EXTERNAL_STORAGE)
            request_permissions(permissions)
        except:
            pass

    def check_and_request_manage_storage(self):
        """Проверяет и запрашивает разрешение MANAGE_EXTERNAL_STORAGE (Android 11+)"""
        if platform != 'android':
            return

        try:
            from jnius import autoclass
            from android.permissions import request_permissions, Permission
            from android import activity

            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            activity = PythonActivity.mActivity

            # Получаем версию Android
            Build = autoclass('android.os.Build$VERSION')
            if Build.SDK_INT >= 30:  # Android 11+
                # Проверяем, есть ли уже разрешение
                Environment = autoclass('android.os.Environment')
                if not Environment.isExternalStorageManager():
                    # Запрашиваем разрешение
                    Intent = autoclass('android.content.Intent')
                    Settings = autoclass('android.provider.Settings')
                    intent = Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION)
                    intent.setData(autoclass('android.net.Uri').parse("package:" + activity.getPackageName()))
                    activity.startActivityForResult(intent, 1005)
        except Exception as e:
            print(f"MANAGE_EXTERNAL_STORAGE error: {e}")

    def select_folder_via_saf(self):
        """Открывает системный диалог выбора папки (SAF)"""
        if platform != 'android':
            return

        try:
            from jnius import autoclass, cast
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Intent = autoclass('android.content.Intent')

            intent = Intent(Intent.ACTION_OPEN_DOCUMENT_TREE)
            current_activity = cast('android.app.Activity', PythonActivity.mActivity)
            current_activity.startActivityForResult(intent, 1004)
        except Exception as e:
            self.show_result_popup(f"SAF error: {e}")

    def on_start(self):
        if platform == 'android':
            from android.permissions import request_permissions, Permission
            from kivy.clock import Clock

            def perm_callback(permissions, results):
                if all(results):
                    Clock.schedule_once(lambda dt: self.refresh_file_list(), 1.0)
                else:
                    self.show_result_popup("Нет доступа к файлам!\nРазрешите в настройках приложения.")

            request_permissions([
                Permission.READ_EXTERNAL_STORAGE,
                Permission.WRITE_EXTERNAL_STORAGE
            ], perm_callback)

    def _fix_layout_on_start(self, dt):
        try:
            Window.update_viewport()
            if hasattr(self, 'editor') and self.editor:
                self.editor._update_text_width(0)
        except:
            pass

    def on_resize(self, window, width, height):
        """Обработчик изменения размера окна (при повороте экрана)"""
        Clock.schedule_once(lambda dt: self._refresh_ui_after_resize(), 0.1)

    def _refresh_ui_after_resize(self):
        """Обновляет UI после поворота экрана"""

        reset_screen_cache()

        # ========== ОБНОВЛЯЕМ ВЕРХНИЕ ПАНЕЛИ (Примеры и Меню) ==========
        if hasattr(self, '_update_top_panels'):
            self._update_top_panels()
        elif hasattr(self, 'top_section') and hasattr(self, '_create_top_bar'):
            # Если нет отдельного метода, пересоздаём панели
            theme = ThemeManager.get_theme()
            old_top = self.top_section
            new_top = self._create_top_bar(theme)

            if old_top and old_top.parent:
                index = old_top.parent.children.index(old_top)
                old_top.parent.remove_widget(old_top)
                old_top.parent.add_widget(new_top, index=index)

            self.top_section = new_top

        # Обновляем спиннер, если он существует отдельно
        if hasattr(self, 'spinner'):
            try:
                self.spinner.values = self._get_example_titles()
                self.spinner.text = self.tr.get('examples', 'Примеры')
                theme = ThemeManager.get_theme()
                self.spinner.background_color = theme['spinner_bg']
                self.spinner.color = theme['spinner_text']
            except:
                pass

        # Обновляем кнопку меню
        if hasattr(self, 'menu_button'):
            try:
                theme = ThemeManager.get_theme()
                self.menu_button.background_color = theme.get('menu_btn_bg', theme['widget_bg'])
                self.menu_button.color = theme.get('menu_btn_text', theme['text_color'])
            except:
                pass

        # Обновляем кнопку запуска
        if hasattr(self, 'run_btn'):
            category = get_screen_category()
            if category == 'tablet':
                run_btn_size = dp(90)
                margin_bottom = dp(90)
                icon_size = dp(32)
            elif category == 'large_phone':
                run_btn_size = dp(78)
                margin_bottom = dp(78)
                icon_size = dp(28)
            else:
                run_btn_size = dp(67)
                margin_bottom = dp(67)
                icon_size = dp(23)

            self.run_btn.size = (run_btn_size, run_btn_size)
            for child in self.run_btn.children:
                if hasattr(child, 'font_size'):
                    child.font_size = f"{dp(icon_size)}sp"

            # Обновляем позицию кнопки
            if hasattr(self, 'root_layout'):
                x = self.root_layout.width - run_btn_size - dp(12)
                y = margin_bottom
                self.run_btn.pos = (x, y)

            # Восстанавливаем иконку на кнопке запуска
            if hasattr(self, 'play_icon') and self.play_icon not in self.run_btn.children:
                self.run_btn.add_widget(self.play_icon)
            if hasattr(self, 'play_icon'):
                self.play_icon.icon = 'play'

        # Обновляем панель вкладок
        if hasattr(self, 'tab_manager'):
            self.tab_manager.max_visible = get_tab_count()
            self.tab_manager._update_tab_bar()
            theme = ThemeManager.get_theme()
            self.tab_manager.update_tab_bar_theme(theme)

        # Обновляем action_bar (панель с кнопками undo/redo и т.д.)
        if hasattr(self, 'action_bar'):
            try:
                category = get_screen_category()
                if category == 'tablet':
                    self.action_bar.height = dp(52)
                    self.action_bar.spacing = dp(18)
                elif category == 'large_phone':
                    self.action_bar.height = dp(45)
                    self.action_bar.spacing = dp(15)
                else:
                    self.action_bar.height = dp(38)
                    self.action_bar.spacing = dp(12)
            except:
                pass

        # Обновляем symbol_bar (панель с символами)
        if hasattr(self, 'symbol_bar'):
            try:
                category = get_screen_category()
                if category == 'tablet':
                    self.symbol_bar.height = dp(42)
                    self.symbol_bar.spacing = dp(4)
                elif category == 'large_phone':
                    self.symbol_bar.height = dp(36)
                    self.symbol_bar.spacing = dp(3)
                else:
                    self.symbol_bar.height = dp(30)
                    self.symbol_bar.spacing = dp(2)
            except:
                pass

        # Обновляем панель номеров строк
        if hasattr(self, 'editor') and self.editor:
            Clock.schedule_once(self.editor._force_line_panel_refresh, 0.2)
            Clock.schedule_once(lambda dt: self.editor._update_line_panel(), 0.3)
            Clock.schedule_once(lambda dt: self.editor._update_text_width(), 0.4)

    def on_pause(self):
        self.tab_manager.save_all_tabs()
        return True

    def on_resume(self):
        """Вызывается при возврате в приложение"""
        reset_screen_cache()  # Сбросить кэш категории экрана
        Clock.schedule_once(lambda dt: self._refresh_ui_after_resize(), 0.1)
        Clock.schedule_once(lambda dt: self._restore_run_button(), 0.2)
        return True

    def on_stop(self):
        self.tab_manager.save_all_tabs()
        self._save_autosave()
        if self._has_unsaved_changes and self.code_input.text.strip():
            self._show_exit_confirmation()
            return False
        self._cleanup_resources()
        return True

    def _get_autosave_path(self):
        app_dir = os.getcwd()
        data_dir = os.path.join(app_dir, 'data')
        try:
            os.makedirs(data_dir, exist_ok=True)
        except:
            pass
        return os.path.join(data_dir, 'autosave.py')

    def _load_api_key_async(self):
        def load_key():
            try:
                self.saved_api_key = SettingsManager.get_api_key()
            except:
                self.saved_api_key = ''

        threading.Thread(target=load_key, daemon=True).start()

    def _load_fonts(self):
        """Регистрирует шрифты из папки fonts"""
        try:
            fonts_dir = os.path.join(os.path.dirname(__file__), 'fonts')

            # Базовый шрифт из папки проекта
            noto_path = os.path.join(fonts_dir, 'NotoSans-Regular.ttf')
            if os.path.exists(noto_path):
                LabelBase.register(name='Roboto', fn_regular=noto_path)

            # Регистрируем моноширинные шрифты для редактора
            font_files = {
                'JetBrainsMono': 'JetBrainsMono.ttf',
                'FiraCode': 'FiraCode-Regular.ttf',
                'CascadiaCode': 'CascadiaCode.ttf',
                'IBMPlexMono': 'IBMPlexMono-Regular.ttf',
                'NotoSansMono': 'NotoSansMono.ttf',
                'SourceCodePro': 'SourceCodePro-Regular.otf',
                'DroidMono': 'NotoSansMono.ttf',  # fallback
            }

            for font_name, font_file in font_files.items():
                font_path = os.path.join(fonts_dir, font_file)
                if os.path.exists(font_path):
                    LabelBase.register(name=font_name, fn_regular=font_path)

            # DejaVuSans для спецсимволов
            dejavu_path = os.path.join(fonts_dir, 'DejaVuSans.ttf')
            if os.path.exists(dejavu_path):
                LabelBase.register(name='DejaVuSans', fn_regular=dejavu_path)

            # Жирный шрифт для интерфейса
            bold_path = os.path.join(fonts_dir, 'SourceSansPro-Bold.ttf')
            if os.path.exists(bold_path):
                LabelBase.register(name='SourceBold', fn_regular=bold_path)

        except Exception as e:
            log_error(f"Font error: {e}")

    def _request_permissions(self):
        if ANV_AVAILABLE:
            try:
                request_permissions([Permission.WRITE_EXTERNAL_STORAGE, Permission.READ_EXTERNAL_STORAGE])
            except:
                pass

    def _request_storage_permission(self):
        try:
            from jnius import autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            activity = PythonActivity.mActivity
            permissions = ["android.permission.READ_EXTERNAL_STORAGE", "android.permission.WRITE_EXTERNAL_STORAGE"]
            VERSION = autoclass('android.os.Build$VERSION')
            if VERSION.SDK_INT >= 23:
                activity.requestPermissions(permissions, 1)
        except:
            pass

    def _set_initial_empty_lines(self):
        def set_lines(dt):
            try:
                self.code_input.text = ''
                if hasattr(self, 'editor') and self.editor:
                    self.editor.original_lines = ['']
                    self.editor._update_line_panel()
                self._has_unsaved_changes = False
                self._update_title_saved()
                self.code_input.cursor = (0, 0)
            except:
                pass

        Clock.schedule_once(set_lines, 0.3)

    def _process_pending_operations(self):
        if not self._ui_ready:
            return
        for op in self._pending_operations:
            try:
                op()
            except:
                pass
        self._pending_operations.clear()

    def apply_theme(self, theme):
        self.current_theme_name = theme['name']
        Window.clearcolor = theme['window_bg']
        if hasattr(self, 'bg_color'):
            self.bg_color.rgba = theme['app_bg']
        if hasattr(self, 'spinner'):
            self.spinner.background_color = theme['spinner_bg']
            self.spinner.background_normal = ''
            self.spinner.background_down = ''
            self.spinner.color = theme['spinner_text']
            if hasattr(self.spinner, 'canvas'):
                self.spinner.canvas.ask_update()
        if hasattr(self, 'menu_button'):
            self.menu_button.background_color = theme.get('menu_btn_bg', theme['widget_bg'])
            self.menu_button.background_normal = ''
            self.menu_button.background_down = ''
            self.menu_button.color = theme.get('menu_btn_text', theme['text_color'])
            if hasattr(self.menu_button, 'canvas'):
                self.menu_button.canvas.ask_update()
        if hasattr(self, 'run_btn'):
            bg_color = theme.get('run_btn_bg', (0.85, 0.88, 0.90, 1))
            icon_color = theme.get('run_btn_text', (0.18, 0.18, 0.19, 1))

            def update_bg(btn, *args):
                btn.canvas.before.clear()
                with btn.canvas.before:
                    Color(*bg_color)
                    Ellipse(pos=btn.pos, size=btn.size)

            update_bg(self.run_btn)
            for child in self.run_btn.children:
                if hasattr(child, 'text_color'):
                    child.text_color = icon_color
        if hasattr(self, 'current_input_widget') and self.current_input_widget:
            try:
                self.current_input_widget.background_color = theme['input_bg']
                self.current_input_widget.foreground_color = theme['input_text']
                self.current_input_widget.cursor_color = theme['input_cursor']
            except:
                pass
        if hasattr(self, 'tab_manager'):
            self.tab_manager.update_tab_bar_theme(theme)

        # Обновляем тему файлового менеджера, если он открыт
        if hasattr(self, 'file_manager') and self.file_manager:
            # Если есть открытый попап файлового менеджера, обновляем его
            if hasattr(self, '_current_file_popup') and self._current_file_popup:
                self._current_file_popup.update_theme()

    def _update_bg(self, instance, value):
        if hasattr(self, 'bg_rect'):
            self.bg_rect.size = instance.size
            self.bg_rect.pos = instance.pos

    def _update_top_bar_bg(self, instance, value):
        if hasattr(self, 'top_bar_bg_rect'):
            self.top_bar_bg_rect.pos = instance.pos
            self.top_bar_bg_rect.size = instance.size

    def _update_panel_bg(self, instance=None, value=None):
        """Обновляет фон панели"""
        if hasattr(self, 'panel_bg_rect'):
            if instance:
                self.panel_bg_rect.pos = instance.pos
                self.panel_bg_rect.size = instance.size
            else:
                self.panel_bg_rect.pos = self.line_panel.pos
                self.panel_bg_rect.size = self.line_panel.size

    def _on_main_touch_down(self, instance, touch):
        if hasattr(self, 'editor') and hasattr(self.editor, 'text_input'):
            editor = self.editor.text_input
            if not editor.collide_point(*touch.pos):
                editor.focus = False
                if hasattr(self.editor, '_keyboard_visible'):
                    self.editor._keyboard_visible = False
        return False

    def _apply_saved_syntax_style(self, dt):
        try:
            saved_style = SyntaxStyleManager.get_current_style()
            if hasattr(self, 'tab_manager'):
                SyntaxStyleManager.apply_style_to_all_tabs(self.tab_manager, saved_style)
        except:
            pass

    def _create_top_bar(self, theme):
        category = get_screen_category()

        if category == 'tablet':
            top_bar_height = 0.08
            spinner_font = adaptive_sp(18)
            menu_font = adaptive_sp(24)
        elif category == 'large_phone':
            top_bar_height = 0.09
            spinner_font = adaptive_sp(16)
            menu_font = adaptive_sp(22)
        else:
            top_bar_height = 0.10
            spinner_font = adaptive_sp(14)
            menu_font = adaptive_sp(20)

        top_bar = BoxLayout(orientation='horizontal', size_hint_y=top_bar_height, spacing=dp(10),
                            padding=[dp(5), dp(5), dp(5), dp(5)])

        with top_bar.canvas.before:
            Color(*theme.get('top_bar_bg', theme['widget_bg']))
            self.top_bar_bg_rect = Rectangle(pos=top_bar.pos, size=top_bar.size)
        top_bar.bind(pos=self._update_top_bar_bg, size=self._update_top_bar_bg)

        # Spinner "Примеры" - слева
        self.spinner = ThemedSpinner(
            text=self.tr.get('examples', 'Examples'),
            values=self._get_example_titles(),
            size_hint_x=0.7,
            background_color=theme['spinner_bg'],
            background_normal='',
            background_down='',
            color=theme['spinner_text'],
            font_size=spinner_font,
            font_name='SourceBold',
            dropdown_bg=theme['spinner_dropdown_bg'],
            dropdown_text_color=theme['spinner_dropdown_text'],
            dropdown_selected_bg=theme['spinner_dropdown_selected_bg']
        )
        self.spinner.bind(text=self.load_example)
        self.spinner.bind(on_press=self._update_spinner_dropdown_colors)
        top_bar.add_widget(self.spinner)

        # Кнопка меню - справа
        self.menu_button = Button(
            text='☰',
            font_name='DejaVuSans',
            size_hint_x=0.15,
            background_color=theme.get('menu_btn_bg', theme['widget_bg']),
            background_normal='',
            background_down='',
            color=theme.get('menu_btn_text', theme['text_color']),
            font_size=menu_font,
            bold=True
        )
        self.menu_button.bind(on_release=self.show_context_menu)
        top_bar.add_widget(self.menu_button)

        return top_bar

    def _restore_run_button(self):
        """Восстанавливает иконку на кнопке запуска"""
        print(f"[DEBUG] _restore_run_button called, run_btn={hasattr(self, 'run_btn')}")

        if not hasattr(self, 'run_btn') or self.run_btn is None:
            print("[DEBUG] run_btn не существует!")
            return

        print(f"[DEBUG] run_btn.children = {self.run_btn.children}")

        # Очищаем и пересоздаём иконку принудительно
        self.run_btn.clear_widgets()

        from kivymd.uix.label import MDIcon
        category = get_screen_category()
        if category == 'tablet':
            icon_size = dp(32)
        elif category == 'large_phone':
            icon_size = dp(28)
        else:
            icon_size = dp(23)

        theme = ThemeManager.get_theme()
        if theme.get('name') == 'dark':
            icon_color = theme.get('run_btn_text', (0.18, 0.18, 0.19, 1))
        else:
            icon_color = theme.get('run_btn_text', (0, 0, 0, 1))

        play_icon = MDIcon(
            icon='play',
            font_size=f"{icon_size}sp",
            theme_text_color="Custom",
            text_color=icon_color,
            pos_hint={"center_x": 0.5, "center_y": 0.5}
        )
        self.run_btn.add_widget(play_icon)
        self.run_btn.canvas.ask_update()
        print("[DEBUG] Иконка добавлена")

    def _update_top_panels(self):
        """Обновляет обе верхние панели (при смене темы, языка или повороте)"""
        if not hasattr(self, 'top_section') or self.top_section is None:
            return

        theme = ThemeManager.get_theme()

        # Просто обновляем существующие виджеты, без пересоздания (БЕЗОПАСНЫЙ ВАРИАНТ)
        if hasattr(self, 'spinner'):
            try:
                self.spinner.text = self.tr.get('examples', 'Примеры')
                self.spinner.values = self._get_example_titles()
                self.spinner.background_color = theme['spinner_bg']
                self.spinner.color = theme['spinner_text']
            except:
                pass

        if hasattr(self, 'menu_button'):
            try:
                self.menu_button.background_color = theme.get('menu_btn_bg', theme['widget_bg'])
                self.menu_button.color = theme.get('menu_btn_text', theme['text_color'])
            except:
                pass

    def _get_example_titles(self):
        return [self.tr[f'example_{i}'] for i in range(1, 19)]

    def _update_spinner_dropdown_colors(self, instance):
        theme = ThemeManager.get_theme()
        if hasattr(self, 'spinner'):
            self.spinner.dropdown_bg = theme['spinner_dropdown_bg']
            self.spinner.dropdown_text_color = theme['spinner_dropdown_text']
            self.spinner.dropdown_selected_bg = theme['spinner_dropdown_selected_bg']

    def show_context_menu(self, instance):
        # ВИБРАЦИЯ
        if hasattr(self, 'vibrate_short'):
            self.vibrate_short()

        theme = ThemeManager.get_theme()
        if not hasattr(self, '_menu_dropdown') or not self._menu_dropdown:
            self._menu_dropdown = DropDown()
            self._menu_dropdown.auto_width = False
            self._menu_dropdown.width = dp(167)
            self._create_menu_items(theme)

        def open_dropdown(*args):
            self._menu_dropdown.open(instance)
            win_width, win_height = Window.size
            if self._menu_dropdown.x + self._menu_dropdown.width > win_width:
                self._menu_dropdown.x = win_width - self._menu_dropdown.width - dp(3)
            elif self._menu_dropdown.x < 0:
                self._menu_dropdown.x = dp(3)
            if self._menu_dropdown.y < 0:
                self._menu_dropdown.y = instance.y + instance.height
            elif self._menu_dropdown.y + self._menu_dropdown.height > win_height:
                self._menu_dropdown.y = instance.y - self._menu_dropdown.height

        Clock.schedule_once(open_dropdown, 0.05)

    def menu_action(self, button, func):
        # ВИБРАЦИЯ
        self.vibrate_short()

        if hasattr(self, '_menu_dropdown'):
            self._menu_dropdown.dismiss()
        func(None)

    def _create_menu_items(self, theme):
        self._menu_dropdown.clear_widgets()
        tr = self.tr

        # Стилизация фона выпадающего меню
        if hasattr(self._menu_dropdown, 'container'):
            container = self._menu_dropdown.container
            container.canvas.before.clear()
            with container.canvas.before:
                Color(*theme.get('action_bar_bg', theme['widget_bg']))
                Rectangle(pos=container.pos, size=container.size)
            container.bind(pos=lambda inst, val: self._update_menu_container_bg(inst, theme),
                           size=lambda inst, val: self._update_menu_container_bg(inst, theme))

        # ========== СПИСОК ПУНКТОВ МЕНЮ ==========
        menu_items = [
            ('folder-open', tr['load'], self.show_load_dialog),
            ('content-save', tr['save'], self.show_save_dialog),
            ('magnify', tr['find'], self.show_search_only_dialog),
            ('find-replace', tr['find_replace'], self.show_search_replace_dialog),
            ('history', tr['history'], self.show_history),
            ('code-tags', tr['format'], self.format_code),
            # ('robot', tr['ai_assistant'], self.show_ai_assistant),
            ('cog', tr['settings'], self._open_settings_menu),
        ]

        from kivymd.uix.label import MDIcon
        from kivy.uix.behaviors import ButtonBehavior
        btn_bg = theme.get('action_bar_bg', theme['widget_bg'])

        for icon_name, text, func in menu_items:
            class MenuItem(ButtonBehavior, BoxLayout):
                pass

            box = MenuItem(orientation='horizontal', size_hint_y=None, height=dp(35),
                           padding=(dp(8), 0), spacing=dp(5))

            icon = MDIcon(icon=icon_name, font_size=f"{dp(10)}sp", theme_text_color="Custom",
                          text_color=theme['text_color'], size_hint_x=None, width=dp(17))

            lbl = Label(text=text, color=theme['text_color'], font_size=dp(15),
                        font_name='SourceBold', halign='left', valign='middle')

            box.add_widget(icon)
            box.add_widget(lbl)

            # Фон и обводка
            box.canvas.before.clear()
            with box.canvas.before:
                Color(*btn_bg)
                Rectangle(pos=box.pos, size=box.size)
                Color(btn_bg[0] + 0.08, btn_bg[1] + 0.08, btn_bg[2] + 0.08, 1)
                Line(rectangle=(box.pos[0], box.pos[1], box.size[0], box.size[1]), width=dp(0.5))

            box.bind(pos=lambda inst, val, bg=btn_bg: self._update_menu_btn_bg(inst, bg),
                     size=lambda inst, val, bg=btn_bg: self._update_menu_btn_bg(inst, bg))

            box.bind(on_release=lambda bt, f=func: self.menu_action(bt, f))
            self._menu_dropdown.add_widget(box)

        self._menu_dropdown.width = dp(167)

    def _update_menu_container_bg(self, instance, theme):
        if not hasattr(instance, 'canvas'):
            return
        instance.canvas.before.clear()
        with instance.canvas.before:
            Color(*theme.get('action_bar_bg', theme['widget_bg']))
            Rectangle(pos=instance.pos, size=instance.size)

    def _update_menu_btn_bg(self, instance, bg_color):
        if not hasattr(instance, 'canvas'):
            return
        instance.canvas.before.clear()
        with instance.canvas.before:
            Color(*bg_color)
            Rectangle(pos=instance.pos, size=instance.size)
            Color(bg_color[0] + 0.08, bg_color[1] + 0.08, bg_color[2] + 0.08, 1)
            Line(rectangle=(instance.pos[0], instance.pos[1], instance.size[0], instance.size[1]), width=dp(0.5))

    def _on_tab_changed(self, new_editor):
        """Переключение вкладки"""
        if not new_editor:
            return

        if not hasattr(self, 'editor_container') or not self.editor_container:
            return

        self.editor_container.clear_widgets()
        self.editor = new_editor

        if not hasattr(new_editor, 'text_input') or not new_editor.text_input:
            return

        self.code_input = new_editor.text_input
        self.editor_container.add_widget(new_editor)

        if hasattr(self, 'action_bar') and self.action_bar:
            self.action_bar.text_input = self.code_input
        if hasattr(self, 'symbol_bar') and self.symbol_bar:
            self.symbol_bar.text_input = self.code_input
        if hasattr(self, 'autocomplete') and self.autocomplete:
            self.autocomplete.code_input = self.code_input

        saved_font = SettingsManager.get_font()
        font_files = {
            'DroidMono': 'DroidMono',
            'JetBrainsMono': 'JetBrainsMono',
            'FiraCode': 'FiraCode',
            'CascadiaCode': 'CascadiaCode',
            'IBMPlexMono': 'IBMPlexMono',
            'NotoSansMono': 'NotoSansMono',
            'SourceCodePro': 'SourceCodePro',
        }
        if saved_font in font_files:
            self.code_input.font_name = font_files[saved_font]

        # Обновляем заголовок окна
        self._update_title_from_current_tab()

        Clock.schedule_once(self._autosave_tabs, 1)

        def set_cursor_to_first_line(dt):
            try:
                if hasattr(self, 'code_input') and self.code_input:
                    self.code_input.cursor = (0, 0)
                    self.code_input.focus = True
            except:
                pass

        Clock.schedule_once(set_cursor_to_first_line, 0.5)
        Clock.schedule_once(set_cursor_to_first_line, 0.7)

        self._restore_run_button()

    def _update_title_from_current_tab(self):
        """Обновляет заголовок окна на основе текущей активной вкладки"""
        if not hasattr(self, 'tab_manager') or not self.tab_manager:
            return

        # Получаем активную вкладку
        active_tab = None
        if 0 <= self.tab_manager.active_index < len(self.tab_manager.tabs):
            active_tab = self.tab_manager.tabs[self.tab_manager.active_index]

        if active_tab:
            is_saved = active_tab.get('saved', True)
            title = active_tab.get('title', 'Untitled')
            file_path = active_tab.get('file')

            # Для файлов используем имя файла
            if file_path and os.path.exists(file_path):
                correct_title = os.path.basename(file_path)
                if active_tab['title'] != correct_title:
                    active_tab['title'] = correct_title
                    self.tab_manager._update_tab_bar()
                title = correct_title

            # Обновляем заголовок окна
            if not is_saved:
                self.title = f"*{title} - {self._original_title}"
            else:
                self.title = f"{title} - {self._original_title}"

            # Обновляем _current_file
            self._current_file = file_path
        else:
            self.title = self._original_title
            self._current_file = None

    def _autosave_tabs(self, dt=None):
        try:
            self.tab_manager.save_all_tabs()
        except:
            pass

    def _setup_autosave(self):
        self._last_autosave_time = 0
        self.code_input.unbind(text=self._on_code_change_for_autosave)
        self.code_input.bind(text=self._on_code_change_for_autosave)

    def _on_code_change_for_autosave(self, instance, value):
        # Проверяем изменения в текущей вкладке
        if hasattr(self, 'tab_manager') and self.tab_manager:
            if 0 <= self.tab_manager.active_index < len(self.tab_manager.tabs):
                # Проверяем, изменилось ли содержимое
                current_tab = self.tab_manager.tabs[self.tab_manager.active_index]
                original = current_tab.get('original_content', "")
                has_changes = value != original

                if has_changes and current_tab.get('saved', True):
                    # Если были изменения, помечаем как несохранённую
                    self.tab_manager.mark_tab_unsaved(self.tab_manager.active_index)
                elif not has_changes and not current_tab.get('saved', True):
                    # Если изменения отменили, помечаем как сохранённую
                    self.tab_manager.mark_tab_saved(self.tab_manager.active_index)

        self._update_title_from_current_tab()

        current_time = time.time()
        if current_time - self._last_autosave_time > 2:
            self._last_autosave_time = current_time
            Clock.unschedule(self._do_autosave)
            Clock.unschedule(self._autosave_tabs)
            Clock.schedule_once(self._do_autosave, 3)
            Clock.schedule_once(self._autosave_tabs, 3)

    def _do_autosave(self, dt):
        """Сохраняет ТОЛЬКО кэш вкладок, НЕ перезаписывает исходные файлы"""
        self._last_autosave_time = time.time()
        self._save_autosave()  # Сохраняем только tabs.json

    def save_current_file(self):
        """Сохраняет текущий файл на диск (явное действие пользователя)"""
        if not self._current_file:
            self.show_save_dialog()
            return

        try:
            with open(self._current_file, 'w', encoding='utf-8') as f:
                f.write(self.code_input.text)

            # Обновляем статус вкладки
            if hasattr(self, 'tab_manager') and self.tab_manager:
                if 0 <= self.tab_manager.active_index < len(self.tab_manager.tabs):
                    self.tab_manager.mark_tab_saved(self.tab_manager.active_index)

            self._update_title_from_current_tab()
            self.show_result_popup(f"✓ Saved: {os.path.basename(self._current_file)}")
        except Exception as e:
            self.show_result_popup(f"X Error saving: {e}")

    def _save_autosave(self):
        try:
            tabs_data = {'active_index': self.tab_manager.active_index, 'tabs': []}
            for tab in self.tab_manager.tabs:
                tabs_data['tabs'].append({'title': tab['title'], 'file': tab['file'],
                                          'text': tab['editor'].get_text() if tab['editor'] else ''})
            dir_path = os.path.dirname(self._autosave_file)
            os.makedirs(dir_path, exist_ok=True)
            with open(self._autosave_file, 'w', encoding='utf-8') as f:
                json.dump(tabs_data, f, indent=2)
        except:
            pass

    def _save_tab_content(self, file_path, content, tab_index):
        """Сохраняет содержимое конкретной вкладки в файл (не переключая активную)"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            # Обновляем только указанную вкладку, если она ещё существует
            if hasattr(self, 'tab_manager') and self.tab_manager:
                if 0 <= tab_index < len(self.tab_manager.tabs):
                    tab = self.tab_manager.tabs[tab_index]
                    tab['original_content'] = content
                    tab['saved'] = True
                    tab['file'] = file_path
                    tab['title'] = os.path.basename(file_path)

                    # Обновляем отображение панели вкладок
                    self.tab_manager._update_tab_bar()

                    # Сохраняем состояние
                    self.tab_manager.save_all_tabs()

            self.show_result_popup(f"✓ Saved: {os.path.basename(file_path)}")
        except Exception as e:
            self.show_result_popup(f"X Error saving: {e}")

    def _save_tab_as(self, content, tab_index):
        """Показывает диалог сохранения для конкретной вкладки"""
        suggested_name = "script.py"

        def on_saved(file_path, _):
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                # Обновляем только указанную вкладку, если она ещё существует
                if hasattr(self, 'tab_manager') and self.tab_manager:
                    if 0 <= tab_index < len(self.tab_manager.tabs):
                        tab = self.tab_manager.tabs[tab_index]
                        tab['file'] = file_path
                        tab['original_content'] = content
                        tab['saved'] = True
                        tab['title'] = os.path.basename(file_path)

                        # Обновляем отображение
                        self.tab_manager._update_tab_bar()
                        self.tab_manager.save_all_tabs()

                        self.show_result_popup(f"✓ Saved: {os.path.basename(file_path)}")
                    else:
                        # Вкладка уже закрыта, просто сохраняем файл
                        self.show_result_popup(f"✓ Saved: {os.path.basename(file_path)}")
                else:
                    self.show_result_popup(f"✓ Saved: {os.path.basename(file_path)}")

            except Exception as e:
                self.show_result_popup(f"X Error saving: {e}")

        browser = FileBrowserPopup(
            self,
            self.file_manager,
            title=self.tr.get('save', 'Save file'),
            mode="save"
        )
        browser.show(on_saved, save_filename=suggested_name)

    def _save_tab_content_by_id(self, file_path, content, tab_id):
        """Сохраняет содержимое вкладки по ID"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            # Находим вкладку по ID и обновляем её
            if hasattr(self, 'tab_manager') and self.tab_manager:
                for i, tab in enumerate(self.tab_manager.tabs):
                    if tab.get('id') == tab_id:
                        tab['original_content'] = content
                        tab['saved'] = True
                        tab['file'] = file_path
                        tab['title'] = os.path.basename(file_path)
                        self.tab_manager._update_tab_bar()
                        self.tab_manager.save_all_tabs()
                        break

            self.show_result_popup(f"✓ Saved: {os.path.basename(file_path)}")
        except Exception as e:
            self.show_result_popup(f"X Error saving: {e}")

    def _save_tab_as_by_id(self, content, tab_id):
        """Сохраняет как вкладку по ID"""
        suggested_name = "script.py"

        def on_saved(file_path, _):
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                # Находим вкладку по ID и обновляем
                if hasattr(self, 'tab_manager') and self.tab_manager:
                    for i, tab in enumerate(self.tab_manager.tabs):
                        if tab.get('id') == tab_id:
                            tab['file'] = file_path
                            tab['original_content'] = content
                            tab['saved'] = True
                            tab['title'] = os.path.basename(file_path)
                            self.tab_manager._update_tab_bar()
                            self.tab_manager.save_all_tabs()
                            break

                self.show_result_popup(f"✓ Saved: {os.path.basename(file_path)}")
            except Exception as e:
                self.show_result_popup(f"X Error saving: {e}")

        browser = FileBrowserPopup(
            self,
            self.file_manager,
            title=self.tr.get('save', 'Save file'),
            mode="save"
        )
        browser.show(on_saved, save_filename=suggested_name)

    def _update_title_with_unsaved(self):
        if self._current_file:
            filename = os.path.basename(self._current_file)
            self.title = f"*{filename} - {self._original_title}"
        else:
            self.title = f"*Untitled - {self._original_title}"

    def _update_title_saved(self):
        self._has_unsaved_changes = False
        if self._current_file:
            filename = os.path.basename(self._current_file)
            self.title = f"{filename} - {self._original_title}"
        else:
            self.title = self._original_title

    def _do_save_file(self, full_path, filename):
        try:
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(self.code_input.text)
            self._current_file = full_path
            self._has_unsaved_changes = False
            self._update_title_saved()
            self.tab_manager.set_active_file(full_path)
            self.show_result_popup(f"✓ {self.tr.get('file_saved', 'Saved')}:\n{filename}")
        except Exception as e:
            self.show_result_popup(f"X {self.tr.get('error_save', 'Error')}:\n{e}")

    def show_load_dialog(self, instance=None):
        """Открывает диалог выбора файла через новый файловый менеджер"""
        browser = FileBrowserPopup(
            self,
            self.file_manager,
            title=self.tr.get('open', 'Open file'),
            mode="open"
        )
        browser.show(self._on_file_loaded)
        # Сохраняем ссылку для обновления темы
        self._current_file_popup = browser

    def _on_file_loaded(self, file_path, content):
        """Обработчик загруженного файла"""
        if not content:
            return

        filename = os.path.basename(file_path)

        # Создаём новую вкладку
        if hasattr(self, 'tab_manager') and self.tab_manager:
            # Добавляем вкладку с содержимым файла
            editor = self.tab_manager.add_tab(title=filename, text=content)
            # Обновляем файл и помечаем как сохранённую
            if 0 <= self.tab_manager.active_index < len(self.tab_manager.tabs):
                self.tab_manager.tabs[self.tab_manager.active_index]['file'] = file_path
                self.tab_manager.tabs[self.tab_manager.active_index]['original_content'] = content
                self.tab_manager.mark_tab_saved(self.tab_manager.active_index)
            self._on_tab_changed(editor)
        else:
            # Fallback
            self.code_input.text = content
            if hasattr(self, 'editor') and self.editor:
                self.editor.original_lines = content.split('\n')
                self.editor._update_line_panel()

        self._current_file = file_path
        self._update_title_from_current_tab()
        self.show_result_popup(f"Loaded: {filename}")

    def show_save_dialog(self, instance=None):
        """Открывает диалог сохранения файла"""
        suggested_name = "script.py"
        if self._current_file:
            suggested_name = os.path.basename(self._current_file)

        browser = FileBrowserPopup(
            self,
            self.file_manager,
            title=self.tr.get('save', 'Save file'),
            mode="save"
        )
        browser.show(self._on_file_saved, save_filename=suggested_name)
        # Сохраняем ссылку для обновления темы
        self._current_file_popup = browser

    def _on_file_saved(self, file_path, content):
        """Обработчик сохранённого файла"""
        filename = os.path.basename(file_path)

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(self.code_input.text)

            self._current_file = file_path

            # Обновляем статус вкладки
            if hasattr(self, 'tab_manager') and self.tab_manager:
                if 0 <= self.tab_manager.active_index < len(self.tab_manager.tabs):
                    # Обновляем исходное содержимое
                    self.tab_manager.tabs[self.tab_manager.active_index]['file'] = file_path
                    self.tab_manager.tabs[self.tab_manager.active_index]['original_content'] = self.code_input.text
                    self.tab_manager.mark_tab_saved(self.tab_manager.active_index)
                    self.tab_manager.set_active_title(filename)

            self._update_title_from_current_tab()
        except Exception as e:
            self.show_result_popup(f"X Error saving: {e}")

    def on_activity_result(self, request_code, result_code, intent):
        """Обработка результатов системных диалогов Android (SAF)"""
        if result_code != -1 or intent is None:
            return

        try:
            uri = intent.getData()
            if not uri:
                return

            # Выбор папки для рабочей директории (SAF)
            if request_code == 1004:
                if uri:
                    # Сохраняем URI рабочей папки
                    if hasattr(self, 'file_manager'):
                        self.file_manager.set_saf_root(str(uri))
                    self.show_result_popup("Папка выбрана! Теперь можно открывать файлы.")
                return

            # Открытие файла через SAF
            if request_code == 1001:
                self._read_file_from_uri(uri)
                return

            # Сохранение файла через SAF
            if request_code == 1002:
                self._save_file_to_uri(uri)
                return

            # Запрос разрешения MANAGE_EXTERNAL_STORAGE (Android 11+)
            if request_code == 1005:
                try:
                    from jnius import autoclass
                    Environment = autoclass('android.os.Environment')
                    if Environment.isExternalStorageManager():
                        self.show_result_popup("✓ Полный доступ к файлам получен!\nПерезапустите приложение.")
                    else:
                        self.show_result_popup(
                            "✗ Полный доступ к файлам не получен.\nНекоторые файлы могут быть не видны.")
                except:
                    pass
                return

        except Exception as e:
            log_error(f"on_activity_result error: {e}")

    def _show_loading_progress(self, message, file_size):
        """Показывает прогресс загрузки большого файла"""
        # ОБЯЗАТЕЛЬНО через Clock.schedule_once для UI в главном потоке
        Clock.schedule_once(lambda dt: self.show_result_popup(message), 0)

    def _read_file_content(self, file_path):
        """Читает содержимое файла с поддержкой отмены"""
        try:
            with open(file_path, 'rb') as f:
                # Определяем кодировку по BOM
                raw_start = f.read(4)
                f.seek(0)

                if raw_start.startswith(b'\xef\xbb\xbf'):
                    encoding = 'utf-8-sig'
                elif raw_start.startswith(b'\xff\xfe'):
                    encoding = 'utf-16-le'
                elif raw_start.startswith(b'\xfe\xff'):
                    encoding = 'utf-16-be'
                elif raw_start.startswith(b'\x00\x00\xfe\xff'):
                    encoding = 'utf-32-be'
                elif raw_start.startswith(b'\xff\xfe\x00\x00'):
                    encoding = 'utf-32-le'
                else:
                    encoding = 'utf-8'

                # Читаем с проверкой отмены
                try:
                    content = f.read().decode(encoding)
                    return content
                except UnicodeDecodeError:
                    pass

                # Пробуем другие кодировки
                for enc in ['cp1251', 'latin-1', 'windows-1251', 'koi8-r']:
                    if self._file_operation_cancel:
                        return None
                    f.seek(0)
                    try:
                        return f.read().decode(enc)
                    except UnicodeDecodeError:
                        continue

                # Fallback: заменяем ошибки
                f.seek(0)
                return f.read().decode('utf-8', errors='replace')

        except Exception as e:
            log_error(f"Read file error: {e}")
            return None

    def _load_large_file(self, file_path, file_size):
        tr = self.tr
        self.show_result_popup(tr.get('file_too_big', '! Большой файл') + f' ({file_size // 1024} KB)\nЗагрузка...')

        def load_in_background():
            try:
                content = self._read_file_content(file_path)
                if content is None:
                    Clock.schedule_once(
                        lambda dt: self.show_result_popup(tr.get('encoding_error', 'X Cannot determine encoding')))
                    return
                Clock.schedule_once(lambda dt: self._apply_loaded_content(content, file_path))
                filename = os.path.basename(file_path)
                Clock.schedule_once(
                    lambda dt: self.show_result_popup(tr.get('file_loaded', '✓ Loaded') + f':\n{filename}'))
            except Exception as e:
                Clock.schedule_once(lambda dt: self.show_result_popup(tr.get('error_load', 'X Error') + f':\n{e}'))

        threading.Thread(target=load_in_background, daemon=True).start()

    def _apply_loaded_content(self, content, file_path):
        self.code_input.text = content
        self._current_file = file_path
        if hasattr(self, 'editor') and self.editor:
            self.editor.original_lines = content.split('\n')
            if hasattr(self.editor, '_cached_max_line_length'):
                del self.editor._cached_max_line_length
            if hasattr(self.editor, '_cached_max_line_index'):
                del self.editor._cached_max_line_index
            self.editor._update_line_panel()
            Clock.schedule_once(self.editor._update_text_width, 0.1)
        self._has_unsaved_changes = False
        self._update_title_saved()
        self.tab_manager.set_active_file(file_path)

    def _show_exit_confirmation(self):
        tr = self.tr
        theme = ThemeManager.get_theme()
        content = BoxLayout(orientation='vertical', padding=dp(7), spacing=dp(5))
        message = tr.get('unsaved_changes', 'You have unsaved changes.')
        if self._current_file:
            message += f"\n{tr.get('save_before_exit', 'Save before exit?')} '{os.path.basename(self._current_file)}'?"
        else:
            message += "\n" + tr.get('save_before_exit', 'Save before exit?')
        content.add_widget(
            Label(text=message, color=theme['text_color'], font_size=dp(11), font_name='SourceBold', halign='center',
                  size_hint_y=None, height=dp(33)))
        btn_layout = BoxLayout(size_hint_y=None, height=dp(23), spacing=dp(4))
        category = get_screen_category()
        if category == 'tablet':
            size_hint = (0.70, 0.30)
        elif category == 'large_phone':
            size_hint = (0.78, 0.32)
        else:
            size_hint = (0.85, 0.35)

        popup = Popup(title=tr.get('exit_title', 'Exit'), title_color=theme['popup_title'], background='',
                      background_color=theme.get('popup_bg', (1.0, 1.0, 1.0, 1)), content=content,
                      size_hint=size_hint, auto_dismiss=False)
        btn_save = Button(text=tr.get('save_and_exit', 'Save & Exit'), font_name='SourceBold',
                          background_color=(0.2, 0.5, 0.2, 1), background_normal='', background_down='',
                          color=theme['text_color'], font_size=dp(10), on_release=lambda x: self._on_exit_save(popup))
        btn_exit = Button(text=tr.get('exit_without_save', 'Exit'), font_name='SourceBold',
                          background_color=(0.5, 0.2, 0.2, 1), background_normal='', background_down='',
                          color=theme['text_color'], font_size=dp(10), on_release=lambda x: self._on_exit_force(popup))
        btn_cancel = Button(text=tr.get('cancel', 'Cancel'), font_name='SourceBold',
                            background_color=theme['widget_bg'], background_normal='', background_down='',
                            color=theme['text_color'], font_size=dp(10), on_release=lambda x: popup.dismiss())
        btn_layout.add_widget(btn_save)
        btn_layout.add_widget(btn_exit)
        btn_layout.add_widget(btn_cancel)
        content.add_widget(btn_layout)
        popup.open()
        self._exit_popup = popup

    def _on_exit_save(self, popup):
        popup.dismiss()
        if self._current_file:
            self._do_save_file(self._current_file, os.path.basename(self._current_file))
        else:
            self._save_before_exit()
        Clock.schedule_once(lambda dt: self._force_exit(), 0.5)

    def _on_exit_force(self, popup):
        popup.dismiss()
        self._force_exit()

    def _confirm_overwrite(self, full_path):
        tr = self.tr
        theme = ThemeManager.get_theme()
        filename = os.path.basename(full_path)

        content = BoxLayout(orientation='vertical', padding=dp(7), spacing=dp(5))
        content.add_widget(Label(
            text=f"{tr.get('file_exists', 'File')} '{filename}' {tr.get('already_exists', 'exists')}.\n{tr.get('overwrite_prompt', 'Overwrite?')}",
            color=theme['text_color'], font_size=dp(11), font_name='SourceBold',
            halign='center', size_hint_y=None, height=dp(27)))

        btn_layout = BoxLayout(size_hint_y=None, height=dp(23), spacing=dp(4))

        popup = Popup(
            title=tr.get('overwrite_title', 'Confirm'),
            title_color=theme['popup_title'],
            background='',
            background_color=theme.get('popup_bg', (1.0, 1.0, 1.0, 1)),
            content=content,
            size_hint=(0.8, 0.35),
            auto_dismiss=False
        )

        btn_yes = Button(
            text=tr.get('overwrite_yes', 'Yes'),
            font_name='SourceBold',
            background_color=theme.get('btn_success_bg', (0.2, 0.5, 0.2, 1)),
            background_normal='', background_down='',
            color=theme['text_color'], font_size=dp(10),
            on_release=lambda x: self._on_overwrite_confirm(popup, full_path, filename))

        btn_no = Button(
            text=tr.get('overwrite_no', 'No'),
            font_name='SourceBold',
            background_color=theme['widget_bg'],
            background_normal='', background_down='',
            color=theme['text_color'], font_size=dp(10),
            on_release=lambda x: popup.dismiss())

        btn_layout.add_widget(btn_yes)
        btn_layout.add_widget(btn_no)
        content.add_widget(btn_layout)
        popup.open()

    def _on_overwrite_confirm(self, popup, full_path, filename):
        popup.dismiss()
        self._do_save_file(full_path, filename)

    def _save_before_exit(self):
        try:
            save_path = '/storage/emulated/0/Download'
            if ANV_AVAILABLE and androidstorage:
                try:
                    save_path = androidstorage.get_external_storage_path() + '/Download'
                except:
                    pass
            os.makedirs(save_path, exist_ok=True)
            filename = f"script_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
            full_path = os.path.join(save_path, filename)
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(self.code_input.text)
            self._current_file = full_path
        except:
            pass

    def _force_exit(self):
        self._cleanup_resources()
        App.get_running_app().stop()

    def _cleanup_resources(self):
        if self._cleanup_scheduled:
            return
        self._cleanup_scheduled = True
        self.history.clear()
        self.dismiss_popup()
        if self._exit_popup:
            try:
                self._exit_popup.dismiss()
            except:
                pass
        if hasattr(self, 'action_bar') and hasattr(self.action_bar, 'cleanup'):
            self.action_bar.cleanup()
        if hasattr(self, 'symbol_bar') and hasattr(self.symbol_bar, 'cleanup'):
            self.symbol_bar.cleanup()
        ThemeManager.unregister(self)

    def run_code(self, instance):
        # Защита от повторного запуска
        if hasattr(self, '_code_running') and self._code_running:
            self.show_result_popup("Код уже выполняется...")
            return

        self.vibrate_short()

        tr = self.tr

        # Проверка наличия редактора
        if not hasattr(self, 'code_input') or not self.code_input:
            self.show_result_popup("Ошибка: редактор не инициализирован")
            return

        code = self.code_input.text
        if not code.strip():
            self.show_result_popup(tr.get('enter_code', 'X Enter code'))
            return

        # Устанавливаем флаг, что код запущен
        self._code_running = True
        instance.disabled = True

        def input_handler(prompt=""):
            return self._handle_input(prompt)

        def result_callback(result):
            self._code_running = False  # Сбрасываем флаг
            instance.disabled = False
            self._show_result(result)

        if not self.code_executor.run(code, input_handler, result_callback):
            self._code_running = False  # Сбрасываем флаг при ошибке
            instance.disabled = False

    def _check_emergency_backup(self, dt):
        """Проверяет, есть ли emergency бэкап после аварийного закрытия"""
        emergency_path = os.path.join(os.getcwd(), 'data', 'emergency_backup.py')
        if os.path.exists(emergency_path):
            try:
                with open(emergency_path, 'r', encoding='utf-8') as f:
                    backup_content = f.read()

                if backup_content.strip() and backup_content != self.code_input.text:
                    self._show_emergency_restore_dialog(backup_content)
            except:
                pass

    def _show_emergency_restore_dialog(self, backup_content):
        """Показывает диалог восстановления после краша"""
        tr = self.tr
        theme = ThemeManager.get_theme()

        content = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        content.add_widget(Label(
            text=tr.get('recovery_message', 'Unsaved code found after crash.\nRestore?'),
            color=theme['text_color'],
            font_size=dp(12),
            halign='center',
            size_hint_y=None,
            height=dp(50)
        ))

        btn_layout = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(10))

        popup = Popup(
            title=tr.get('recovery_title', 'Data Recovery'),
            title_color=theme['popup_title'],
            background='',
            background_color=theme.get('popup_bg', (0.188, 0.204, 0.251, 1)),
            content=content,
            size_hint=(0.8, 0.3),
            auto_dismiss=False
        )

        def on_restore(btn):
            self.code_input.text = backup_content
            if hasattr(self, 'editor'):
                self.editor.original_lines = backup_content.split('\n')
                self.editor._update_line_panel()
            try:
                os.remove(os.path.join(os.getcwd(), 'data', 'emergency_backup.py'))
            except:
                pass
            popup.dismiss()
            self.show_result_popup(tr.get('code_restored', 'Code restored'))

        def on_ignore(btn):
            try:
                os.remove(os.path.join(os.getcwd(), 'data', 'emergency_backup.py'))
            except:
                pass
            popup.dismiss()

        btn_restore = Button(
            text=tr.get('recovery_restore', 'Restore'),
            background_color=(0.2, 0.5, 0.2, 1),
            background_normal='', background_down='',
            color=(1, 1, 1, 1),
            on_release=on_restore
        )
        btn_ignore = Button(
            text=tr.get('recovery_ignore', 'Ignore'),
            background_color=theme['widget_bg'],
            background_normal='', background_down='',
            color=theme['text_color'],
            on_release=on_ignore
        )

        btn_layout.add_widget(btn_restore)
        btn_layout.add_widget(btn_ignore)
        content.add_widget(btn_layout)
        popup.open()

    def _handle_input(self, prompt=""):
        tr = self.tr
        self.code_executor.clear_input()
        input_result = [None]
        input_event = threading.Event()

        def show_popup(dt):
            theme = ThemeManager.get_theme()
            content = BoxLayout(orientation='vertical', padding=dp(5), spacing=dp(4))
            content.add_widget(Label(text=prompt or tr.get('input_prompt', 'Enter value:'), color=theme['text_color'],
                                     font_size=dp(14), font_name='SourceBold', size_hint_y=None, height=dp(25)))
            text_input = TextInput(multiline=False, font_size=dp(14), font_name='SourceBold',
                                   background_color=theme['input_bg'], foreground_color=theme['input_text'],
                                   cursor_color=theme['input_cursor'], hint_text=tr.get('input_hint', 'Enter text...'),
                                   hint_text_color=theme['hint_text'], size_hint_y=None, height=dp(35),
                                   padding=(dp(5), dp(5)))
            self.current_input_widget = text_input
            content.add_widget(text_input)
            buttons = BoxLayout(size_hint_y=None, height=dp(30), spacing=dp(5))

            def on_ok(*args):
                value = text_input.text.strip()
                input_result[0] = value if value else ""
                self.code_executor.provide_input(value if value else "")
                self.current_input_widget = None
                popup.dismiss()
                input_event.set()

            def on_cancel(*args):
                input_result[0] = ""
                self.code_executor.provide_input("")
                self.current_input_widget = None
                popup.dismiss()
                input_event.set()

            btn_cancel = Button(text=tr.get('cancel', 'Cancel'), font_name='SourceBold',
                                background_color=theme['widget_bg'], background_normal='', background_down='',
                                color=theme['text_color'], font_size=dp(12), on_release=on_cancel)
            btn_ok = Button(text=tr.get('ok', 'OK'), font_name='SourceBold', background_color=theme['widget_bg'],
                            background_normal='', background_down='', color=theme['text_color'], font_size=dp(12),
                            on_release=on_ok)
            buttons.add_widget(btn_cancel)
            buttons.add_widget(btn_ok)
            content.add_widget(buttons)
            category = get_screen_category()
            if category == 'tablet':
                size_hint = (0.80, 0.40)
            elif category == 'large_phone':
                size_hint = (0.88, 0.42)
            else:
                size_hint = (0.93, 0.45)

            popup = Popup(title=tr.get('input_title', 'Input'), title_color=theme['popup_title'], background='',
                          background_color=theme.get('popup_bg', (1.0, 1.0, 1.0, 1)), content=content,
                          size_hint=size_hint, pos_hint={'top': 0.95}, auto_dismiss=False)
            popup.bind(on_dismiss=lambda *args: input_event.set())
            popup.open()

            def focus_input(dt):
                if text_input and text_input.parent:
                    text_input.focus = True

            Clock.schedule_once(focus_input, 0.3)

        Clock.schedule_once(show_popup, 0.1)
        input_event.wait(timeout=180)
        return input_result[0] if input_result[0] is not None else ""

    def _show_result(self, result):
        # Ограничиваем длину результата для производительности
        MAX_RESULT_LENGTH = 50000
        if len(result) > MAX_RESULT_LENGTH:
            result = result[:MAX_RESULT_LENGTH] + "\n\n... (вывод обрезан)"

        self.history.append({"time": datetime.now().strftime("%H:%M:%S"), "out": result})
        if len(self.history) > self._max_history:
            self.history = self.history[-self._max_history:]
        self.show_result_popup(result)

    def load_example(self, spinner, text):
        # ВИБРАЦИЯ
        self.vibrate_short()

        if not text or text == self.tr.get('examples', 'Examples'):
            return
        examples = self._examples_cache if self._examples_cache else self._build_examples()
        example_map = {'1. Hello World': '1. Hello World', '2. Variables': '2. Переменные',
                       '2. Переменные': '2. Переменные', '3. Input': '3. Ввод данных', '3. Ввод': '3. Ввод данных',
                       '4. Conditions': '4. Условия', '4. Условия': '4. Условия', '5. For Loop': '5. Цикл For',
                       '5. Цикл For': '5. Цикл For', '6. While Loop': '6. Цикл While', '6. Цикл While': '6. Цикл While',
                       '7. Lists': '7. Списки', '7. Списки': '7. Списки',
                       '8. List Comprehensions': '8. Генераторы списков',
                       '8. Генераторы списков': '8. Генераторы списков', '9. Dictionaries': '9. Словари',
                       '9. Словари': '9. Словари', '10. Functions': '10. Функции', '10. Функции': '10. Функции',
                       '11. Lambda': '11. Lambda', '12. Classes': '12. Классы', '12. Классы': '12. Классы',
                       '13. Inheritance': '13. Наследование', '13. Наследование': '13. Наследование',
                       '14. Errors': '14. Ошибки', '14. Ошибки': '14. Ошибки', '15. Files': '15. Файлы',
                       '15. Файлы': '15. Файлы', '16. Recursion': '16. Рекурсия', '16. Рекурсия': '16. Рекурсия',
                       '17. Generators': '17. Генераторы', '17. Генераторы': '17. Генераторы',
                       '18. Decorators': '18. Декораторы', '18. Декораторы': '18. Декораторы'}
        key = example_map.get(text, text)
        code = examples.get(key, '# Example not found')
        self.code_input.text = code
        if hasattr(self, 'editor') and self.editor:
            self.editor.original_lines = code.split('\n')
            self.editor._update_line_panel()
            Clock.schedule_once(self.editor._update_text_width, 0.1)
        self._current_file = None
        self._has_unsaved_changes = False
        self._update_title_saved()

    def _build_examples(self):
        lang = self.current_language
        if lang == 'en':
            return {
                '1. Hello World': '''# My first program
print("Hello, World!")
print("I am learning Python!")''',

                '2. Переменные': '''# Create variables
name = "Alice"
age = 25
height = 1.68

print("Name:", name)
print("Age:", age)
print("Height:", height)

# Change value
age = age + 1
print("Next year will be:", age)''',

                '3. Ввод данных': '''# Program asks your name
name = input("What is your name? ")
print("Hello,", name + "!")

# Ask age
age_str = input("How old are you? ")
if age_str.strip():
    age = int(age_str)
    print("Next year you will be", age + 1)
else:
    print("You didn't enter age")''',

                '4. Условия': '''# Check grade
grade = 85

if grade >= 90:
    print("Excellent! Grade A")
elif grade >= 80:
    print("Good! Grade B")
elif grade >= 70:
    print("Satisfactory! Grade C")
else:
    print("Need to study more")

# Age check
age = 18
if age >= 18:
    print("You can drive a car")
else:
    print("Too early to drive")''',

                '5. Цикл For': '''# Count from 1 to 5
print("Count from 1 to 5:")
for i in range(1, 6):
    print("Number:", i)

# Shopping list
items = ["bread", "milk", "eggs"]
print("\\nNeed to buy:")
for item in items:
    print("-", item)''',

                '6. Цикл While': '''# Count to 5
counter = 1
while counter <= 5:
    print("Counter:", counter)
    counter = counter + 1

# Sum of numbers
total = 0
num = 1
while num <= 10:
    total = total + num
    num = num + 1
print("Sum 1-10 =", total)''',

                '7. Списки': '''# Create list of numbers
numbers = [1, 2, 3, 4, 5]
print("List:", numbers)

# Add element
numbers.append(6)
print("Added 6:", numbers)

# Remove element
numbers.remove(3)
print("Removed 3:", numbers)

# List length
print("List length:", len(numbers))''',

                '8. Генераторы списков': '''# Squares of numbers
squares = [x**2 for x in range(1, 6)]
print("Squares 1-5:", squares)

# Only even numbers
evens = [x for x in range(1, 11) if x % 2 == 0]
print("Evens 1-10:", evens)''',

                '9. Словари': '''# Person info
person = {
    "name": "Alice",
    "age": 25,
    "city": "Moscow"
}

print("Name:", person["name"])
print("Age:", person["age"])

# Add new field
person["email"] = "alice@mail.ru"
print("Email added")''',

                '10. Функции': '''# Greeting function
def greet(name):
    return "Hello, " + name + "!"

# Call function
print(greet("Alice"))
print(greet("Bob"))

# Addition function
def add(a, b):
    return a + b

print("5 + 3 =", add(5, 3))''',

                '11. Lambda': '''# Short function
square = lambda x: x ** 2
print("5^2 =", square(5))

# Multiplication
multiply = lambda x, y: x * y
print("3 * 4 =", multiply(3, 4))''',

                '12. Классы': '''# Create Dog class
class Dog:
    def __init__(self, name):
        self.name = name

    def bark(self):
        return self.name + " says: Woof!"

# Create a dog
my_dog = Dog("Buddy")
print(my_dog.bark())''',

                '13. Наследование': '''# Base class
class Animal:
    def __init__(self, name):
        self.name = name

# Inherit from Animal
class Cat(Animal):
    def meow(self):
        return self.name + " says: Meow!"

cat = Cat("Murka")
print(cat.meow())''',

                '14. Ошибки': '''# Error handling
try:
    num = int(input("Enter a number: "))
    print("10 /", num, "=", 10 / num)
except ValueError:
    print("That's not a number!")
except ZeroDivisionError:
    print("Cannot divide by zero!")''',

                '15. Файлы': '''#
                Write to file
with open("test.txt", "w") as f:
    f.write("Hello, World!\\n")
    f.write("This is my file")
print("File created!")

# Read file
with open("test.txt", "r") as f:
    text = f.read()
print("Contents:")
print(text)''',

                '16. Рекурсия': '''# Factorial via recursion
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)

print("5! =", factorial(5))
print("7! =", factorial(7))''',

                '17. Генераторы': '''# Countdown generator
def countdown(n):
    while n > 0:
        yield n
        n -= 1

print("Countdown from 5:")
for num in countdown(5):
    print(num, end=" ")''',

                '18. Декораторы': '''# Timer decorator
import time

def measure_time(func):
    def wrapper():
        start = time.time()
        func()
        end = time.time()
        print(f"\\nTime: {end - start:.2f} sec")
    return wrapper

@measure_time
def pause():
    time.sleep(2)
    print("Done!")

pause()'''
            }
        else:
            return {
                '1. Hello World': '''# Моя первая программа
print("Привет, мир!")
print("Я учу Python!")''',

                '2. Переменные': '''# Создаем переменные
имя = "Алиса"
возраст = 25
рост = 1.68

print("Имя:", имя)
print("Возраст:", возраст)
print("Рост:", рост)

# Меняем значение
возраст = возраст + 1
print("В следующем году будет:", возраст)''',

                '3. Ввод данных': '''# Программа спрашивает ваше имя
имя = input("Как вас зовут? ")
print("Привет,", имя + "!")

# Спрашиваем возраст
возраст_стр = input("Сколько вам лет? ")
if возраст_стр.strip():
    возраст = int(возраст_стр)
    print("Через год вам будет", возраст + 1)
else:
    print("Вы не ввели возраст")''',

                '4. Условия': '''# Проверяем оценку
оценка = 85

if оценка >= 90:
    print("Отлично! Оценка A")
elif оценка >= 80:
    print("Хорошо! Оценка B")
elif оценка >= 70:
    print("Удовлетворительно! Оценка C")
else:
    print("Нужно подучить")

# Проверка возраста
возраст = 18
if возраст >= 18:
    print("Можно водить машину")
else:
    print("Ещё рано водить")''',

                '5. Цикл For': '''# Считаем от 1 до 5
print("Счет от 1 до 5:")
for i in range(1, 6):
    print("Число:", i)

# Список покупок
покупки = ["хлеб", "молоко", "яйца"]
print("\\nНужно купить:")
for товар in покупки:
    print("-", товар)''',

                '6. Цикл While': '''# Считаем до 5
счетчик = 1
while счетчик <= 5:
    print("Счетчик:", счетчик)
    счетчик = счетчик + 1

# Сумма чисел
сумма = 0
число = 1
while число <= 10:
    сумма = сумма + число
    число = число + 1
print("Сумма 1-10 =", сумма)''',

                '7. Списки': '''# Создаем список чисел
числа = [1, 2, 3, 4, 5]
print("Список:", числа)

# Добавляем элемент
числа.append(6)
print("Добавили 6:", числа)

# Удаляем элемент
числа.remove(3)
print("Удалили 3:", числа)

# Длина списка
print("Длина списка:", len(числа))''',

                '8. Генераторы списков': '''# Квадраты чисел
квадраты = [x**2 for x in range(1, 6)]
print("Квадраты 1-5:", квадраты)

# Только четные числа
четные = [x for x in range(1, 11) if x % 2 == 0]
print("Четные 1-10:", четные)''',

                '9. Словари': '''# Информация о человеке
человек = {
    "имя": "Алиса",
    "возраст": 25,
    "город": "Москва"
}

print("Имя:", человек["имя"])
print("Возраст:", человек["возраст"])

# Добавляем новое поле
человек["email"] = "alice@mail.ru"
print("Email добавлен")''',

                '10. Функции': '''# Функция приветствия
def приветствие(имя):
    return "Привет, " + имя + "!"

# Вызываем функцию
print(приветствие("Алиса"))
print(приветствие("Боб"))

# Функция сложения
def сложить(a, b):
    return a + b

print("5 + 3 =", сложить(5, 3))''',

                '11. Lambda': '''# Короткая функция
квадрат = lambda x: x ** 2
print("5^2 =", квадрат(5))

# Умножение
умножить = lambda x, y: x * y
print("3 * 4 =", умножить(3, 4))''',

                '12. Классы': '''# Создаем класс Собака
class Собака:
    def __init__(self, имя):
        self.имя = имя

    def гав(self):
        return self.имя + " говорит: Гав!"

# Создаем собаку
мой_пес = Собака("Бобик")
print(мой_пес.гав())''',

                '13. Наследование': '''# Базовый класс
class Животное:
    def __init__(self, имя):
        self.имя = имя

# Наследуем от Животного
class Кошка(Животное):
    def мяу(self):
        return self.имя + " говорит: Мяу!"

кошка = Кошка("Мурка")
print(кошка.мяу())''',

                '14. Ошибки': '''# Обработка ошибок
try:
    число = int(input("Введите число: "))
    print("10 /", число, "=", 10 / число)
except ValueError:
    print("Это не число!")
except ZeroDivisionError:
    print("На ноль делить нельзя!")''',

                '15. Файлы': '''#
                Записываем в файл
with open("тест.txt", "w") as ф:
    ф.write("Привет, мир!\\n")
    ф.write("Это мой файл")
print("Файл создан!")

# Читаем файл
with open("тест.txt", "r") as ф:
    текст = ф.read()
print("Содержимое:")
print(текст)''',

                '16. Рекурсия': '''# Факториал через рекурсию
def факториал(n):
    if n <= 1:
        return 1
    return n * факториал(n - 1)

print("5! =", факториал(5))
print("7! =", факториал(7))''',

                '17. Генераторы': '''# Генератор обратного отсчета
def отсчет(n):
    while n > 0:
        yield n
        n -= 1

print("Отсчет от 5:")
for число in отсчет(5):
    print(число, end=" ")''',

                '18. Декораторы': '''# Декоратор для замера времени
import time

def замерить_время(func):
    def обертка():
        начало = time.time()
        func()
        конец = time.time()
        print(f"\\nВремя: {конец - начало:.2f} сек")
    return обертка

@замерить_время
def пауза():
    time.sleep(2)
    print("Готово!")

пауза()'''
            }

    def show_search_only_dialog(self, instance=None):
        self.dismiss_search()

        content = SearchOnlyPopup(self.code_input)

        # Добавляем как виджет, а не popup
        content.size_hint_y = None
        content.height = dp(120)
        content.pos_hint = {'top': 1}

        self.search_widget = content

        # Добавляем в корневой виджет
        if hasattr(self, 'root_layout'):
            self.root_layout.add_widget(content)
        else:
            # Ищем корневой виджет
            for child in self.root.children:
                if hasattr(child, 'children'):
                    for sub in child.children:
                        if isinstance(sub, FloatLayout):
                            sub.add_widget(content)
                            break
                    break

        Clock.schedule_once(lambda dt: content._focus_search(), 0.3)

    def show_search_replace_dialog(self, instance=None):
        self.dismiss_search()

        content = SearchReplacePopup(self.code_input)

        # Добавляем как виджет, а не popup
        content.size_hint_y = None
        content.height = dp(155)
        content.pos_hint = {'top': 1}

        self.search_widget = content

        # Добавляем в корневой виджет
        if hasattr(self, 'root_layout'):
            self.root_layout.add_widget(content)
        else:
            # Ищем корневой виджет
            for child in self.root.children:
                if hasattr(child, 'children'):
                    for sub in child.children:
                        if isinstance(sub, FloatLayout):
                            sub.add_widget(content)
                            break
                    break

        Clock.schedule_once(lambda dt: content._focus_search(), 0.3)

    def show_goto_line_dialog(self, instance=None):
        """Показывает диалог перехода к строке"""
        self.dismiss_search()

        content = GotoLinePopup(self.code_input)
        content.size_hint_y = None
        content.height = dp(95)
        content.pos_hint = {'top': 1}

        self.search_widget = content

        if hasattr(self, 'root_layout'):
            self.root_layout.add_widget(content)
        else:
            for child in self.root.children:
                if hasattr(child, 'children'):
                    for sub in child.children:
                        if isinstance(sub, FloatLayout):
                            sub.add_widget(content)
                            break
                    break

        Clock.schedule_once(lambda dt: content._focus_input(), 0.3)

    def dismiss_search(self):
        """Закрывает окно поиска"""
        if hasattr(self, 'search_widget') and self.search_widget:
            try:
                self.search_widget.parent.remove_widget(self.search_widget)
            except:
                pass
            self.search_widget = None

        # Восстанавливаем фокус на редакторе
        if hasattr(self, 'code_input') and self.code_input:
            Clock.schedule_once(lambda dt: setattr(self.code_input, 'focus', True), 0.1)

    def show_search_dialog_from_button(self):
        self.show_search_only_dialog(None)

    def show_history(self, instance):
        if not self.history:
            self.show_result_popup(self.tr.get('history_empty', 'History is empty'))
            return
        lines = []
        for h in self.history[-10:]:
            out = h['out']
            if len(out) > 300:
                out = out[:300] + "..."
            lines.append(f"[{h['time']}] {out}\n{'-' * 40}")
        self.show_result_popup("\n".join(lines))

    def format_code(self, instance):
        """Форматирование кода через autopep8 с fallback"""
        code = self.code_input.text
        if not code.strip():
            self.show_result_popup(self.tr.get('no_code', 'No code to format'))
            return

        self.run_btn.text = "..."
        self.run_btn.disabled = True

        def do_format():
            try:
                if HAS_AUTOPEP8 and autopep8 is not None:
                    print("[INFO] Форматирование через autopep8")
                    formatted = autopep8.fix_code(
                        code,
                        options={
                            'aggressive': 1,
                            'indent_size': 4,
                            'max_line_length': 88,
                            'experimental': True
                        }
                    )
                else:
                    print("[INFO] autopep8 недоступен → используем базовое форматирование")
                    formatted = self._basic_format(code)

                Clock.schedule_once(lambda dt: self._apply_formatting(formatted))
            except Exception as e:
                error_msg = f"Ошибка форматирования: {str(e)}"
                Clock.schedule_once(lambda dt: self._formatting_error(error_msg))

        threading.Thread(target=do_format, daemon=True).start()

    def _basic_format(self, code: str) -> str:
        """Простое форматирование отступов (fallback)"""
        lines = code.split('\n')
        formatted = []
        indent_level = 0

        for raw_line in lines:
            stripped = raw_line.strip()
            original_end = raw_line[len(raw_line.rstrip()):]  # сохраняем пробелы в конце

            if not stripped:
                formatted.append(raw_line)
                continue

            # Уменьшаем отступ
            if stripped.startswith(('else:', 'elif ', 'except ', 'finally:', '}', '])', ')')):
                indent_level = max(0, indent_level - 1)

            indent = '    ' * indent_level
            formatted.append(indent + stripped + original_end)

            # Увеличиваем отступ
            if (stripped.endswith(':') and not stripped.startswith(
                    ('import', 'from', 'elif', 'else', 'except', 'finally'))) or \
                    stripped.startswith(('def ', 'class ', 'if ', 'for ', 'while ', 'with ', 'try:')):
                indent_level += 1

        return '\n'.join(formatted)

    def _apply_formatting(self, formatted):
        """Применение отформатированного кода"""
        self.run_btn.text = self.tr.get('run', '▶')
        self.run_btn.disabled = False

        if formatted.strip() == self.code_input.text.strip():
            self.show_result_popup(self.tr.get('formatted_fail', '! No changes needed'))
            return

        try:
            cursor_pos = self.code_input.cursor_index()
        except:
            cursor_pos = 0

        self.code_input.text = formatted

        if hasattr(self, 'editor') and self.editor:
            self.editor.original_lines = formatted.split('\n')
            self.editor._update_line_panel()
            Clock.schedule_once(self.editor._update_text_width, 0.1)

        try:
            if cursor_pos <= len(formatted):
                self.code_input.cursor = self.code_input.get_cursor_from_index(cursor_pos)
        except:
            pass

        self.show_result_popup(self.tr.get('formatted_ok', '✓ Code formatted'))

    def _formatting_error(self, error_msg):
        """Обработка ошибки форматирования"""
        self.run_btn.text = self.tr.get('run', '▶')
        self.run_btn.disabled = False
        self.show_result_popup(f"{self.tr.get('error', 'Error')}:\n{str(error_msg)[:250]}")

    def show_api_key_settings(self, instance=None):
        tr = self.tr
        current_key = self.saved_api_key or SettingsManager.get_api_key()
        theme = ThemeManager.get_theme()
        content = BoxLayout(orientation='vertical', padding=dp(5), spacing=dp(3))
        status_label = Label(
            text=tr.get('api_ok', '✓ Key set') if current_key else tr.get('api_not_set', '! Key not set'),
            font_name='SourceBold', color=theme['text_color'], font_size=dp(10), size_hint_y=None, height=dp(15))
        content.add_widget(status_label)
        key_input = TextInput(text=current_key, font_name='SourceBold',
                              hint_text=tr.get('api_key_hint', 'Paste API key'), multiline=False, font_size=dp(10),
                              background_color=theme['input_bg'], foreground_color=theme['input_text'],
                              hint_text_color=theme['hint_text'], size_hint_y=None, height=dp(27),
                              padding=(dp(5), dp(5)))
        content.add_widget(key_input)
        info_label = Label(text=tr.get('api_info', 'Get key: aistudio.google.com'), font_name='SourceBold',
                           color=theme['stats_text'], font_size=dp(8), size_hint_y=None, height=dp(13))
        content.add_widget(info_label)
        btn_layout = BoxLayout(size_hint_y=None, height=dp(22), spacing=dp(4))
        popup = Popup(title=tr.get('api_title', 'API Key'), title_color=theme['popup_title'], background='',
                      background_color=theme.get('popup_bg', (1.0, 1.0, 1.0, 1)), content=content, size_hint=(0.9, 0.5),
                      auto_dismiss=True)
        btn_clear = Button(text=tr.get('delete', 'Delete'), font_name='SourceBold', background_color=(0.3, 0.1, 0.1, 1),
                           background_normal='', background_down='', color=theme['text_color'], font_size=dp(9),
                           on_release=lambda x: self._clear_api_key(key_input, status_label))
        btn_save = Button(text=tr.get('save', 'Save'), font_name='SourceBold', background_color=theme['widget_bg'],
                          background_normal='', background_down='', color=theme['text_color'], font_size=dp(9),
                          on_release=lambda x: self._save_api_key(key_input, status_label, popup))
        btn_cancel = Button(text=tr.get('cancel', 'Cancel'), font_name='SourceBold',
                            background_color=theme['widget_bg'], background_normal='', background_down='',
                            color=theme['text_color'], font_size=dp(9), on_release=lambda x: popup.dismiss())
        btn_layout.add_widget(btn_clear)
        btn_layout.add_widget(btn_save)
        btn_layout.add_widget(btn_cancel)
        content.add_widget(btn_layout)
        popup.open()

    def _clear_api_key(self, key_input, status_label):
        key_input.text = ''
        SettingsManager.save_api_key('')
        self.saved_api_key = ''
        status_label.text = self.tr.get('api_not_set', '! Key not set')
        self.show_result_popup(self.tr.get('api_deleted', 'X Key deleted'))

    def _save_api_key(self, key_input, status_label, popup):
        api_key = key_input.text.strip()
        if api_key:
            SettingsManager.save_api_key(api_key)
            self.saved_api_key = api_key
            status_label.text = self.tr.get('api_ok', '✓ Key set')
            self.show_result_popup(self.tr.get('api_saved', '✓ Key saved!'))
        popup.dismiss()

    def show_ai_assistant(self, instance):
        api_key = self.saved_api_key or SettingsManager.get_api_key()
        if not api_key:
            self.show_result_popup(self.tr.get('no_api_key', '! API key not set'))
            return
        content = AIAssistantPopup(api_key=api_key)
        theme = ThemeManager.get_theme()
        popup = Popup(title=self.tr.get('ai_title', 'AI Assistant'), title_color=theme['popup_title'], background='',
                      background_color=theme.get('popup_bg', (1.0, 1.0, 1.0, 1)), content=content,
                      size_hint=(0.95, 0.9))
        popup.open()

    def switch_language(self, instance=None):
        self.current_language = 'en' if self.current_language == 'ru' else 'ru'
        self.tr = TRANSLATIONS[self.current_language]
        try:
            with open(os.path.join(os.getcwd(), 'language.txt'), 'w') as f:
                f.write(self.current_language)
        except:
            pass
        SettingsManager.save_language(self.current_language)
        self._update_ui_language()
        self.show_result_popup(self.tr.get('language', 'Language') + ': ' + self.current_language.upper())

    def _update_ui_language(self):
        tr = self.tr
        self._examples_cache = None

        if hasattr(self, 'tab_manager'):
            # Переименовываем вкладки при смене языка
            for tab in self.tab_manager.tabs:
                current_title = tab['title']
                # Убираем звёздочку, если есть (несохранённые изменения)
                has_asterisk = current_title.startswith('*')
                clean_title = current_title.lstrip('*')

                # Список названий для переименования на разных языках
                if clean_title in ['Untitled', 'New', 'Новый']:
                    new_title = tr.get('untitled_tab', 'New')
                    if has_asterisk:
                        new_title = '*' + new_title
                    tab['title'] = new_title
            self.tab_manager._update_tab_bar()

        # ========== ОБНОВЛЕНИЕ ВЕРХНИХ ПАНЕЛЕЙ ==========
        if hasattr(self, '_update_top_panels'):
            self._update_top_panels()  # ← ГЛАВНОЕ: обновляем обе панели

        # Для обратной совместимости (если старый код)
        if hasattr(self, 'spinner'):
            try:
                self.spinner.values = self._get_example_titles()
                self.spinner.text = tr.get('examples', 'Examples')
            except:
                pass

        if hasattr(self, 'action_bar'):
            try:
                self.action_bar.action_keys = ['undo', 'redo', 'copy', 'paste', 'cut', 'sel_all', 'auto', 'key',
                                               'clean', 'find', 'find_replace', 'goto']
                self.action_bar._create_buttons()
                self.action_bar.button_container.clear_widgets()
                for btn in self.action_bar.buttons:
                    self.action_bar.button_container.add_widget(btn)
            except:
                pass

        if hasattr(self, 'run_btn'):
            try:
                self.run_btn.text = tr.get('run', '▶')
            except:
                pass

        if hasattr(self, '_menu_dropdown'):
            try:
                self._create_menu_items(ThemeManager.get_theme())
            except:
                pass

        # Обновляем заголовок меню (Settings) при смене языка
        if hasattr(self, '_settings_menu') and self._settings_menu:
            try:
                # Пересоздаём меню настроек с новым языком
                self._settings_menu = SettingsMenu(self)
            except:
                pass

        try:
            if self._has_unsaved_changes:
                self._update_title_with_unsaved()
            else:
                self._update_title_saved()
        except:
            pass

    def _open_settings_menu(self, button):
        if self._settings_menu is None:
            self._settings_menu = SettingsMenu(self)
        self._settings_menu.show(self.menu_button)

    def show_result_popup(self, result):
        """Показывает результат в всплывающем окне."""
        # ВИБРАЦИЯ
        self.vibrate_short()

        tr = self.tr

        if len(result) > 50000:
            result = result[:50000] + "\n\n... " + \
                     tr.get('output_truncated', '(truncated)')

        theme = ThemeManager.get_theme()
        content = BoxLayout(orientation='vertical', padding=dp(5), spacing=dp(3))

        scroll = ScrollView(size_hint=(1, 0.85),
                            do_scroll_x=False, do_scroll_y=True)
        output_view = TextInput(
            text=str(result),
            readonly=True,
            font_size=dp(16),
            font_name='SourceBold',
            background_color=theme['result_bg'],
            foreground_color=theme['result_text'],
            do_wrap=True,
            multiline=True,
            size_hint_y=None,
            height=dp(33),
            padding=(dp(5), dp(5), dp(5), dp(5))
        )
        output_view.bind(minimum_height=output_view.setter('height'))
        scroll.add_widget(output_view)
        content.add_widget(scroll)

        btn_layout = BoxLayout(size_hint_y=None, height=dp(18), spacing=dp(3))

        btn_copy = Button(
            text=tr.get('copy_btn', 'Copy'),
            font_name='SourceBold',
            background_color=theme['widget_bg'],
            background_normal='',
            background_down='',
            color=theme['text_color'],
            font_size=dp(15),
            size_hint_y=None,
            height=dp(33),
            on_release=lambda x: self._copy_result(result)
        )

        # ВИБРАЦИЯ ДЛЯ КНОПКИ COPY
        btn_copy.bind(on_press=lambda x: self.vibrate_short())

        btn_close = Button(
            text=tr.get('close', 'Close'),
            font_name='SourceBold',
            background_color=theme['widget_bg'],
            background_normal='',
            background_down='',
            color=theme['text_color'],
            font_size=dp(15),
            size_hint_y=None,
            height=dp(33)
        )

        # ВИБРАЦИЯ ДЛЯ КНОПКИ CLOSE
        btn_close.bind(on_press=lambda x: self.vibrate_short())

        btn_layout.add_widget(btn_copy)
        btn_layout.add_widget(btn_close)
        content.add_widget(btn_layout)

        # Адаптивный размер Popup
        category = get_screen_category()
        if category == 'tablet':
            size_hint = (0.75, 0.70)
        elif category == 'large_phone':
            size_hint = (0.85, 0.76)
        else:
            size_hint = (0.90, 0.82)

        popup = ThemedPopup(
            title=tr.get('result_title', 'Result'),
            popup_bg=theme.get('popup_bg', (0.188, 0.204, 0.251, 1)),
            title_bg=theme.get('popup_title_bg', (0.188, 0.204, 0.251, 1)),
            title_color=theme['popup_title'],
            content=content,
            size_hint=size_hint,  # <--- ИСПОЛЬЗУЕМ ПЕРЕМЕННУЮ
            auto_dismiss=False,
            separator_color=theme.get('popup_separator', (0.25, 0.25, 0.25, 1))
        )
        btn_close.bind(on_release=popup.dismiss)
        popup.open()
        self._popup = popup
        self._current_popup_type = 'result'

    def _copy_result(self, text):
        Clipboard.copy(text)
        if platform == 'android':
            android_copy(text)
        self.show_result_popup(self.tr.get('result_copied', '✓ Copied'))

    def dismiss_popup(self, *args):
        # ВИБРАЦИЯ
        self.vibrate_short()

        if self._popup:
            try:
                if hasattr(self._popup, 'dismiss'):
                    self._popup.dismiss()
            except:
                pass
            finally:
                self._popup = None
                self._current_popup_type = None

    def _show_rename_tab_dialog(self, index):
        """Показывает диалог переименования вкладки."""
        tr = self.tr
        theme = ThemeManager.get_theme()

        if index < 0 or index >= len(self.tab_manager.tabs):
            return

        current_title = self.tab_manager.tabs[index]['title']

        content = BoxLayout(orientation='vertical', padding=[dp(7), dp(2), dp(7), dp(7)], spacing=dp(33))

        content.add_widget(Label(
            text=tr.get('rename_tab', 'Rename tab'),
            color=theme['text_color'], font_size=dp(15),
            font_name='SourceBold',
            size_hint_y=None, height=dp(15)
        ))

        name_input = TextInput(
            text=current_title, multiline=False, font_size=dp(15),
            font_name='SourceBold',
            background_color=theme['input_bg'],
            foreground_color=theme['input_text'],
            size_hint_y=None, height=dp(30),
            padding=(dp(5), dp(5))
        )
        content.add_widget(name_input)

        btn_layout = BoxLayout(size_hint_y=None, height=dp(18), spacing=dp(51))

        popup = Popup(
            title=tr.get('rename_tab', 'Rename'),
            title_color=theme['popup_title'],
            background='',
            background_color=theme.get('popup_bg', (1.0, 1.0, 1.0, 1)),
            content=content,
            size_hint=(0.85, 0.35),
            pos_hint={'top': 0.80},
            auto_dismiss=False
        )

        btn_ok = Button(
            text=tr.get('ok', 'OK'),
            font_name='SourceBold',
            background_color=theme['widget_bg'],
            background_normal='', background_down='',
            color=theme['text_color'], font_size=dp(15),
            size_hint_y=None, height=dp(30),
            on_release=lambda x: self._rename_tab_confirm(popup, index, name_input)
        )

        btn_cancel = Button(
            text=tr.get('cancel', 'Cancel'),
            font_name='SourceBold',
            background_color=theme['widget_bg'],
            background_normal='', background_down='',
            color=theme['text_color'], font_size=dp(15),
            size_hint_y=None, height=dp(30),
            on_release=lambda x: popup.dismiss()
        )

        btn_layout.add_widget(btn_cancel)
        btn_layout.add_widget(btn_ok)
        content.add_widget(btn_layout)
        popup.open()
        self._popup = popup

    def _rename_tab_confirm(self, popup, index, name_input):
        new_title = name_input.text.strip()
        if new_title:
            self.tab_manager.tabs[index]['title'] = new_title
            self.tab_manager._update_tab_bar()
            self.tab_manager.save_all_tabs()
        popup.dismiss()

    def _keyboard_handler(self, window, key, scancode=None, codepoint=None, modifier=None):
        if hasattr(self, 'current_input_widget') and self.current_input_widget:
            try:
                if self.current_input_widget.focus:
                    return False
            except:
                pass
        ctrl_pressed = modifier and 'ctrl' in modifier
        if ctrl_pressed:
            hotkeys = {115: self.show_save_dialog, 111: self.show_load_dialog, 102: self.show_search_only_dialog,
                       114: self.run_code, 104: self.show_history}
            if key in hotkeys:
                Clock.schedule_once(lambda dt, f=hotkeys[key]: f(None), 0)
                return True
        return False

    def vibrate_short(self):
        """Вызывает короткую вибрацию устройства, если это возможно."""
        try:
            # Время вибрации в секундах, 0.02 = 100 миллисекунд
            vibrator.vibrate(0.02)
        except NotImplementedError:
            # Тихая обработка ошибки, если функция не поддерживается (например, на ПК)
            pass


if __name__ == '__main__':
    try:
        PythonLearningApp().run()
    except Exception as e:
        error_msg = f"FATAL ERROR: {e}\n\nTraceback:\n{traceback.format_exc()}"
        try:
            with open('/storage/emulated/0/Download/app_error.log', 'w', encoding='utf-8') as f:
                f.write(error_msg)
        except:
            pass
        raise



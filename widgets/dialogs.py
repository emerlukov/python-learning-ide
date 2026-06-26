"""
Custom dialogs and popup widgets
"""
import ssl
import json
import threading
import urllib.request
import urllib.error

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.graphics import Color, Rectangle, Line
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.app import App
from kivy.core.window import Window
from kivy.properties import ColorProperty, ListProperty, StringProperty
from kivy.lang import Builder

from utils.debug_utils import log_error
from utils.screen_utils import get_screen_category, adaptive_dp, adaptive_sp
from ide_core.themes import ThemeManager
from ide_core.translations import TRANSLATIONS
from utils.vibration_manager import VibrationManager

Builder.load_string('''
<-MyActionBar>:
    canvas.before:
        Clear
    canvas.after:
        Clear
    background_color: [0, 0, 0, 0]
    border: [0, 0, 0, 0]
    background_image: ''

<-MySymbolScrollBar>:
    canvas.before:
        Clear
    canvas.after:
        Clear
    background_color: [0, 0, 0, 0]
    border: [0, 0, 0, 0]
    background_image: ''
''')

class ThemedPopup(Popup):
    """Кастомный Popup с поддержкой тем"""

    def __init__(self, **kwargs):
        self._title_bg = kwargs.pop('title_bg', (0.188, 0.204, 0.251, 1))
        self._title_color = kwargs.pop('title_color', (0.85, 0.88, 0.90, 1))
        self._separator_color = kwargs.pop('separator_color', (0.25, 0.25, 0.25, 1))
        self._popup_bg = kwargs.pop('popup_bg', (0.188, 0.204, 0.251, 1))
        kwargs['background'] = ''
        kwargs['background_color'] = self._popup_bg
        super().__init__(**kwargs)
        self.separator_color = self._separator_color
        self._title_box = None
        self._popup_bg_color = None
        self._popup_bg_rect = None
        Clock.schedule_once(self._apply_full_theme, 0.1)

    def _apply_full_theme(self, dt):
        try:
            self._apply_popup_background()
            self._apply_title_theme()
            Clock.schedule_once(self._force_title_color, 0.15)
        except Exception as e:
            log_error(f"ThemedPopup error: {e}")

    def _apply_popup_background(self):
        self.canvas.before.clear()
        with self.canvas.before:
            self._popup_bg_color = Color(*self._popup_bg)
            self._popup_bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_popup_bg, size=self._update_popup_bg)

    def _apply_title_theme(self):
        self._title_box = self._find_title_box(self)
        if not self._title_box:
            return
        self._title_box.background = ''
        self._title_box.background_normal = ''
        self._title_box.background_down = ''
        self._title_box.canvas.before.clear()
        with self._title_box.canvas.before:
            Color(*self._title_bg)
            Rectangle(pos=self._title_box.pos, size=self._title_box.size)
        self._title_box.bind(pos=self._update_title_bg, size=self._update_title_bg)
        for child in self._title_box.children:
            if isinstance(child, Label):
                child.color = self._title_color
                child.font_name = 'SourceBold'

    def _force_title_color(self, dt):
        try:
            self._color_all_labels(self, self._title_color)
        except Exception as e:
            log_error(f"_force_title_color error: {e}")

    def _color_all_labels(self, widget, color):
        if isinstance(widget, Label):
            widget.color = color
            widget.font_name = 'SourceBold'
        if hasattr(widget, 'children'):
            for child in widget.children:
                self._color_all_labels(child, color)

    def _find_title_box(self, widget):
        if isinstance(widget, BoxLayout):
            for child in widget.children:
                if isinstance(child, Label) and child.text == self.title:
                    return widget
        if hasattr(widget, 'children'):
            for child in widget.children:
                result = self._find_title_box(child)
                if result:
                    return result
        return None

    def _update_popup_bg(self, instance, value):
        if self._popup_bg_rect:
            self._popup_bg_rect.pos = instance.pos
            self._popup_bg_rect.size = instance.size

    def _update_title_bg(self, instance, value):
        if not hasattr(instance, 'canvas'):
            return
        instance.canvas.before.clear()
        with instance.canvas.before:
            Color(*self._title_bg)
            Rectangle(pos=instance.pos, size=instance.size)


class ThemedSpinner(Spinner):
    """Кастомный Spinner с поддержкой тем"""
    dropdown_bg = ColorProperty([0.188, 0.204, 0.251, 1])
    dropdown_text_color = ColorProperty([0.85, 0.88, 0.90, 1])
    dropdown_selected_bg = ColorProperty([0.141, 0.145, 0.149, 1])

    def __init__(self, **kwargs):
        self._dropdown_bg = kwargs.pop('dropdown_bg', self.dropdown_bg)
        self._dropdown_text_color = kwargs.pop('dropdown_text_color', self.dropdown_text_color)
        self._dropdown_selected_bg = kwargs.pop('dropdown_selected_bg', self.dropdown_selected_bg)
        # Если передан dropdown_width (число в dp или пикселях) — используем его.
        # Если None — поведение по умолчанию (ширина кнопки).
        self._custom_dropdown_width = kwargs.pop('dropdown_width', None)
        kwargs.setdefault('background_normal', '')
        kwargs.setdefault('background_down', '')
        super().__init__(**kwargs)
        self.dropdown_bg = self._dropdown_bg
        self.dropdown_text_color = self._dropdown_text_color
        self.dropdown_selected_bg = self._dropdown_selected_bg
        self.bind(on_press=self._on_spinner_press)

    def _on_spinner_press(self, instance):
        # ВИБРАЦИЯ
        #app = App.get_running_app()
        #if app and hasattr(app, 'vibrate_short'):
            #app.vibrate_short()

        Clock.schedule_once(lambda dt: self._apply_custom_width(), 0.0)
        Clock.schedule_once(lambda dt: self._apply_custom_width(), 0.05)
        Clock.schedule_once(lambda dt: self._apply_dropdown_theme(), 0.05)
        Clock.schedule_once(lambda dt: self._apply_dropdown_theme(), 0.1)

    def _apply_custom_width(self):
        if self._custom_dropdown_width is None:
            return
        if not hasattr(self, '_dropdown') or not self._dropdown:
            return
        # Если передан коэффициент (<=1) — вычисляем от текущей ширины окна
        if self._custom_dropdown_width <= 1.0:
            width = Window.width * self._custom_dropdown_width
        else:
            width = self._custom_dropdown_width
        self._dropdown.auto_width = False
        self._dropdown.width = width
        self._dropdown.x = (Window.width - width) / 2

    def _update_dropdown(self, *args):
        # Отключаем auto_width ДО вызова родителя, чтобы Kivy не перезаписал ширину
        if self._custom_dropdown_width is not None:
            if hasattr(self, '_dropdown') and self._dropdown:
                self._dropdown.auto_width = False
                self._dropdown.width = self._custom_dropdown_width
        super()._update_dropdown(*args)
        # Применяем снова после родителя на случай если он сбросил
        if self._custom_dropdown_width is not None:
            if hasattr(self, '_dropdown') and self._dropdown:
                if self._custom_dropdown_width <= 1.0:
                    width = Window.width * self._custom_dropdown_width
                else:
                    width = self._custom_dropdown_width
                self._dropdown.auto_width = False
                self._dropdown.width = width
                self._dropdown.x = (Window.width - width) / 2
        Clock.schedule_once(lambda dt: self._apply_dropdown_theme(), 0.05)

    def _apply_dropdown_theme(self):
        if not hasattr(self, '_dropdown') or not self._dropdown:
            return
        try:
            dropdown = self._dropdown
            if hasattr(dropdown, 'container'):
                container = dropdown.container
                container.canvas.before.clear()
                with container.canvas.before:
                    Color(*self.dropdown_bg)
                    Rectangle(pos=container.pos, size=container.size)
                container.bind(pos=self._update_container_bg, size=self._update_container_bg)
            self._style_all_buttons(dropdown)

            # ========== ДОБАВИТЬ ОБЁРТКУ КНОПОК В СПИННЕРЕ ==========
            app = App.get_running_app()
            if app and hasattr(app, 'wrap_widget_buttons'):
                if hasattr(dropdown, 'container'):
                    for child in dropdown.container.children:
                        app.wrap_widget_buttons(child)

        except Exception as e:
            log_error(f"Spinner theme error: {e}")

    def _update_container_bg(self, instance, value=None):
        if not hasattr(instance, 'canvas'):
            return
        instance.canvas.before.clear()
        with instance.canvas.before:
            Color(*self.dropdown_bg)
            Rectangle(pos=instance.pos, size=instance.size)

    def _style_all_buttons(self, widget):
        if isinstance(widget, Button):
            theme = ThemeManager.get_theme()
            btn_bg = theme.get('action_bar_bg', self.dropdown_bg)
            text_color = theme.get('spinner_dropdown_text', self.dropdown_text_color)
            widget.background_normal = ''
            widget.background_down = ''
            widget.background_color = (0, 0, 0, 0)
            widget.canvas.before.clear()
            with widget.canvas.before:
                Color(*btn_bg)
                Rectangle(pos=widget.pos, size=widget.size)
                Color(btn_bg[0] + 0.08, btn_bg[1] + 0.08, btn_bg[2] + 0.08, 1)
                Line(rectangle=(widget.pos[0], widget.pos[1], widget.size[0], widget.size[1]), width=dp(0.5))
            widget.bind(pos=self._update_btn_bg, size=self._update_btn_bg)
            widget.color = text_color
            widget.font_name = 'SourceBold'
            widget.size_hint_x = 0.94
            widget.pos_hint = {'center_x': 0.5}
        if hasattr(widget, 'children'):
            for child in widget.children:
                self._style_all_buttons(child)

    def _update_btn_bg(self, instance, value=None):
        if not hasattr(instance, 'canvas'):
            return
        theme = ThemeManager.get_theme()
        btn_bg = theme.get('spinner_dropdown_btn_bg', self.dropdown_bg)
        instance.canvas.before.clear()
        with instance.canvas.before:
            Color(*btn_bg)
            Rectangle(pos=instance.pos, size=instance.size)
            Color(btn_bg[0] + 0.08, btn_bg[1] + 0.08, btn_bg[2] + 0.08, 1)
            Line(rectangle=(instance.pos[0], instance.pos[1], instance.size[0], instance.size[1]), width=dp(0.5))


class SearchOnlyPopup(BoxLayout):
    """Диалог для поиска текста (вверху экрана, не блокирует редактор)"""

    def __init__(self, text_input, **kwargs):
        super().__init__(**kwargs)
        self.text_input = text_input
        self.orientation = 'vertical'
        self.padding = [dp(10), dp(8), dp(10), dp(8)]
        self.spacing = dp(8)
        self.last_search = ''
        self.search_results = []
        self.current_result_index = -1
        app = App.get_running_app()
        self.tr = app.tr if app else TRANSLATIONS['ru']
        theme = ThemeManager.get_theme()
        self._create_ui(theme)

        # Настройки для виджета
        self.size_hint_y = None
        self.height = dp(95)

        # Добавляем тень/рамку для видимости
        with self.canvas.before:
            # Основной фон
            Color(*theme.get('popup_bg', (0.188, 0.204, 0.251, 1)))
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

        # Добавляем тонкую рамку
        with self.canvas.after:
            Color(*theme.get('separator_color', (0.5, 0.5, 0.5, 0.5)))
            self.border_line = Line(rectangle=(self.x, self.y, self.width, self.height), width=dp(1))
        self.bind(pos=self._update_border, size=self._update_border)

    def _update_bg(self, instance, value):
        if hasattr(self, 'bg_rect'):
            self.bg_rect.pos = instance.pos
            self.bg_rect.size = instance.size

    def _update_border(self, instance, value):
        if hasattr(self, 'border_line'):
            self.border_line.rectangle = (instance.x, instance.y, instance.width, instance.height)

    def _create_ui(self, theme):
        tr = self.tr

        # Верхняя строка с заголовком и кнопкой закрытия
        header_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(28), spacing=dp(10))

        header_label = Label(
            text=tr.get('find', '🔍 Search'),
            color=theme.get('text_color', (0.85, 0.88, 0.90, 1)),
            font_size=dp(14),
            font_name='SourceBold',
            size_hint_x=0.7,
            halign='left',
            valign='middle'
        )
        header_label.bind(size=lambda s, sz: setattr(header_label, 'text_size', (sz[0], None)))
        header_box.add_widget(header_label)

        # Кнопка закрытия
        btn_close = Button(
            text='✕',
            font_name='DejaVuSans',
            size_hint=(None, 1),
            width=dp(36),
            background_color=theme.get('btn_danger_bg', (0.5, 0.2, 0.2, 1)),
            background_normal='', background_down='',
            color=(1, 1, 1, 1),
            font_size=dp(16),
            bold=True
        )
        btn_close.bind(on_release=lambda x: self.dismiss())
        header_box.add_widget(btn_close)
        self.add_widget(header_box)

        # Строка поиска
        search_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(36), spacing=dp(8))

        self.search_input = TextInput(
            hint_text=tr.get('find_text', 'Find...'),
            multiline=False,
            font_size=dp(14),
            font_name='SourceBold',
            background_color=theme['input_bg'],
            foreground_color=theme['input_text'],
            cursor_color=theme['input_cursor'],
            hint_text_color=theme['hint_text'],
            size_hint_x=0.7
        )
        self.search_input.bind(text=self._on_search_text_change)
        search_row.add_widget(self.search_input)

        # Кнопки навигации
        nav_layout = BoxLayout(orientation='horizontal', size_hint_x=0.3, spacing=dp(6))

        btn_prev = Button(
            text='◀',
            font_name='DejaVuSans',
            background_color=theme['widget_bg'],
            background_normal='', background_down='',
            color=theme['text_color'],
            font_size=dp(14),
            on_release=lambda x: self.find_previous()
        )
        btn_next = Button(
            text='▶',
            font_name='DejaVuSans',
            background_color=theme['widget_bg'],
            background_normal='', background_down='',
            color=theme['text_color'],
            font_size=dp(14),
            on_release=lambda x: self.find_next()
        )
        nav_layout.add_widget(btn_prev)
        nav_layout.add_widget(btn_next)
        search_row.add_widget(nav_layout)

        self.add_widget(search_row)

        # Статусная строка
        self.status_label = Label(
            text='',
            color=theme.get('stats_text', (0.6, 0.63, 0.65, 1)),
            font_size=dp(10),
            font_name='SourceBold',
            size_hint_y=None,
            height=dp(20),
            halign='left',
            valign='middle'
        )
        self.status_label.bind(size=lambda s, sz: setattr(self.status_label, 'text_size', (sz[0], None)))
        self.add_widget(self.status_label)

        # Обёртываем кнопки для вибрации
        app = App.get_running_app()
        if app and hasattr(app, 'wrap_widget_buttons'):
            app.wrap_widget_buttons(self)

    def _on_search_text_change(self, instance, value):
        if value != self.last_search:
            self._perform_search()

    def _perform_search(self):
        search_text = self.search_input.text
        if not search_text:
            self.search_results = []
            self.status_label.text = ''
            return

        self.last_search = search_text
        text = self.text_input.text
        if not text:
            self.search_results = []
            self.status_label.text = self.tr.get('not_found', 'Not found')
            return

        try:
            self.search_results = []
            search_lower = search_text.lower()
            text_lower = text.lower()
            start = 0
            while True:
                pos = text_lower.find(search_lower, start)
                if pos == -1:
                    break
                self.search_results.append((pos, pos + len(search_text)))
                start = pos + 1
        except:
            self.search_results = []

        self.current_result_index = -1
        if self.search_results:
            self.status_label.text = f"✓ {self.tr.get('found', 'Found')}: {len(self.search_results)}"
            self.find_next()
        else:
            self.status_label.text = f"✗ {self.tr.get('not_found', 'Not found')}"

    def find_next(self):
        if not self.search_results:
            return
        # ВИБРАЦИЯ
        #app = App.get_running_app()
        #if app and hasattr(app, 'vibrate_short'):
            #app.vibrate_short()
        self.current_result_index = (self.current_result_index + 1) % len(self.search_results)
        self._highlight_current()

    def find_previous(self):
        if not self.search_results:
            return
        # ВИБРАЦИЯ
        #app = App.get_running_app()
        #if app and hasattr(app, 'vibrate_short'):
            #app.vibrate_short()
        self.current_result_index = (self.current_result_index - 1) % len(self.search_results)
        self._highlight_current()

    def _highlight_current(self):
        if not self.search_results or self.current_result_index < 0:
            return
        start, end = self.search_results[self.current_result_index]
        self.text_input.select_text(start, end)
        self._scroll_to_position(start)

        # Обновляем статус
        self.status_label.text = f"→ {self.current_result_index + 1} / {len(self.search_results)}"

    def _scroll_to_position(self, position):
        try:
            text = self.text_input.text
            text_before = text[:position]
            line_number = text_before.count('\n')
            total_lines = max(1, text.count('\n') + 1)
            target_y = 1.0 - (line_number / total_lines)
            target_y = max(0.0, min(1.0, target_y))
            parent = self.text_input.parent
            while parent:
                if isinstance(parent, ScrollView):
                    parent.scroll_y = target_y
                    break
                parent = parent.parent
        except:
            pass

    def dismiss(self, *args):
        # ВИБРАЦИЯ
        #app = App.get_running_app()
        #if app and hasattr(app, 'vibrate_short'):
            #app.vibrate_short()
        app = App.get_running_app()
        if app:
            app.dismiss_search()

    def _focus_search(self):
        if self.search_input:
            self.search_input.focus = True


class SearchReplacePopup(BoxLayout):
    """Диалог для поиска и замены (вверху экрана, не блокирует редактор)"""

    def __init__(self, text_input, **kwargs):
        super().__init__(**kwargs)
        self.text_input = text_input
        self.orientation = 'vertical'
        self.padding = [dp(10), dp(8), dp(10), dp(8)]
        self.spacing = dp(8)
        self.last_search = ''
        self.search_results = []
        self.current_result_index = -1
        app = App.get_running_app()
        self.tr = app.tr if app else TRANSLATIONS['ru']
        theme = ThemeManager.get_theme()
        self._create_ui(theme)

        # Настройки для виджета
        self.size_hint_y = None
        self.height = dp(135)

        # Добавляем тень/рамку для видимости
        with self.canvas.before:
            Color(*theme.get('popup_bg', (0.188, 0.204, 0.251, 1)))
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

        with self.canvas.after:
            Color(*theme.get('separator_color', (0.5, 0.5, 0.5, 0.5)))
            self.border_line = Line(rectangle=(self.x, self.y, self.width, self.height), width=dp(1))
        self.bind(pos=self._update_border, size=self._update_border)

    def _update_bg(self, instance, value):
        if hasattr(self, 'bg_rect'):
            self.bg_rect.pos = instance.pos
            self.bg_rect.size = instance.size

    def _update_border(self, instance, value):
        if hasattr(self, 'border_line'):
            self.border_line.rectangle = (instance.x, instance.y, instance.width, instance.height)

    def _create_ui(self, theme):
        tr = self.tr

        # Верхняя строка с заголовком и кнопкой закрытия
        header_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(28), spacing=dp(10))

        header_label = Label(
            text=tr.get('find_replace', '🔄 Find & Replace'),
            color=theme.get('text_color', (0.85, 0.88, 0.90, 1)),
            font_size=dp(14),
            font_name='SourceBold',
            size_hint_x=0.7,
            halign='left',
            valign='middle'
        )
        header_label.bind(size=lambda s, sz: setattr(header_label, 'text_size', (sz[0], None)))
        header_box.add_widget(header_label)

        btn_close = Button(
            text='✕',
            font_name='DejaVuSans',
            size_hint=(None, 1),
            width=dp(36),
            background_color=theme.get('btn_danger_bg', (0.5, 0.2, 0.2, 1)),
            background_normal='', background_down='',
            color=(1, 1, 1, 1),
            font_size=dp(16),
            bold=True
        )
        btn_close.bind(on_release=lambda x: self.dismiss())
        header_box.add_widget(btn_close)
        self.add_widget(header_box)

        # Строка поиска
        search_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(34), spacing=dp(8))

        self.search_input = TextInput(
            hint_text=tr.get('find_text', 'Find...'),
            multiline=False,
            font_size=dp(13),
            font_name='SourceBold',
            background_color=theme['input_bg'],
            foreground_color=theme['input_text'],
            cursor_color=theme['input_cursor'],
            hint_text_color=theme['hint_text'],
            size_hint_x=0.6
        )
        self.search_input.bind(text=self._on_search_text_change)
        search_row.add_widget(self.search_input)

        # Кнопки навигации
        nav_layout = BoxLayout(orientation='horizontal', size_hint_x=0.4, spacing=dp(6))
        btn_prev = Button(
            text='◀',
            font_name='DejaVuSans',
            background_color=theme['widget_bg'],
            background_normal='', background_down='',
            color=theme['text_color'],
            font_size=dp(13),
            on_release=lambda x: self.find_previous()
        )
        btn_next = Button(
            text='▶',
            font_name='DejaVuSans',
            background_color=theme['widget_bg'],
            background_normal='', background_down='',
            color=theme['text_color'],
            font_size=dp(13),
            on_release=lambda x: self.find_next()
        )
        nav_layout.add_widget(btn_prev)
        nav_layout.add_widget(btn_next)
        search_row.add_widget(nav_layout)

        self.add_widget(search_row)

        # Строка замены
        replace_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(34), spacing=dp(8))

        self.replace_input = TextInput(
            hint_text=tr.get('replace_text', 'Replace with...'),
            multiline=False,
            font_size=dp(13),
            font_name='SourceBold',
            background_color=theme['input_bg'],
            foreground_color=theme['input_text'],
            cursor_color=theme['input_cursor'],
            hint_text_color=theme['hint_text'],
            size_hint_x=0.6
        )
        replace_row.add_widget(self.replace_input)

        # Кнопки действий
        action_layout = BoxLayout(orientation='horizontal', size_hint_x=0.4, spacing=dp(6))
        btn_replace = Button(
            text=tr.get('replace', 'Replace'),
            background_color=theme.get('btn_success_bg', (0.2, 0.5, 0.2, 1)),
            background_normal='', background_down='',
            color=(1, 1, 1, 1),
            font_size=dp(11),
            on_release=lambda x: self.replace_current()
        )
        btn_replace_all = Button(
            text=tr.get('replace_all', 'Replace All'),
            background_color=theme['widget_bg'],
            background_normal='', background_down='',
            color=theme['text_color'],
            font_size=dp(11),
            on_release=lambda x: self.replace_all()
        )
        action_layout.add_widget(btn_replace)
        action_layout.add_widget(btn_replace_all)
        replace_row.add_widget(action_layout)

        self.add_widget(replace_row)

        # Статусная строка
        self.status_label = Label(
            text='',
            color=theme.get('stats_text', (0.6, 0.63, 0.65, 1)),
            font_size=dp(10),
            font_name='SourceBold',
            size_hint_y=None,
            height=dp(20),
            halign='left',
            valign='middle'
        )
        self.status_label.bind(size=lambda s, sz: setattr(self.status_label, 'text_size', (sz[0], None)))
        self.add_widget(self.status_label)

        # Обёртываем кнопки для вибрации
        app = App.get_running_app()
        if app and hasattr(app, 'wrap_widget_buttons'):
            app.wrap_widget_buttons(self)

    def _on_search_text_change(self, instance, value):
        if value != self.last_search:
            self._perform_search()

    def _perform_search(self):
        search_text = self.search_input.text
        if not search_text:
            self.search_results = []
            self.status_label.text = ''
            return

        self.last_search = search_text
        text = self.text_input.text
        if not text:
            self.search_results = []
            self.status_label.text = self.tr.get('not_found', 'Not found')
            return

        try:
            self.search_results = []
            search_lower = search_text.lower()
            text_lower = text.lower()
            start = 0
            while True:
                pos = text_lower.find(search_lower, start)
                if pos == -1:
                    break
                self.search_results.append((pos, pos + len(search_text)))
                start = pos + 1
        except:
            self.search_results = []

        self.current_result_index = -1
        if self.search_results:
            self.status_label.text = f"✓ {self.tr.get('found', 'Found')}: {len(self.search_results)}"
            self.find_next()
        else:
            self.status_label.text = f"✗ {self.tr.get('not_found', 'Not found')}"

    def find_next(self):
        if not self.search_results:
            return
        # ВИБРАЦИЯ
        #app = App.get_running_app()
        #if app and hasattr(app, 'vibrate_short'):
            #app.vibrate_short()
        self.current_result_index = (self.current_result_index + 1) % len(self.search_results)
        self._highlight_current()

    def find_previous(self):
        if not self.search_results:
            return
        # ВИБРАЦИЯ
        #app = App.get_running_app()
        #if app and hasattr(app, 'vibrate_short'):
            #app.vibrate_short()
        self.current_result_index = (self.current_result_index - 1) % len(self.search_results)
        self._highlight_current()

    def _highlight_current(self):
        if not self.search_results or self.current_result_index < 0:
            return
        start, end = self.search_results[self.current_result_index]
        self.text_input.select_text(start, end)
        self._scroll_to_position(start)
        self.status_label.text = f"→ {self.current_result_index + 1} / {len(self.search_results)}"

    def _scroll_to_position(self, position):
        try:
            text = self.text_input.text
            text_before = text[:position]
            line_number = text_before.count('\n')
            total_lines = max(1, text.count('\n') + 1)
            target_y = 1.0 - (line_number / total_lines)
            target_y = max(0.0, min(1.0, target_y))
            parent = self.text_input.parent
            while parent:
                if isinstance(parent, ScrollView):
                    parent.scroll_y = target_y
                    break
                parent = parent.parent
        except:
            pass

    def replace_current(self):
        if not self.search_results or self.current_result_index < 0:
            return
        if self.current_result_index >= len(self.search_results):
            return

         # ВИБРАЦИЯ
        #app = App.get_running_app()
        #if app and hasattr(app, 'vibrate_short'):
            #app.vibrate_short()

        start, end = self.search_results[self.current_result_index]
        replace_text = self.replace_input.text

        old_text = self.text_input.text
        new_text = old_text[:start] + replace_text + old_text[end:]
        self.text_input.text = new_text

        # Корректируем позиции оставшихся результатов
        delta = len(replace_text) - (end - start)
        adjusted_results = []
        for i, (s, e) in enumerate(self.search_results):
            if i == self.current_result_index:
                adjusted_results.append((start, start + len(replace_text)))
            elif s > start:
                adjusted_results.append((s + delta, e + delta))
            else:
                adjusted_results.append((s, e))

        self.search_results = adjusted_results
        if self.current_result_index < len(self.search_results):
            self._highlight_current()
        else:
            self.current_result_index = -1

        self.status_label.text = f"✓ {self.tr.get('replaced', 'Replaced')} | {len(self.search_results)} matches"

    def replace_all(self):
        if not self.search_results:
            return

        # ВИБРАЦИЯ
        #app = App.get_running_app()
        #if app and hasattr(app, 'vibrate_short'):
            #app.vibrate_short()

        replace_text = self.replace_input.text
        text = self.text_input.text

        # Заменяем с конца, чтобы не сбивать позиции
        for start, end in reversed(self.search_results):
            text = text[:start] + replace_text + text[end:]

        self.text_input.text = text
        self.search_results = []
        self.current_result_index = -1
        self.status_label.text = f"✓ {self.tr.get('replaced', 'Replaced')} all"

    def dismiss(self, *args):
        # ВИБРАЦИЯ
        #app = App.get_running_app()
        #if app and hasattr(app, 'vibrate_short'):
            #app.vibrate_short()
        app = App.get_running_app()
        if app:
            app.dismiss_search()

    def _focus_search(self):
        if self.search_input:
            self.search_input.focus = True


class GotoLinePopup(BoxLayout):
    """Диалог для перехода к строке (вверху экрана, не блокирует редактор)"""

    def __init__(self, text_input, **kwargs):
        super().__init__(**kwargs)
        self.text_input = text_input
        self.orientation = 'vertical'
        self.padding = [dp(10), dp(8), dp(10), dp(8)]
        self.spacing = dp(8)
        app = App.get_running_app()
        self.tr = app.tr if app else TRANSLATIONS['ru']
        theme = ThemeManager.get_theme()
        self._create_ui(theme)

        self.size_hint_y = None
        self.height = dp(95)

        with self.canvas.before:
            Color(*theme.get('popup_bg', (0.188, 0.204, 0.251, 1)))
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

        with self.canvas.after:
            Color(*theme.get('separator_color', (0.5, 0.5, 0.5, 0.5)))
            self.border_line = Line(rectangle=(self.x, self.y, self.width, self.height), width=dp(1))
        self.bind(pos=self._update_border, size=self._update_border)

    def _update_bg(self, instance, value):
        if hasattr(self, 'bg_rect'):
            self.bg_rect.pos = instance.pos
            self.bg_rect.size = instance.size

    def _update_border(self, instance, value):
        if hasattr(self, 'border_line'):
            self.border_line.rectangle = (instance.x, instance.y, instance.width, instance.height)

    def _create_ui(self, theme):
        tr = self.tr

        header_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(28), spacing=dp(10))

        header_label = Label(
            text=tr.get('goto_line_title', 'Go to line'),
            color=theme.get('text_color', (0.85, 0.88, 0.90, 1)),
            font_size=dp(14),
            font_name='SourceBold',
            size_hint_x=0.7,
            halign='left',
            valign='middle'
        )
        header_label.bind(size=lambda s, sz: setattr(header_label, 'text_size', (sz[0], None)))
        header_box.add_widget(header_label)

        btn_close = Button(
            text='✕',
            font_name='DejaVuSans',
            size_hint=(None, 1),
            width=dp(36),
            background_color=theme.get('btn_danger_bg', (0.5, 0.2, 0.2, 1)),
            background_normal='', background_down='',
            color=(1, 1, 1, 1),
            font_size=dp(16),
            bold=True
        )
        btn_close.bind(on_release=lambda x: self.dismiss())
        header_box.add_widget(btn_close)
        self.add_widget(header_box)

        row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(36), spacing=dp(8))

        lines_count = len(self.text_input.text.split('\n')) if self.text_input.text else 1

        self.line_input = TextInput(
            hint_text=f"{tr.get('goto_line_hint', 'Line number')} (1-{lines_count})",
            multiline=False,
            font_size=dp(14),
            font_name='SourceBold',
            background_color=theme['input_bg'],
            foreground_color=theme['input_text'],
            cursor_color=theme['input_cursor'],
            hint_text_color=theme['hint_text'],
            size_hint_x=0.7,
            input_filter='int'
        )
        self.line_input.bind(on_text_validate=self._on_enter)
        row.add_widget(self.line_input)

        btn_goto = Button(
            text=tr.get('goto_line', 'Go'),
            font_name='SourceBold',
            size_hint_x=0.3,
            background_color=theme.get('btn_success_bg', (0.2, 0.5, 0.2, 1)),
            background_normal='', background_down='',
            color=(1, 1, 1, 1),
            font_size=dp(14),
            on_release=lambda x: self._goto_line()
        )
        row.add_widget(btn_goto)
        self.add_widget(row)

        # Обёртываем кнопки для вибрации
        app = App.get_running_app()
        if app and hasattr(app, 'wrap_widget_buttons'):
            app.wrap_widget_buttons(self)

    def _on_enter(self, instance):
        self._goto_line()

    def _goto_line(self):
        if not self.text_input or not self.text_input.text:
            self.dismiss()
            return

        try:
            line_num = int(self.line_input.text.strip())
            lines = self.text_input.text.split('\n')
            lines_count = len(lines)

            if 1 <= line_num <= lines_count:
                char_pos = 0
                for i in range(line_num - 1):
                    char_pos += len(lines[i]) + 1

                self.text_input.cursor = self.text_input.get_cursor_from_index(char_pos)
                self._scroll_to_line(line_num, lines_count)
                self.dismiss()
            else:
                self.line_input.text = ""
                self.line_input.hint_text = f"1-{lines_count}"
                self.line_input.hint_text_color = (0.8, 0.2, 0.2, 1)
                Clock.schedule_once(lambda dt: setattr(self.line_input, 'focus', True), 0.1)
        except ValueError:
            self.line_input.text = ""
            self.line_input.hint_text = "?"
            self.line_input.hint_text_color = (0.8, 0.2, 0.2, 1)
            Clock.schedule_once(lambda dt: setattr(self.line_input, 'focus', True), 0.1)

    def _scroll_to_line(self, line_num, total_lines):
        try:
            parent = self.text_input.parent
            while parent:
                if isinstance(parent, ScrollView):
                    target_y = 1.0 - (line_num / total_lines)
                    target_y = max(0.0, min(1.0, target_y))
                    parent.scroll_y = target_y
                    break
                parent = parent.parent
        except:
            pass

    def dismiss(self, *args):
        #app = App.get_running_app()
        #if app and hasattr(app, 'vibrate_short'):
            #app.vibrate_short()
        app = App.get_running_app()
        if app:
            app.dismiss_search()

    def _focus_input(self):
        if self.line_input:
            self.line_input.focus = True
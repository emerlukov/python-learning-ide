# ui/top_bar.py
"""
Top bar with example spinner, course button and menu button
"""
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.graphics import Color, Rectangle
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.core.window import Window

from utils.screen_utils import adaptive_sp, get_screen_category
from widgets.dialogs import ThemedSpinner
from ide_core.themes import ThemeManager


class TopBarBuilder:
    """Строитель верхней панели со спиннером примеров, кнопкой курса и кнопкой меню"""

    def __init__(self, app):
        self.app = app
        self.top_bar = None
        self.examples_spinner = None
        self.course_btn = None
        self.menu_button = None
        self.top_bar_bg_rect = None

    def create_top_bar(self, theme):
        """Создаёт верхнюю панель с двумя кнопками: Примеры и Курс"""
        category = get_screen_category()

        if category == 'tablet':
            top_bar_height = 0.08
            spinner_font = adaptive_sp(18)
            btn_font = adaptive_sp(30)
            menu_font = adaptive_sp(24)
        elif category == 'large_phone':
            top_bar_height = 0.09
            spinner_font = adaptive_sp(16)
            btn_font = adaptive_sp(28)
            menu_font = adaptive_sp(22)
        else:
            top_bar_height = 0.10
            spinner_font = adaptive_sp(14)
            btn_font = adaptive_sp(26)
            menu_font = adaptive_sp(20)

        self.top_bar = BoxLayout(
            orientation='horizontal', size_hint_y=top_bar_height,
            spacing=dp(8), padding=[dp(5), dp(5), dp(5), dp(5)]
        )

        with self.top_bar.canvas.before:
            Color(*theme.get('top_bar_bg', theme['widget_bg']))
            self.top_bar_bg_rect = Rectangle(pos=self.top_bar.pos, size=self.top_bar.size)

        self.top_bar.bind(pos=self._update_bg, size=self._update_bg)

        # ========== КНОПКА / СПИННЕР "ПРИМЕРЫ" ==========
        self.examples_spinner = ThemedSpinner(
            text=self.app.tr.get('examples', 'Examples'),
            values=self.app._get_example_titles(),
            size_hint_x=0.4,
            background_color=theme['spinner_bg'],
            background_normal='', background_down='',
            color=theme['spinner_text'],
            font_size=spinner_font, font_name='SourceBold',
            dropdown_bg=theme['spinner_dropdown_bg'],
            dropdown_text_color=theme['spinner_dropdown_text'],
            dropdown_selected_bg=theme['spinner_dropdown_selected_bg'],
            dropdown_width=0.95,
        )
        self.examples_spinner.bind(text=self.app.load_example)
        self.examples_spinner.bind(on_press=self._update_spinner_colors)

        # ========== НОВАЯ КНОПКА "КУРС" ==========
        self.course_btn = Button(
            text=self.app.tr.get('course', 'Py'),
            font_name='SourceBold',
            size_hint_x=0.10,
            background_color=theme.get('menu_btn_bg', theme['widget_bg']),
            background_normal='', background_down='',
            color=theme.get('menu_btn_text', theme['text_color']),
            font_size=btn_font,
            bold=True
        )
        # Временная заглушка — пока просто показываем сообщение
        self.course_btn.bind(on_release=self._on_course_click)

        # ========== КНОПКА МЕНЮ (☰) ==========
        self.menu_button = Button(
            text='☰', font_name='DejaVuSans', size_hint_x=0.10,
            background_color=theme.get('menu_btn_bg', theme['widget_bg']),
            background_normal='', background_down='',
            color=theme.get('menu_btn_text', theme['text_color']),
            font_size=menu_font, bold=True
        )
        self.menu_button.bind(on_release=self.app.show_context_menu)

        # Добавляем виджеты в панель
        self.top_bar.add_widget(self.examples_spinner)
        self.top_bar.add_widget(self.course_btn)
        self.top_bar.add_widget(self.menu_button)

        # Сохраняем ссылки в app
        self.app.spinner = self.examples_spinner
        self.app.course_btn = self.course_btn  # ← НОВАЯ ССЫЛКА
        self.app.menu_button = self.menu_button

        return self.top_bar

    def _on_course_click(self, instance):
        """Открывает меню курса"""
        from ui.course_menu import CourseMenu

        app = App.get_running_app()
        if app and hasattr(app, 'root_layout'):
            course_menu = CourseMenu(app)
            course_menu.size_hint = (0.92, 0.85)
            course_menu.pos_hint = {'center_x': 0.5, 'center_y': 0.5}
            app.root_layout.add_widget(course_menu)

    def update_theme(self, theme):
        """Обновляет тему панели"""
        if not self.top_bar:
            return

        # Обновляем фон
        self.top_bar.canvas.before.clear()
        with self.top_bar.canvas.before:
            Color(*theme.get('top_bar_bg', theme['widget_bg']))
            self.top_bar_bg_rect = Rectangle(pos=self.top_bar.pos, size=self.top_bar.size)

        # Обновляем спиннер примеров
        if self.examples_spinner:
            self.examples_spinner.background_color = theme['spinner_bg']
            self.examples_spinner.color = theme['spinner_text']
            self.examples_spinner.dropdown_bg = theme['spinner_dropdown_bg']
            self.examples_spinner.dropdown_text_color = theme['spinner_dropdown_text']

        # Обновляем кнопку курса
        if self.course_btn:
            self.course_btn.background_color = theme.get('menu_btn_bg', theme['widget_bg'])
            self.course_btn.color = theme.get('menu_btn_text', theme['text_color'])

        # Обновляем кнопку меню
        if self.menu_button:
            self.menu_button.background_color = theme.get('menu_btn_bg', theme['widget_bg'])
            self.menu_button.color = theme.get('menu_btn_text', theme['text_color'])

    def update_language(self):
        """Обновляет язык спиннера и кнопки курса"""
        if self.examples_spinner:
            self.examples_spinner.text = self.app.tr.get('examples', 'Examples')
            self.examples_spinner.values = self.app._get_example_titles()

        if self.course_btn:
            self.course_btn.text = self.app.tr.get('course', 'Course')

    def _update_spinner_colors(self, instance):
        """Обновляет цвета выпадающего списка спиннера"""
        theme = ThemeManager.get_theme()
        if self.examples_spinner:
            self.examples_spinner.dropdown_bg = theme['spinner_dropdown_bg']
            self.examples_spinner.dropdown_text_color = theme['spinner_dropdown_text']
            self.examples_spinner.dropdown_selected_bg = theme['spinner_dropdown_selected_bg']

    def _update_bg(self, instance, value):
        """Обновляет фон при изменении позиции/размера"""
        if self.top_bar_bg_rect:
            self.top_bar_bg_rect.pos = instance.pos
            self.top_bar_bg_rect.size = instance.size
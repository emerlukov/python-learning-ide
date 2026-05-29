"""
Animated splash screen - Custom colors
Keyboard COMPLETELY DISABLED
"""
import os
from kivy.uix.screenmanager import Screen, SlideTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.core.text import LabelBase
from kivy.config import Config
import threading
import time

# Полное отключение клавиатуры
# Config.set('kivy', 'keyboard_mode', 'systemandmulti')

# ========== ЦВЕТА ==========
BG_COLOR = (0.188, 0.204, 0.251, 1)  # Тёмно-синий фон
TEXT_COLOR = (0.596, 0.486, 1.0, 1)  # Фиолетовый текст
SUB_COLOR = (0.7, 0.65, 0.9, 0.9)  # Светло-фиолетовый
PROGRESS_BG = (0.25, 0.27, 0.32, 1)  # Тёмный фон прогресс-бара
PROGRESS_FILL = (0.596, 0.486, 1.0, 1)  # Фиолетовая заливка
STATUS_COLOR = (0.65, 0.6, 0.85, 0.8)  # Статус текст

# ========== FONT REGISTRATION ==========
current_dir = os.path.dirname(os.path.abspath(__file__))
fonts_dir = os.path.join(current_dir, 'fonts')

bold_font_path = os.path.join(fonts_dir, 'SourceSansPro-Bold.ttf')
regular_font_path = os.path.join(fonts_dir, 'NotoSans-Regular.ttf')


class CustomProgressBar(Widget):
    """Кастомный прогресс-бар"""

    def __init__(self, max_val=100, **kwargs):
        super().__init__(**kwargs)
        self.max_value = max_val
        self._value = 0
        self.size_hint = (0.6, None)
        self.height = dp(3)
        self.pos_hint = {'center_x': 0.5}

        with self.canvas:
            Color(*PROGRESS_BG)
            self.bg = Rectangle(pos=self.pos, size=self.size)
            Color(*PROGRESS_FILL)
            self.fill = Rectangle(pos=self.pos, size=(0, self.height))

        self.bind(pos=self._update_rects, size=self._update_rects)

    def _update_rects(self, instance, value):
        self.bg.pos = self.pos
        self.bg.size = self.size
        self.fill.pos = self.pos
        self.fill.size = ((self.width * self._value / self.max_value), self.height)

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = min(value, self.max_value)
        self.fill.size = ((self.width * self._value / self.max_value), self.height)


class AnimatedSplashScreen(Screen):
    """Анимированная заставка - исправлено дёрганье клавиатуры"""

    def __init__(self, main_app, **kwargs):
        super().__init__(**kwargs)
        self.main_app = main_app
        self.name = 'splash'
        self.loading_complete = False

        # Защита от дёрганья клавиатуры
        # Window.bind(on_resize=self._on_window_resize)

        # Фон
        with self.canvas.before:
            Color(*BG_COLOR)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)

        self.bind(pos=self._update_bg, size=self._update_bg)

        # Main layout
        layout = BoxLayout(
            orientation='vertical',
            padding=[dp(30), dp(60), dp(30), dp(60)],
            spacing=dp(25)
        )

        layout.add_widget(Widget(size_hint_y=0.2))

        # TITLE - используем стандартный шрифт
        self.title_label = Label(
            text='[b]Python[/b]\nLearning IDE',
            markup=True,
            font_name='Roboto',  # ← изменено
            font_size=sp(34),
            color=TEXT_COLOR,
            halign='center',
            valign='middle',
            size_hint=(1, 0.3)
        )
        self.title_label.bind(
            width=lambda inst, val: setattr(inst, 'text_size', (val, None))
        )
        layout.add_widget(self.title_label)

        # SUBTITLE
        self.subtitle_label = Label(
            text='Learn Python on Android',
            font_name='Roboto',  # ← изменено
            font_size=sp(14),
            color=SUB_COLOR,
            halign='center',
            valign='top',
            size_hint=(1, 0.1)
        )
        layout.add_widget(self.subtitle_label)

        # PROGRESS BAR
        self.progress_bar = CustomProgressBar(max_val=100)
        layout.add_widget(self.progress_bar)

        # STATUS TEXT
        self.status_label = Label(
            text='Loading...',
            font_name='Roboto',
            font_size=sp(11),
            color=STATUS_COLOR,
            halign='center',
            valign='middle',
            size_hint=(1, 0.08)
        )
        layout.add_widget(self.status_label)

        # DOTS
        self.dots_label = Label(
            text='',
            font_name='Roboto',
            font_size=sp(16),
            color=SUB_COLOR,
            halign='center',
            valign='middle',
            size_hint=(1, 0.08)
        )
        layout.add_widget(self.dots_label)

        layout.add_widget(Widget(size_hint_y=0.2))

        self.add_widget(layout)

        # Минимальное отключение клавиатуры
        self._disable_keyboard()

        # Запуск
        Clock.schedule_once(self._start, 0.1)

    def _disable_keyboard(self):
        """Только отключаем фокус — без агрессивного изменения softinput_mode"""
        try:
            if hasattr(self.main_app, 'code_input') and self.main_app.code_input:
                self.main_app.code_input.focus = False
                self.main_app.code_input.disabled = True
        except:
            pass

    def on_pre_enter(self):
        self._disable_keyboard()

    def on_touch_down(self, touch):
        """Игнорируем все касания на splash"""
        return True

    def _update_bg(self, instance, value):
        if hasattr(self, 'bg_rect'):
            self.bg_rect.pos = instance.pos
            self.bg_rect.size = instance.size

    def _start(self, dt):
        """Запуск анимаций и загрузки"""
        Clock.schedule_once(self._start_animations, 0.05)
        threading.Thread(target=self._load_resources, daemon=True).start()

    def _start_animations(self, dt=None):
        """Анимации заголовка и подзаголовка"""
        # Появление заголовка
        anim = Animation(opacity=1, duration=0.2)
        self.title_label.opacity = 0
        anim.start(self.title_label)

        # Пульсация подзаголовка
        pulse = Animation(opacity=0.5, duration=1) + Animation(opacity=0.9, duration=1)
        pulse.repeat = True
        pulse.start(self.subtitle_label)

        self._animate_dots()

    def _animate_dots(self, count=0):
        dots = ['.  ', '.. ', '...', '   ']
        self.dots_label.text = dots[count % len(dots)]
        Clock.schedule_once(lambda dt: self._animate_dots(count + 1), 0.5)

    def _load_resources(self):
        steps = [
            (10, "Loading fonts..."),
            (15, "Initializing..."),
            (20, "Setting up editor..."),
            (20, "Loading themes..."),
            (20, "Preparing examples..."),
            (15, "Starting!"),
        ]

        current = 0
        for step_val, step_text in steps:
            Clock.schedule_once(lambda dt, t=step_text: self._set_status(t), 0)
            for _ in range(step_val):
                current += 1
                if current <= 100:
                    Clock.schedule_once(lambda dt, v=current: self._set_progress(v), 0)
                    time.sleep(0.005)

        Clock.schedule_once(lambda dt: self._set_progress(100), 0)
        Clock.schedule_once(self._finish, 0.5)

    def _set_status(self, text):
        self.status_label.text = text

    def _set_progress(self, value):
        self.progress_bar.value = value

    def _finish(self, dt):
        if not self.loading_complete:
            self.loading_complete = True
            self.status_label.text = "Ready!"
            fade = Animation(opacity=0, duration=0.2)
            fade.start(self)
            Clock.schedule_once(self._go_to_main, 0.25)

    def _go_to_main(self, dt):
        """Безопасный переход на главный экран с корректной передачей фокуса."""
        # 1. Получаем редактор из главного приложения
        editor = None
        if hasattr(self.main_app, 'tab_manager') and self.main_app.tab_manager:
            editor = self.main_app.tab_manager.get_active_editor()

        if editor and hasattr(editor, 'text_input'):
            # 2. ВКЛЮЧАЕМ ввод, который был отключен
            editor.text_input.disabled = False
            # 3. Устанавливаем стабильный режим софт-клавиатуры
            Window.softinput_mode = 'below_target'
            # 4. Даем фокус редактору кода через небольшую задержку
            Clock.schedule_once(lambda dt: setattr(editor.text_input, 'focus', True), 0.1)

        # 5. Переключаем экран с более плавной анимацией
        self.manager.transition = SlideTransition(direction='left', duration=0.25)
        self.manager.current = 'main'

        # 6. Оповещаем приложение, что всё готово
        if hasattr(self.main_app, 'on_splash_finished'):
            self.main_app.on_splash_finished()

    def _final_restore(self):
        """Финальное восстановление после загрузки"""
        if hasattr(self.main_app, '_restore_run_button'):
            self.main_app._restore_run_button()
        if hasattr(self.main_app, '_refresh_ui_after_resize'):
            self.main_app._refresh_ui_after_resize()

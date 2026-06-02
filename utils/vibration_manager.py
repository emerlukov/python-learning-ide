# utils/vibration_manager.py - исправленная версия

"""
Centralized vibration management for all buttons
Унифицированная система управления вибрацией
"""
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.button import Button
from kivy.uix.behaviors import ButtonBehavior
from kivy.utils import platform
from functools import wraps

# Попытка импортировать plyer для вибрации
HAS_VIBRATOR = False
try:
    from plyer import vibrator

    # Проверяем, работает ли вибратор на этой платформе
    if platform == 'android' or platform == 'ios':
        HAS_VIBRATOR = True
    else:
        # На Windows вибрация не поддерживается
        HAS_VIBRATOR = False
except ImportError:
    HAS_VIBRATOR = False
except Exception:
    HAS_VIBRATOR = False

# Для Android используем прямой вызов если plyer не работает
ANDROID_AVAILABLE = False
if platform == 'android':
    try:
        from jnius import autoclass

        ANDROID_VIBRATOR = autoclass('android.os.Vibrator')
        Context = autoclass('android.content.Context')
        ANDROID_AVAILABLE = True
    except:
        ANDROID_AVAILABLE = False


class VibrationManager:
    """
    Централизованное управление вибрацией для всего приложения.
    Поддерживает: plyer (Android/iOS), Android Vibrator, автоматическую обёртку кнопок.
    На Windows/PCLinux вибрация просто не вызывается (без ошибок).
    """

    _instance = None
    _enabled = True
    _duration = 0.02  # 20 миллисекунд
    _wrapped_buttons = set()
    _vibrator_instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._init_vibrator()
        return cls._instance

    @classmethod
    def _init_vibrator(cls):
        """Инициализирует вибратор для текущей платформы"""
        if platform == 'android' and ANDROID_AVAILABLE:
            try:
                from jnius import autoclass
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                activity = PythonActivity.mActivity
                cls._vibrator_instance = activity.getSystemService(Context.VIBRATOR_SERVICE)
            except:
                cls._vibrator_instance = None

    @classmethod
    def vibrate(cls, duration=None):
        """
        Единый метод для вызова вибрации.

        Args:
            duration: Длительность вибрации в секундах (по умолчанию 0.02)
        """
        if not cls._enabled:
            return

        # На Windows/PCLinux просто выходим без ошибок
        if platform not in ('android', 'ios'):
            return

        if duration is None:
            duration = cls._duration

        try:
            # Способ 1: через plyer
            if HAS_VIBRATOR:
                vibrator.vibrate(duration)
                return

            # Способ 2: через Android напрямую
            if platform == 'android' and cls._vibrator_instance:
                milliseconds = int(duration * 1000)
                cls._vibrator_instance.vibrate(milliseconds)
                return
        except Exception as e:
            # Тихо игнорируем ошибки вибрации
            pass

    @classmethod
    def set_enabled(cls, enabled):
        """Включает/выключает вибрацию"""
        cls._enabled = enabled

    @classmethod
    def is_enabled(cls):
        """Возвращает текущее состояние вибрации"""
        return cls._enabled

    @classmethod
    def set_duration(cls, duration):
        """Устанавливает длительность вибрации"""
        cls._duration = duration

    @classmethod
    def wrap_button(cls, button, vibrate_on_press=False):
        """
        Обёртывает кнопку для автоматической вибрации.

        Args:
            button: Кнопка для обёртки
            vibrate_on_press: Если True, вибрация на on_press, иначе на on_release
        """
        if not button or button in cls._wrapped_buttons:
            return button

        # Сохраняем оригинальные обработчики
        original_on_release = getattr(button, 'on_release', None)
        original_on_press = getattr(button, 'on_press', None)

        def vibrate_and_call_release(*args, **kwargs):
            cls.vibrate()
            if callable(original_on_release):
                return original_on_release(*args, **kwargs)

        def vibrate_and_call_press(*args, **kwargs):
            cls.vibrate()
            if callable(original_on_press):
                return original_on_press(*args, **kwargs)

        if vibrate_on_press:
            button.on_press = vibrate_and_call_press
        else:
            button.on_release = vibrate_and_call_release

        cls._wrapped_buttons.add(button)
        return button

    @classmethod
    def unwrap_button(cls, button):
        """Возвращает кнопке оригинальные обработчики"""
        if button in cls._wrapped_buttons:
            button.on_release = None
            button.on_press = None
            cls._wrapped_buttons.discard(button)

    @classmethod
    def get_wrapped_count(cls):
        """Возвращает количество обёрнутых кнопок"""
        return len(cls._wrapped_buttons)


def vibrate(func):
    """
    Декоратор для добавления вибрации к любому методу.

    Использование:
        @vibrate
        def on_button_click(self, instance):
            pass
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        VibrationManager.vibrate()
        return func(*args, **kwargs)

    return wrapper


def vibrate_on_press(func):
    """
    Декоратор для вибрации при нажатии (вместо отпускания)
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        VibrationManager.vibrate()
        return func(*args, **kwargs)

    return wrapper

def wrap_all_buttons(widget, recursive=True):
    """
    Рекурсивно обёртывает все кнопки в виджете.
    Теперь поддерживает ВСЕ типы кнопок.
    """
    if widget is None:
        return

    try:
        from kivy.uix.button import Button
        from kivymd.uix.button import (MDRectangleFlatButton, MDIconButton,
                                       MDFlatButton, MDRoundFlatButton,
                                       MDFloatingActionButton, MDRaisedButton)
        from kivy.uix.behaviors import ButtonBehavior

        # Все возможные типы кнопок
        button_types = (
            Button,
            MDRectangleFlatButton,
            MDIconButton,
            MDFlatButton,
            MDRoundFlatButton,
            MDFloatingActionButton,
            MDRaisedButton,
        )

        # Также оборачиваем любой виджет с ButtonBehavior
        if isinstance(widget, ButtonBehavior):
            VibrationManager.wrap_button(widget)
        elif isinstance(widget, button_types):
            VibrationManager.wrap_button(widget)

        if recursive and hasattr(widget, 'children'):
            for child in widget.children:
                wrap_all_buttons(child, recursive)
    except Exception as e:
        pass  # Игнорируем ошибки при обёртке


def auto_wrap_on_build(app_instance):
    """
    Автоматически обёртывает все кнопки после построения интерфейса.
    Вызывать в методе build() приложения.

    Использование:
        class MyApp(App):
            def build(self):
                # ... создание UI ...
                auto_wrap_on_build(self)
                return root_widget
    """
    if app_instance and hasattr(app_instance, 'root'):
        Clock.schedule_once(lambda dt: wrap_all_buttons(app_instance.root), 0.5)
        Clock.schedule_once(lambda dt: wrap_all_buttons(app_instance.root), 1.0)


# Инициализация глобального экземпляра
vibration_manager = VibrationManager()
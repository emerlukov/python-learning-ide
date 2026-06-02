# utils/__init__.py - обновлённая версия

"""
Utility modules for the Python Learning IDE
"""
from .debug_utils import DEBUG, log_error
from .screen_utils import (
    get_screen_category,
    reset_screen_cache,
    adaptive_dp,
    adaptive_sp,
    get_tab_count
)
from .android_utils import patched_excepthook, android_copy
from .hotkeys import HotkeyManager

# Пытаемся импортировать vibration_manager
try:
    from .vibration_manager import (
        VibrationManager,
        vibrate,
        vibrate_on_press,
        wrap_all_buttons,
        auto_wrap_on_build
    )
except ImportError:
    # Заглушка, если файл ещё не создан
    class VibrationManager:
        @classmethod
        def vibrate(cls, duration=None): pass

        @classmethod
        def set_enabled(cls, enabled): pass

        @classmethod
        def is_enabled(cls): return True


    def vibrate(func):
        return func


    def vibrate_on_press(func):
        return func


    def wrap_all_buttons(widget, recursive=True):
        pass


    def auto_wrap_on_build(app_instance):
        pass

__all__ = [
    'DEBUG',
    'log_error',
    'get_screen_category',
    'reset_screen_cache',
    'adaptive_dp',
    'adaptive_sp',
    'get_tab_count',
    'patched_excepthook',
    'android_copy',
    'HotkeyManager',
    'VibrationManager',
    'vibrate',
    'vibrate_on_press',
    'wrap_all_buttons',
    'auto_wrap_on_build'
]
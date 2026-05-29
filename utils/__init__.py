# utils/__init__.py
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
    'HotkeyManager'
]
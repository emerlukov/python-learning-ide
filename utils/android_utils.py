"""
Android-specific utilities
"""
import sys
from kivy.utils import platform

# ====================== ИСПРАВЛЕНИЕ ОШИБКИ FOCUS ======================
def patched_excepthook(exctype, value, traceback_obj):
    """
    Игнорирует ошибку 'MainApp' object has no attribute 'focus',
    которая возникает при сворачивании/разворачивании приложения.
    """
    if exctype == AttributeError and "'MainApp' object has no attribute 'focus'" in str(value):
        return
    sys.__excepthook__(exctype, value, traceback_obj)

# ====================== ОТЛАДОЧНЫЕ ФУНКЦИИ ======================
def android_copy(text):
    """
    Копирует текст в буфер обмена через Android API.
    Работает надёжнее, чем стандартный Clipboard Kivy.
    """
    try:
        from jnius import autoclass
        Context = autoclass('android.content.Context')
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        activity = PythonActivity.mActivity
        clipboard = activity.getSystemService(Context.CLIPBOARD_SERVICE)
        ClipData = autoclass('android.content.ClipData')
        clip = ClipData.newPlainText("python_ide", text)
        clipboard.setPrimaryClip(clip)
        return True
    except:
        return False
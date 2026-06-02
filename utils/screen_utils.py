"""
Screen utilities for adaptive UI
"""
from kivy.utils import platform
from kivy.metrics import dp, sp
from kivy.core.window import Window

_SCREEN_CATEGORY = None


def get_screen_category():
    """Определяет тип экрана по реальной диагонали в дюймах"""
    global _SCREEN_CATEGORY
    if _SCREEN_CATEGORY:
        return _SCREEN_CATEGORY

    width, height = Window.size

    # Получаем реальные пиксели на Android
    if platform == 'android':
        try:
            from jnius import autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            metrics = PythonActivity.mActivity.getResources().getDisplayMetrics()
            width = metrics.widthPixels
            height = metrics.heightPixels
        except:
            pass

    diagonal_px = (width ** 2 + height ** 2) ** 0.5
    diagonal_inch = diagonal_px / dp(160)

    # КАТЕГОРИИ ЭКРАНОВ
    if diagonal_inch < 5.5:
        _SCREEN_CATEGORY = 'small_phone'
    elif diagonal_inch < 7.0:
        _SCREEN_CATEGORY = 'phone'
    elif diagonal_inch < 10.0:
        _SCREEN_CATEGORY = 'large_phone'
    else:
        _SCREEN_CATEGORY = 'tablet'

    print(f"[SCREEN] {diagonal_inch:.1f}\" -> {_SCREEN_CATEGORY} ({width}x{height})")
    return _SCREEN_CATEGORY


def reset_screen_cache():
    """Сбросить кэш (вызывать при повороте экрана)"""
    global _SCREEN_CATEGORY
    _SCREEN_CATEGORY = None


def adaptive_dp(value):
    """Адаптивный размер в dp"""
    category = get_screen_category()
    if category == 'tablet':
        return dp(value * 1.6)  # ← ГЛАВНОЕ: увеличен коэффициент для планшетов
    elif category == 'large_phone':
        return dp(value * 1.2)
    else:
        return dp(value)


def adaptive_sp(value):
    """Адаптивный размер шрифта в sp"""
    category = get_screen_category()
    if category == 'tablet':
        return sp(value * 1.6)  # ← ГЛАВНОЕ: увеличен коэффициент для планшетов
    elif category == 'large_phone':
        return sp(value * 1.2)
    else:
        return sp(value)


def get_tab_count():
    """Количество видимых вкладок"""
    if platform != 'android':
        return 7
    category = get_screen_category()
    if category == 'tablet':
        return 7
    elif category == 'large_phone':
        return 7
    else:
        return 3
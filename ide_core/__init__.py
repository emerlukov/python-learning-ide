"""
Core modules for the Python Learning IDE
"""
from .settings import SettingsManager
from .themes import ThemeManager, SyntaxStyleManager, DARK_THEME, LIGHT_THEME
from .translations import TRANSLATIONS
from .lessons import LessonManager

__all__ = [
    'SettingsManager',
    'ThemeManager',
    'SyntaxStyleManager',
    'DARK_THEME',
    'LIGHT_THEME',
    'TRANSLATIONS',
    'LessonManager'
]
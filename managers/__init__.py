"""
Manager modules for the Python Learning IDE
"""
from .autocomplete import AutoCompleteWidget
from .executor import CodeExecutor
from .tab_manager import TabManager

__all__ = [
    'AutoCompleteWidget',
    'CodeExecutor',
    'TabManager'
]
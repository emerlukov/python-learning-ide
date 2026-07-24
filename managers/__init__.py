# managers/__init__.py
"""
Manager modules for the Python Learning IDE
"""
from .autocomplete import AutoCompleteWidget
from .ime_support import KeyboardSupport, IMETextHandler
from .executor import CodeExecutor
from .tab_manager import TabManager
from .input_handler import InputHandler
from .emergency_recovery import EmergencyRecovery
from .file_handlers import FileOperationHandlers
from .examples_manager import examples_manager, ExamplesManager

__all__ = [
    'AutoCompleteWidget',
    'KeyboardSupport',
    'IMETextHandler',
    'CodeExecutor',
    'TabManager',
    'InputHandler',
    'EmergencyRecovery',
    'FileOperationHandlers',
    'examples_manager',
    'ExamplesManager'
]

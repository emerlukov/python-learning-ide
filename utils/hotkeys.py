# utils/hotkeys.py
"""
Hotkey manager for the application
"""
from kivy.clock import Clock


class HotkeyManager:
    """Управляет горячими клавишами"""

    def __init__(self, app):
        self.app = app

        # Маппинг клавиш (коды)
        self.hotkeys = {
            115: 'save',  # Ctrl+S
            111: 'open',  # Ctrl+O
            102: 'find',  # Ctrl+F
            114: 'run',  # Ctrl+R
            104: 'history',  # Ctrl+H
        }

    def handle_keyboard(self, window, key, scancode=None, codepoint=None, modifier=None):
        """Обрабатывает нажатия клавиш"""
        # Проверяем, не в фокусе ли поле ввода
        if hasattr(self.app, 'current_input_widget') and self.app.current_input_widget:
            try:
                if self.app.current_input_widget.focus:
                    return False
            except:
                pass

        # Проверяем Ctrl
        ctrl_pressed = modifier and 'ctrl' in modifier

        if ctrl_pressed and key in self.hotkeys:
            action = self.hotkeys[key]
            self._execute_action(action)
            return True

        return False

    def _execute_action(self, action):
        """Выполняет действие по горячей клавише"""
        actions = {
            'save': lambda: self.app.show_save_dialog(None),
            'open': lambda: self.app.show_load_dialog(None),
            'find': lambda: self.app.show_search_only_dialog(None),
            'run': lambda: self.app.run_code(None),
            'history': lambda: self.app.show_history(None),
        }

        if action in actions:
            Clock.schedule_once(lambda dt: actions[action](), 0)
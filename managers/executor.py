"""
Python code executor with input handling
"""
import sys
import io
import builtins
import threading
import traceback
from kivy.clock import Clock

class CodeExecutor:
    """Выполняет Python-код"""

    def __init__(self):
        self.is_running = False
        self._input_queue = []
        self._input_event = threading.Event()

    def run(self, code, input_handler, result_callback):
        if self.is_running:
            result_callback("! Код уже выполняется, подождите...")
            return False
        if not code.strip():
            result_callback("X Введите код перед запуском")
            return False

        self.is_running = True
        self._input_queue.clear()
        self._input_event.clear()

        def execute():
            old_stdout = sys.stdout
            redirected_output = io.StringIO()
            sys.stdout = redirected_output
            original_input = builtins.input
            builtins.input = input_handler

            try:
                exec(code, {})
                result = redirected_output.getvalue()
                if not result.strip():
                    result = "! Код выполнен успешно"
            except Exception:
                result = f"Ошибка:\n{traceback.format_exc()}"
            finally:
                sys.stdout = old_stdout
                builtins.input = original_input
                self.is_running = False

            Clock.schedule_once(lambda dt: result_callback(result))

        threading.Thread(target=execute, daemon=True).start()
        return True

    def provide_input(self, value):
        self._input_queue.append(value)
        self._input_event.set()

    def clear_input(self):
        self._input_queue.clear()
        self._input_event.clear()
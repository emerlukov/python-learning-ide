"""
Python code executor with input handling
"""
import sys
import io
import builtins
import threading
import traceback
from kivy.clock import Clock
from kivy.app import App
from utils.error_explainer import explain_error


class CodeExecutor:
    def __init__(self):
        self.is_running = False
        self._input_queue = []
        self._input_event = threading.Event()
        self._timeout_timer = None
        self.TIMEOUT_SECONDS = 30
        self._stop_requested = False

    def _trace_stop(self, frame, event, arg):
        """Трассировщик для остановки выполнения"""
        if self._stop_requested:
            raise SystemExit("Execution stopped by timeout")
        return self._trace_stop

    def run(self, code, input_handler, result_callback):
        app = App.get_running_app()
        tr = app.tr if app else {}

        if self.is_running:
            msg = tr.get('code_already_running', 'Code is already running, please wait...')
            result_callback(msg)
            return False
        if not code.strip():
            msg = tr.get('enter_code_first', 'Enter code before running')
            result_callback(msg)
            return False

        self.is_running = True
        self._stop_requested = False
        self._input_queue.clear()
        self._input_event.clear()

        def timeout_handler():
            if self.is_running:
                self._stop_requested = True
                self.is_running = False

        self._timeout_timer = threading.Timer(self.TIMEOUT_SECONDS, timeout_handler)
        self._timeout_timer.daemon = True

        def execute():
            old_stdout = sys.stdout
            redirected_output = io.StringIO()
            sys.stdout = redirected_output
            original_input = builtins.input
            builtins.input = input_handler

            # Устанавливаем трассировщик
            old_trace = sys.gettrace()
            sys.settrace(self._trace_stop)

            self._timeout_timer.start()

            result = ""
            try:
                exec(code, {})
                result = redirected_output.getvalue()
                if len(result) > 100000:
                    result = result[:100000] + "\n\n... (вывод обрезан)"
                if not result.strip():
                    if app and app.current_language == 'ru':
                        result = "Код выполнен успешно"
                    else:
                        result = "Code executed successfully"
            except SystemExit:
                timeout_msg = tr.get('timeout_exceeded', 'Execution timeout exceeded ({} sec)').format(
                    self.TIMEOUT_SECONDS)
                result = timeout_msg
            except RecursionError as e:
                error_msg = tr.get('recursion_error', 'Error: maximum recursion depth exceeded')
                result = f"{error_msg}\n{str(e)}"
            except Exception as e:
                error_text = traceback.format_exc()
                app = App.get_running_app()

                use_explainer = True
                if app and hasattr(app, 'error_explainer_enabled'):
                    use_explainer = app.error_explainer_enabled

                if use_explainer and app:
                    locale = app.current_language if app else 'ru'
                    # explain_error уже определяет тип ошибки внутри
                    friendly_error = explain_error(error_text, code, locale)
                    result = friendly_error
                else:
                    result = f"Error:\n{error_text}"
            finally:
                sys.stdout = old_stdout
                builtins.input = original_input
                sys.settrace(old_trace)
                self.is_running = False
                if self._timeout_timer:
                    self._timeout_timer.cancel()
                    self._timeout_timer = None

            Clock.schedule_once(lambda dt: result_callback(result))

        threading.Thread(target=execute, daemon=True).start()
        return True

    def provide_input(self, value):
        self._input_queue.append(value)
        self._input_event.set()

    def clear_input(self):
        self._input_queue.clear()
        self._input_event.clear()
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

_FOLD_MARKER = '\u25B6'  # ▶


class CodeExecutor:
    def __init__(self):
        self.is_running = False
        self._input_queue = []
        self._input_event = threading.Event()
        self._timeout_timer = None
        self.TIMEOUT_SECONDS = 30
        self._stop_requested = False
        self._trace_counter = 0
        self._lock = threading.Lock()  # Защита от race conditions

    def _clean_code(self, code):
        """Удаляет маркеры сворачивания из кода"""
        if not code:
            return code
        lines = code.split('\n')
        cleaned = []
        for line in lines:
            if _FOLD_MARKER in line or '▶' in line:
                # Оставляем только часть до маркера
                if '▶' in line:
                    clean_line = line.split('▶')[0].rstrip(' .')
                else:
                    clean_line = line.split(_FOLD_MARKER)[0].rstrip(' .')
                cleaned.append(clean_line)
            else:
                cleaned.append(line)
        return '\n'.join(cleaned)

    def _trace_stop(self, frame, event, arg):
        """Оптимизированный трассировщик — проверка каждые 100 вызовов"""
        # Счётчик вызовов
        self._trace_counter = getattr(self, '_trace_counter', 0) + 1

        # Проверяем только каждый 100-й вызов (вместо каждого)
        if self._trace_counter >= 100:
            self._trace_counter = 0
            if self._stop_requested:
                raise SystemExit("Execution stopped by timeout")
        return self._trace_stop

    def run(self, code, input_handler, result_callback):
        app = App.get_running_app()
        tr = app.tr if app else {}

        print("=== EXECUTOR DEBUG ===")
        print(f"Code length: {len(code)}")
        print("First 6 lines:")
        for i, line in enumerate(code.split('\n')[:6]):
            print(f"{i + 1:2d}: {repr(line)}")
        print("=====================")

        with self._lock:
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
            # Объявляем app в самом начале
            app = App.get_running_app()
            tr = app.tr if app else {}

            old_stdout = sys.stdout
            redirected_output = io.StringIO()
            sys.stdout = redirected_output
            original_input = builtins.input
            builtins.input = input_handler

            # Устанавливаем трассировщик
            old_trace = sys.gettrace()
            sys.settrace(self._trace_stop)
            # Сбрасываем счётчик при каждом запуске
            self._trace_counter = 0

            self._timeout_timer.start()

            result = ""
            try:
                exec(code, {})
                result = redirected_output.getvalue()
                print(f"=== EXECUTOR: raw output = '{result}'")
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

                use_explainer = True
                if app and hasattr(app, 'error_explainer_enabled'):
                    use_explainer = app.error_explainer_enabled

                if use_explainer and app:
                    locale = app.current_language if app else 'ru'
                    friendly_error = explain_error(error_text, code, locale)
                    result = friendly_error
                else:
                    result = f"Error:\n{error_text}"
            finally:
                sys.stdout = old_stdout
                builtins.input = original_input
                sys.settrace(old_trace)
                with self._lock:
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
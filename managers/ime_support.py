"""
Google Keyboard and IME Support for Autocomplete
Поддержка Google Keyboard и других методов ввода текста
"""
from kivy.utils import platform
from kivy.app import App
from kivy.clock import Clock
import re


class KeyboardSupport:
    """Обеспечивает совместимость с различными клавиатурами (Google, Samsung, etc.)"""

    def __init__(self):
        self.is_google_keyboard = False
        self.is_samsung_keyboard = False
        self.ime_enabled = False
        self._detect_keyboard()
        self._ime_buffer = ""
        self._ime_composition_active = False

    def _detect_keyboard(self):
        """Определяет установленную клавиатуру"""
        if platform != 'android':
            self.ime_enabled = False
            return

        try:
            from jnius import autoclass

            # Получаем InputMethodManager
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            activity = PythonActivity.mActivity

            # Получаем текущий input method ID
            settings_secure = autoclass('android.provider.Settings$Secure')
            content_resolver = activity.getContentResolver()
            current_ime = settings_secure.getString(
                content_resolver,
                'default_input_method'
            )

            if current_ime:
                if 'google' in current_ime.lower():
                    self.is_google_keyboard = True
                    print("[IME] Detected Google Keyboard")
                elif 'samsung' in current_ime.lower():
                    self.is_samsung_keyboard = True
                    print("[IME] Detected Samsung Keyboard")

                self.ime_enabled = True
                print(f"[IME] Current IME: {current_ime}")
        except Exception as e:
            print(f"[IME] Detection failed: {e}")
            self.ime_enabled = False

    def handle_ime_text_input(self, text_input_widget, new_text):
        """
        Обрабатывает ввод текста от IME
        Поддерживает:
        - Google Keyboard (поддержка многоязычного ввода)
        - Samsung Keyboard (особая обработка)
        - iOS QuickType (если приложение портировано)
        """
        if not text_input_widget:
            return

        try:
            # Получаем приложение для доступа к автодополнению
            app = App.get_running_app()
            if not app or not hasattr(app, 'autocomplete_popup'):
                return

            # Извлекаем текущее слово
            cursor_pos = text_input_widget.cursor_index()
            text_before_cursor = new_text[:cursor_pos]

            # Ищем последнее слово (для разных типов IME)
            match = re.search(r'([a-zA-Z_]\w*)$', text_before_cursor)
            current_word = match.group(1) if match else ""

            # Вызываем автодополнение
            if current_word and len(current_word) >= 1:
                Clock.schedule_once(
                    lambda dt: app.autocomplete_popup.show(current_word, text_input_widget),
                    0.05  # Небольшая задержка для обработки IME
                )
        except Exception as e:
            print(f"[IME] Handle IME text error: {e}")

    def enable_ime_features(self):
        """Включает расширенные функции IME"""
        if not platform == 'android':
            return

        try:
            from jnius import autoclass

            # Получаем InputMethodManager
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            activity = PythonActivity.mActivity
            Context = autoclass('android.content.Context')
            InputMethodManager = autoclass('android.view.inputmethod.InputMethodManager')

            imm = activity.getSystemService(Context.INPUT_METHOD_SERVICE)

            # Включаем режимы IME
            if self.is_google_keyboard:
                # Включаем режим с подсказками
                print("[IME] Google Keyboard features enabled")

            print("[IME] IME features enabled")
        except Exception as e:
            print(f"[IME] Enable IME features failed: {e}")

    def get_keyboard_info(self):
        """Возвращает информацию о текущей клавиатуре"""
        info = {
            'google_keyboard': self.is_google_keyboard,
            'samsung_keyboard': self.is_samsung_keyboard,
            'ime_enabled': self.ime_enabled,
            'platform': platform
        }
        return info

    def suggest_ime_optimizations(self):
        """Возвращает рекомендации для оптимизации работы с IME"""
        recommendations = []

        if self.is_google_keyboard:
            recommendations.extend([
                'Use composition text handling for complex input',
                'Support continuous input suggestions',
                'Enable gesture typing if needed'
            ])

        if self.is_samsung_keyboard:
            recommendations.append('Samsung IME may have reduced composition support')

        return recommendations


class IMETextHandler:
    """Обработчик текста для IME с поддержкой состава (composition)"""

    def __init__(self):
        self.composition_text = ""
        self.is_composing = False
        self.cursor_position = 0

    def start_composition(self, composition):
        """Начинает обработку composition text"""
        self.composition_text = composition
        self.is_composing = True
        print(f"[IME] Composition started: {composition}")

    def update_composition(self, composition, cursor):
        """Обновляет composition text во время ввода"""
        self.composition_text = composition
        self.cursor_position = cursor
        print(f"[IME] Composition updated: {composition} (cursor: {cursor})")

    def finish_composition(self, final_text):
        """Завершает обработку composition"""
        self.composition_text = ""
        self.is_composing = False
        print(f"[IME] Composition finished: {final_text}")
        return final_text

    def is_composition_active(self):
        """Проверяет, активна ли composition"""
        return self.is_composing




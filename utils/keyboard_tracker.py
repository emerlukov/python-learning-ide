"""
Надежный отслеживатель высоты клавиатуры на Android
"""
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.utils import platform

class KeyboardTracker:
    """Отслеживает высоту клавиатуры и вызывает колбеки"""

    def __init__(self):
        self.keyboard_height = 0
        self.last_window_height = Window.height
        self.callbacks = []
        self._monitoring = False
        self._last_reported_height = 0

    def start_monitoring(self):
        """Начинает мониторинг клавиатуры"""
        if self._monitoring:
            return

        self._monitoring = True

        # Привязываем к событиям окна
        Window.bind(
            keyboard_height=self._on_keyboard_height,
            size=self._on_window_size,
            on_keyboard=self._on_keyboard_event
        )

        # Запускаем периодический мониторинг
        Clock.schedule_interval(self._monitor_height, 0.05)

        print("[KeyboardTracker] Monitoring started")

    def stop_monitoring(self):
        """Останавливает мониторинг"""
        if not self._monitoring:
            return

        self._monitoring = False
        Window.unbind(
            keyboard_height=self._on_keyboard_height,
            size=self._on_window_size,
            on_keyboard=self._on_keyboard_event
        )
        Clock.unschedule(self._monitor_height)
        print("[KeyboardTracker] Monitoring stopped")

    def add_callback(self, callback):
        """Добавляет колбек для вызова при изменении высоты клавиатуры"""
        if callback not in self.callbacks:
            self.callbacks.append(callback)

    def remove_callback(self, callback):
        """Удаляет колбек"""
        if callback in self.callbacks:
            self.callbacks.remove(callback)

    def _on_keyboard_height(self, window, height):
        """Обработчик события on_keyboard_height"""
        print(f"[KeyboardTracker] keyboard_height event: {height}")
        self.keyboard_height = height
        self._notify_callbacks()

    def _on_window_size(self, window, size):
        """Обработчик события изменения размера окна"""
        current_height = size[1]
        height_diff = self.last_window_height - current_height

        # Если окно уменьшилось значительно, то появилась клавиатура
        if height_diff > 50:  # Минимальная высота клавиатуры ~50 пиксель
            self.keyboard_height = height_diff
            print(f"[KeyboardTracker] Detected keyboard from window resize: {self.keyboard_height}")
            self._notify_callbacks()
        elif height_diff < -50:  # Окно увеличилось - клавиатура скрыта
            self.keyboard_height = 0
            print("[KeyboardTracker] Keyboard hidden (window expanded)")
            self._notify_callbacks()

        self.last_window_height = current_height

    def _on_keyboard_event(self, window, key, scancode, codepoint, modifier):
        """Обработчик события клавиатуры"""
        # Любое нажатие на клавиатуру - обновляем
        Clock.schedule_once(lambda dt: self._notify_callbacks(), 0.01)
        return False

    def _monitor_height(self, dt):
        """Периодический мониторинг высоты"""
        # Способ 1: через Window.keyboard_height
        height = getattr(Window, 'keyboard_height', 0) or 0

        # Способ 2: через разницу высот окна
        if height == 0:
            current_height = Window.height
            height_diff = self.last_window_height - current_height
            if height_diff > 50:
                height = height_diff

        # Если высота изменилась, уведомляем
        if height != self._last_reported_height:
            self.keyboard_height = height
            self._last_reported_height = height
            self._notify_callbacks()

    def _notify_callbacks(self):
        """Вызывает все зарегистрированные колбеки"""
        for callback in self.callbacks:
            try:
                callback(self.keyboard_height)
            except Exception as e:
                print(f"[KeyboardTracker] Callback error: {e}")

    def get_keyboard_height(self):
        """Возвращает текущую высоту клавиатуры"""
        return self.keyboard_height


# Глобальный экземпляр
_tracker = None

def get_keyboard_tracker():
    """Возвращает глобальный экземпляр трекера"""
    global _tracker
    if _tracker is None:
        _tracker = KeyboardTracker()
        if platform == 'android':
            _tracker.start_monitoring()
    return _tracker


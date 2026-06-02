# widgets/vibrating_buttons.py
"""
Vibrating button classes with built-in haptic feedback
Базовые классы кнопок со встроенной вибрацией
"""
from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.behaviors import ButtonBehavior
from kivy.properties import BooleanProperty, NumericProperty
from kivymd.uix.button import MDRectangleFlatButton, MDIconButton, MDFlatButton
from utils.vibration_manager import VibrationManager


class VibratingMixin:
    """
    Миксин для добавления вибрации к кнопкам.
    Использует VibrationManager для централизованного управления.
    """

    vibrate_enabled = BooleanProperty(True)
    vibrate_duration = NumericProperty(0.02)
    vibrate_on_press = BooleanProperty(False)  # False = on_release, True = on_press

    def __init__(self, **kwargs):
        self.vibrate_enabled = kwargs.pop('vibrate_enabled', True)
        self.vibrate_duration = kwargs.pop('vibrate_duration', 0.02)
        self.vibrate_on_press = kwargs.pop('vibrate_on_press', False)
        super().__init__(**kwargs)

    def on_release(self):
        if self.vibrate_enabled and not self.vibrate_on_press:
            VibrationManager.vibrate(self.vibrate_duration)
        super().on_release()

    def on_press(self):
        if self.vibrate_enabled and self.vibrate_on_press:
            VibrationManager.vibrate(self.vibrate_duration)
        super().on_press()


class VibratingButton(VibratingMixin, Button):
    """Обычная кнопка с вибрацией"""
    pass


class VibratingMDRectangleFlatButton(VibratingMixin, MDRectangleFlatButton):
    """MD прямоугольная кнопка с вибрацией"""
    pass


class VibratingMDIconButton(VibratingMixin, MDIconButton):
    """MD иконка-кнопка с вибрацией"""
    pass


class VibratingMDFlatButton(VibratingMixin, MDFlatButton):
    """MD плоская кнопка с вибрацией"""
    pass


# Функции для быстрого создания кнопок с вибрацией
def make_vibrating_button(text, on_release=None, **kwargs):
    """Быстрое создание вибрирующей кнопки"""
    btn = VibratingButton(text=text, **kwargs)
    if on_release:
        btn.bind(on_release=on_release)
    return btn


def make_vibrating_md_button(text, on_release=None, **kwargs):
    """Быстрое создание вибрирующей MD кнопки"""
    btn = VibratingMDRectangleFlatButton(text=text, **kwargs)
    if on_release:
        btn.bind(on_release=on_release)
    return btn
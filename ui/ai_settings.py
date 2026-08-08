"""
Диалог настройки API-ключей ИИ
"""

from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.label import MDLabel
from kivy.metrics import dp
from kivy.uix.scrollview import ScrollView
from kivy.uix.modalview import ModalView
from kivy.clock import Clock
from kivy.utils import platform


class AISettingsContent(MDBoxLayout):
    def __init__(self, agent, locale="ru", **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.spacing = dp(10)
        self.padding = dp(12)
        self.size_hint_y = None
        self.bind(minimum_height=self.setter('height'))  # Для ScrollView
        self.agent = agent
        self.locale = locale

        # Загружаем тему для применения цветов
        try:
            from ide_core.themes import ThemeManager
            self.theme = ThemeManager.get_theme()
        except:
            self.theme = {
                'popup_bg': (0.188, 0.204, 0.251, 1),
                'text_color': (0.85, 0.88, 0.9, 1),
                'widget_bg': (0.141, 0.145, 0.149, 1)
            }

        # Применяем цвет фона к контейнеру
        self.md_bg_color = self.theme.get('popup_bg', (0.188, 0.204, 0.251, 1))

        self.add_widget(MDLabel(
            text="API-ключи ИИ-тьютора" if locale == "ru" else "AI Tutor API Keys",
            font_style="H6",
            size_hint_y=None,
            height=dp(30),
            theme_text_color="Custom",
            text_color=self.theme.get('text_color', (0.85, 0.88, 0.9, 1))
        ))

        self.groq_field = MDTextField(
            hint_text="Groq API Key" if locale == "en" else "Groq API Key (рекомендуется)",
            text=agent.groq_key,
            password=False,  # password=True вызывает проблемы на Android
            size_hint_y=None,
            height=dp(45),
            hint_text_color=self.theme.get('hint_text', (0.45, 0.48, 0.5, 1)),
            mode="fill",
            line_color_normal=self.theme.get('widget_bg', (0.141, 0.145, 0.149, 1)),
            line_color_focus=self.theme.get('accent', (0.95, 0.95, 1.0, 1)),
        )
        self.add_widget(self.groq_field)

        self.gemini_field = MDTextField(
            hint_text="Gemini API Key" if locale == "en" else "Gemini API Key (запасной)",
            text=agent.gemini_key,
            password=False,  # password=True вызывает проблемы на Android
            size_hint_y=None,
            height=dp(45),
            hint_text_color=self.theme.get('hint_text', (0.45, 0.48, 0.5, 1)),
            mode="fill",
            line_color_normal=self.theme.get('widget_bg', (0.141, 0.145, 0.149, 1)),
            line_color_focus=self.theme.get('accent', (0.95, 0.95, 1.0, 1)),
        )
        self.add_widget(self.gemini_field)

        self.add_widget(MDLabel(
            text="Provider:" if locale == "en" else "Провайдер:",
            size_hint_y=None,
            height=dp(25),
            theme_text_color="Custom",
            text_color=self.theme.get('text_color', (0.85, 0.88, 0.9, 1))
        ))

        # Простой выбор через кнопки
        self.provider = agent.preferred
        btn_box = MDBoxLayout(size_hint_y=None, height=dp(40), spacing=dp(5))
        self.btn_groq = MDRaisedButton(text="Groq", on_release=lambda x: self._set_provider("groq"))
        self.btn_gemini = MDRaisedButton(text="Gemini", on_release=lambda x: self._set_provider("gemini"))
        self.btn_auto = MDRaisedButton(text="Auto", on_release=lambda x: self._set_provider("auto"))
        btn_box.add_widget(self.btn_groq)
        btn_box.add_widget(self.btn_gemini)
        btn_box.add_widget(self.btn_auto)
        self.add_widget(btn_box)

        # Отложенное применение цветов для стабильности на Android
        Clock.schedule_once(self._apply_colors, 0.1)

        self.add_widget(MDLabel(
            text="Get keys:\n• Groq > console.groq.com/keys\n• Gemini > aistudio.google.com/apikey" if locale == "en" else "Получить ключи:\n• Groq > console.groq.com/keys\n• Gemini > aistudio.google.com/apikey",
            size_hint_y=None,
            height=dp(70),
            theme_text_color="Custom",
            text_color=self.theme.get('text_color', (0.85, 0.88, 0.9, 1))
        ))

    def _apply_colors(self, dt):
        """Отложенное применение цветов для стабильности"""
        try:
            from ide_core.themes import ThemeManager
            theme = ThemeManager.get_theme()
            selected_color = theme.get('btn_success_bg', (0.2, 0.5, 0.2, 1))
            normal_color = theme.get('widget_bg', (0.141, 0.145, 0.149, 1))
            text_color = theme.get('text_color', (0.85, 0.88, 0.9, 1))
        except Exception as e:
            # Дефолтные цвета если ThemeManager не работает
            selected_color = (0.2, 0.5, 0.2, 1)
            normal_color = (0.141, 0.145, 0.149, 1)
            text_color = (0.85, 0.88, 0.9, 1)

        # Применяем цвета фона кнопок
        self.btn_groq.background_color = normal_color
        self.btn_gemini.background_color = normal_color
        self.btn_auto.background_color = normal_color

        # Применяем цвета текста кнопок
        self.btn_groq.text_color = text_color
        self.btn_gemini.text_color = text_color
        self.btn_auto.text_color = text_color

        # Выделяем выбранную кнопку
        if self.provider == "groq":
            self.btn_groq.background_color = selected_color
        elif self.provider == "gemini":
            self.btn_gemini.background_color = selected_color
        elif self.provider == "auto":
            self.btn_auto.background_color = selected_color

    def _set_provider(self, name):
        self.provider = name
        self._update_provider_buttons()

    def _update_provider_buttons(self):
        """Отложенное обновление кнопок для стабильности"""
        Clock.schedule_once(self._do_update_buttons, 0.05)

    def _do_update_buttons(self, dt):
        """Фактическое обновление кнопок"""
        try:
            from ide_core.themes import ThemeManager
            theme = ThemeManager.get_theme()
            selected_color = theme.get('btn_success_bg', (0.2, 0.5, 0.2, 1))
            normal_color = theme.get('widget_bg', (0.141, 0.145, 0.149, 1))
            text_color = theme.get('text_color', (0.85, 0.88, 0.9, 1))
        except Exception as e:
            selected_color = (0.2, 0.5, 0.2, 1)
            normal_color = (0.141, 0.145, 0.149, 1)
            text_color = (0.85, 0.88, 0.9, 1)

        # Сбрасываем все кнопки на обычный цвет
        self.btn_groq.background_color = normal_color
        self.btn_gemini.background_color = normal_color
        self.btn_auto.background_color = normal_color

        # Применяем цвета текста кнопок
        self.btn_groq.text_color = text_color
        self.btn_gemini.text_color = text_color
        self.btn_auto.text_color = text_color

        # Выделяем выбранную кнопку
        if self.provider == "groq":
            self.btn_groq.background_color = selected_color
        elif self.provider == "gemini":
            self.btn_gemini.background_color = selected_color
        elif self.provider == "auto":
            self.btn_auto.background_color = selected_color

    def get_values(self):
        return {
            "groq": self.groq_field.text.strip(),
            "gemini": self.gemini_field.text.strip(),
            "provider": self.provider,
        }


def open_ai_settings(agent, locale="ru", on_save=None):
    # Безопасная загрузка темы
    try:
        from ide_core.themes import ThemeManager
        theme = ThemeManager.get_theme()
    except Exception as e:
        theme = {
            'popup_bg': (0.188, 0.204, 0.251, 1),
            'text_color': (0.85, 0.88, 0.9, 1),
            'widget_bg': (0.141, 0.145, 0.149, 1),
            'btn_success_bg': (0.2, 0.5, 0.2, 1)
        }

    # Используем класс content вместо прямого создания layout
    content = AISettingsContent(agent, locale=locale)

    # Кнопки внизу
    button_box = MDBoxLayout(
        orientation="horizontal",
        size_hint_y=None,
        height=dp(50),
        spacing=dp(10),
        padding=dp(10)
    )

    cancel_btn = MDFlatButton(
        text="Cancel" if locale == "en" else "Отмена",
        on_release=lambda x: modal.dismiss(),
        theme_text_color="Custom",
        text_color=theme.get('text_color', (0.85, 0.88, 0.9, 1))
    )
    save_btn = MDRaisedButton(
        text="Save" if locale == "en" else "Сохранить",
        on_release=lambda x: _save(),
        md_bg_color=theme.get('btn_success_bg', (0.2, 0.5, 0.2, 1)),
        text_color=(1, 1, 1, 1)
    )

    button_box.add_widget(cancel_btn)
    button_box.add_widget(save_btn)
    content.add_widget(button_box)

    def _save():
        try:
            vals = content.get_values()
            agent.set_keys(vals["groq"], vals["gemini"], vals["provider"])
            if on_save:
                on_save()
            modal.dismiss()
        except Exception as e:
            print(f"Error saving AI settings: {e}")
            modal.dismiss()

    # Оборачиваем в ScrollView для прокрутки если контент не помещается
    scroll = ScrollView(
        do_scroll_x=False,
        do_scroll_y=True,
        size_hint=(1, 1)
    )
    scroll.add_widget(content)

    # Адаптивный размер для Android
    if platform == 'android':
        size_hint = (0.9, 0.5)
    else:
        size_hint = (0.9, 0.7)

    modal = ModalView(
        size_hint=size_hint,
        background_color=theme.get('popup_bg', (0.188, 0.204, 0.251, 1))
    )
    modal.add_widget(scroll)
    modal.open()
    return modal

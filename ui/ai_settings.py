"""
Диалог настройки API-ключей ИИ
"""

from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.label import MDLabel
from kivymd.uix.dialog import MDDialog
from kivymd.uix.selectioncontrol import MDSwitch
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout


class AISettingsContent(MDBoxLayout):
    def __init__(self, agent, locale="ru", **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.spacing = dp(12)
        self.padding = dp(16)
        self.size_hint_y = None
        self.height = dp(420)
        self.agent = agent
        self.locale = locale

        self.add_widget(MDLabel(
            text="API-ключи ИИ-тьютора" if locale == "ru" else "AI Tutor API Keys",
            font_style="H6",
            size_hint_y=None,
            height=dp(36),
        ))

        self.groq_field = MDTextField(
            hint_text="Groq API Key (рекомендуется)",
            text=agent.groq_key,
            password=True,
            size_hint_y=None,
            height=dp(48),
        )
        self.add_widget(self.groq_field)

        self.gemini_field = MDTextField(
            hint_text="Gemini API Key (запасной)",
            text=agent.gemini_key,
            password=True,
            size_hint_y=None,
            height=dp(48),
        )
        self.add_widget(self.gemini_field)

        self.add_widget(MDLabel(
            text="Предпочтительный провайдер:",
            size_hint_y=None,
            height=dp(28),
        ))

        # Простой выбор через кнопки
        self.provider = agent.preferred
        btn_box = MDBoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        self.btn_groq = MDRaisedButton(text="Groq", on_release=lambda x: self._set_provider("groq"))
        self.btn_gemini = MDRaisedButton(text="Gemini", on_release=lambda x: self._set_provider("gemini"))
        self.btn_auto = MDRaisedButton(text="Auto", on_release=lambda x: self._set_provider("auto"))
        btn_box.add_widget(self.btn_groq)
        btn_box.add_widget(self.btn_gemini)
        btn_box.add_widget(self.btn_auto)
        self.add_widget(btn_box)
        
        # Применяем цвета сразу при инициализации
        from ide_core.themes import ThemeManager
        theme = ThemeManager.get_theme()
        selected_color = theme.get('btn_success_bg', (0.2, 0.5, 0.2, 1))
        normal_color = theme.get('widget_bg', (0.3, 0.3, 0.3, 1))
        
        # Устанавливаем начальные цвета
        self.btn_groq.md_bg_color = normal_color
        self.btn_gemini.md_bg_color = normal_color
        self.btn_auto.md_bg_color = normal_color
        
        # Выделяем выбранную кнопку
        if self.provider == "groq":
            self.btn_groq.md_bg_color = selected_color
        elif self.provider == "gemini":
            self.btn_gemini.md_bg_color = selected_color
        elif self.provider == "auto":
            self.btn_auto.md_bg_color = selected_color

        self.add_widget(MDLabel(
            text="Получить ключи:\n• Groq > console.groq.com/keys\n• Gemini > aistudio.google.com/apikey" if locale == "ru" else "Get keys:\n• Groq > console.groq.com/keys\n• Gemini > aistudio.google.com/apikey",
            size_hint_y=None,
            height=dp(80),
            theme_text_color="Secondary",
            font_name="DejaVuSans",
        ))

    def _set_provider(self, name):
        self.provider = name
        self._update_provider_buttons()

    def _update_provider_buttons(self):
        # Визуальное выделение выбранной кнопки
        from ide_core.themes import ThemeManager
        theme = ThemeManager.get_theme()
        
        # Цвет выбранной кнопки (яркое выделение)
        selected_color = theme.get('btn_success_bg', (0.2, 0.5, 0.2, 1))
        # Цвет невыбранных кнопок (обычный)
        normal_color = theme.get('widget_bg', (0.3, 0.3, 0.3, 1))
        
        # Сбрасываем все кнопки на обычный цвет
        self.btn_groq.md_bg_color = normal_color
        self.btn_gemini.md_bg_color = normal_color
        self.btn_auto.md_bg_color = normal_color
        
        # Выделяем выбранную кнопку
        if self.provider == "groq":
            self.btn_groq.md_bg_color = selected_color
        elif self.provider == "gemini":
            self.btn_gemini.md_bg_color = selected_color
        elif self.provider == "auto":
            self.btn_auto.md_bg_color = selected_color

    def get_values(self):
        return {
            "groq": self.groq_field.text.strip(),
            "gemini": self.gemini_field.text.strip(),
            "provider": self.provider,
        }


def open_ai_settings(agent, locale="ru", on_save=None):
    content = AISettingsContent(agent, locale=locale)

    def save(*args):
        vals = content.get_values()
        agent.set_keys(vals["groq"], vals["gemini"], vals["provider"])
        if on_save:
            on_save()
        dialog.dismiss()

    dialog = MDDialog(
        title="Настройки ИИ" if locale == "ru" else "AI Settings",
        type="custom",
        content_cls=content,
        buttons=[
            MDFlatButton(text="Отмена" if locale == "ru" else "Cancel", on_release=lambda x: dialog.dismiss()),
            MDRaisedButton(text="Сохранить" if locale == "ru" else "Save", on_release=save),
        ],
    )
    dialog.open()
    return dialog

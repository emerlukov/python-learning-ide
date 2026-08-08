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


class AISettingsContent(MDBoxLayout):
    def __init__(self, agent, locale="ru", **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.spacing = dp(10)
        self.padding = dp(12)
        self.size_hint_y = None
        self.agent = agent
        self.locale = locale

        self.add_widget(MDLabel(
            text="API-ключи ИИ-тьютора" if locale == "ru" else "AI Tutor API Keys",
            font_style="H6",
            size_hint_y=None,
            height=dp(30),
        ))

        self.groq_field = MDTextField(
            hint_text="Groq API Key" if locale == "en" else "Groq API Key (рекомендуется)",
            text=agent.groq_key,
            password=True,
            size_hint_y=None,
            height=dp(45),
        )
        self.add_widget(self.groq_field)

        self.gemini_field = MDTextField(
            hint_text="Gemini API Key" if locale == "en" else "Gemini API Key (запасной)",
            text=agent.gemini_key,
            password=True,
            size_hint_y=None,
            height=dp(45),
        )
        self.add_widget(self.gemini_field)

        self.add_widget(MDLabel(
            text="Provider:" if locale == "en" else "Провайдер:",
            size_hint_y=None,
            height=dp(25),
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
            text="Get keys:\n• Groq > console.groq.com/keys\n• Gemini > aistudio.google.com/apikey" if locale == "en" else "Получить ключи:\n• Groq > console.groq.com/keys\n• Gemini > aistudio.google.com/apikey",
            size_hint_y=None,
            height=dp(70),
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
    from ide_core.themes import ThemeManager
    theme = ThemeManager.get_theme()

    # Основной контейнер
    main_box = MDBoxLayout(
        orientation="vertical",
        spacing=dp(10),
        padding=dp(12),
        md_bg_color=theme.get('popup_bg', (0.1, 0.1, 0.1, 1))
    )

    # Заголовок
    main_box.add_widget(MDLabel(
        text="API-ключи ИИ-тьютора" if locale == "ru" else "AI Tutor API Keys",
        font_style="H6",
        size_hint_y=None,
        height=dp(30),
    ))

    # Поле Groq
    groq_field = MDTextField(
        hint_text="Groq API Key" if locale == "en" else "Groq API Key (рекомендуется)",
        text=agent.groq_key,
        password=True,
        size_hint_y=None,
        height=dp(45),
    )
    main_box.add_widget(groq_field)

    # Поле Gemini
    gemini_field = MDTextField(
        hint_text="Gemini API Key" if locale == "en" else "Gemini API Key (запасной)",
        text=agent.gemini_key,
        password=True,
        size_hint_y=None,
        height=dp(45),
    )
    main_box.add_widget(gemini_field)

    # Выбор провайдера
    main_box.add_widget(MDLabel(
        text="Provider:" if locale == "en" else "Провайдер:",
        size_hint_y=None,
        height=dp(25),
    ))

    # ИСПРАВЛЕНИЕ: Используем список вместо nonlocal
    provider_state = [agent.preferred]  # Используем список для изменяемого состояния
    
    btn_box = MDBoxLayout(size_hint_y=None, height=dp(40), spacing=dp(5))
    btn_groq = MDRaisedButton(text="Groq", on_release=lambda x: _set_provider("groq"))
    btn_gemini = MDRaisedButton(text="Gemini", on_release=lambda x: _set_provider("gemini"))
    btn_auto = MDRaisedButton(text="Auto", on_release=lambda x: _set_provider("auto"))
    btn_box.add_widget(btn_groq)
    btn_box.add_widget(btn_gemini)
    btn_box.add_widget(btn_auto)
    main_box.add_widget(btn_box)

    # Применяем цвета
    selected_color = theme.get('btn_success_bg', (0.2, 0.5, 0.2, 1))
    normal_color = theme.get('widget_bg', (0.3, 0.3, 0.3, 1))

    btn_groq.md_bg_color = normal_color
    btn_gemini.md_bg_color = normal_color
    btn_auto.md_bg_color = normal_color

    if provider_state[0] == "groq":
        btn_groq.md_bg_color = selected_color
    elif provider_state[0] == "gemini":
        btn_gemini.md_bg_color = selected_color
    elif provider_state[0] == "auto":
        btn_auto.md_bg_color = selected_color

    # Информация о ключах
    main_box.add_widget(MDLabel(
        text="Get keys:\n• Groq > console.groq.com/keys\n• Gemini > aistudio.google.com/apikey" if locale == "en" else "Получить ключи:\n• Groq > console.groq.com/keys\n• Gemini > aistudio.google.com/apikey",
        size_hint_y=None,
        height=dp(70),
        theme_text_color="Secondary",
        font_name="DejaVuSans",
    ))

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
        on_release=lambda x: modal.dismiss()
    )
    save_btn = MDRaisedButton(
        text="Save" if locale == "en" else "Сохранить",
        on_release=lambda x: _save()
    )

    button_box.add_widget(cancel_btn)
    button_box.add_widget(save_btn)
    main_box.add_widget(button_box)

    def _set_provider(name):
        provider_state[0] = name  # Обновляем значение в списке
        btn_groq.md_bg_color = normal_color
        btn_gemini.md_bg_color = normal_color
        btn_auto.md_bg_color = normal_color
        if provider_state[0] == "groq":
            btn_groq.md_bg_color = selected_color
        elif provider_state[0] == "gemini":
            btn_gemini.md_bg_color = selected_color
        elif provider_state[0] == "auto":
            btn_auto.md_bg_color = selected_color

    def _save():
        agent.set_keys(groq_field.text.strip(), gemini_field.text.strip(), provider_state[0])
        if on_save:
            on_save()
        modal.dismiss()

    # Создаем модальное окно
    modal = ModalView(
        size_hint=(0.9, 0.7),
        background_color=theme.get('popup_bg', (0.1, 0.1, 0.1, 1))
    )
    modal.add_widget(main_box)
    modal.open()
    return modal

"""
Диалог настройки API-ключей ИИ
"""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.modalview import ModalView
from kivy.metrics import dp
from kivy.utils import platform


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
            'btn_success_bg': (0.2, 0.5, 0.2, 1),
            'input_bg': (0.188, 0.204, 0.251, 1),
            'input_text': (1.0, 1.0, 1.0, 1)
        }

    # Основной контейнер
    main_box = BoxLayout(
        orientation="vertical",
        spacing=dp(10),
        padding=dp(12),
        size_hint_y=None
    )

    # Заголовок
    main_box.add_widget(Label(
        text="API-ключи ИИ-тьютора" if locale == "ru" else "AI Tutor API Keys",
        font_size=dp(18),
        size_hint_y=None,
        height=dp(30)
    ))

    # Поле Groq
    groq_field = TextInput(
        hint_text="Groq API Key" if locale == "en" else "Groq API Key (рекомендуется)",
        text=agent.groq_key,
        password=False,  # password=True вызывает проблемы на Android
        size_hint_y=None,
        height=dp(45),
        padding=[dp(10), dp(10), dp(10), dp(10)],
        multiline=False
    )
    main_box.add_widget(groq_field)

    # Поле Gemini
    gemini_field = TextInput(
        hint_text="Gemini API Key" if locale == "en" else "Gemini API Key (запасной)",
        text=agent.gemini_key,
        password=False,  # password=True вызывает проблемы на Android
        size_hint_y=None,
        height=dp(45),
        padding=[dp(10), dp(10), dp(10), dp(10)],
        multiline=False
    )
    main_box.add_widget(gemini_field)

    # Выбор провайдера
    main_box.add_widget(Label(
        text="Provider:" if locale == "en" else "Провайдер:",
        size_hint_y=None,
        height=dp(25)
    ))

    # Кнопки провайдера
    provider_state = [agent.preferred]  # Используем список для изменяемого состояния

    btn_box = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(5))

    def set_provider(name):
        provider_state[0] = name
        # Обновляем цвета кнопок
        normal_color = theme.get('widget_bg', (0.141, 0.145, 0.149, 1))
        selected_color = theme.get('btn_success_bg', (0.2, 0.5, 0.2, 1))

        if provider_state[0] == "groq":
            btn_groq.background_color = selected_color
            btn_gemini.background_color = normal_color
            btn_auto.background_color = normal_color
        elif provider_state[0] == "gemini":
            btn_groq.background_color = normal_color
            btn_gemini.background_color = selected_color
            btn_auto.background_color = normal_color
        elif provider_state[0] == "auto":
            btn_groq.background_color = normal_color
            btn_gemini.background_color = normal_color
            btn_auto.background_color = selected_color

    btn_groq = Button(
        text="Groq",
        on_release=lambda x: set_provider("groq"),
        background_normal='', background_down='',
        size_hint_y=None, height=dp(35)
    )
    btn_gemini = Button(
        text="Gemini",
        on_release=lambda x: set_provider("gemini"),
        background_normal='', background_down='',
        size_hint_y=None, height=dp(35)
    )
    btn_auto = Button(
        text="Auto",
        on_release=lambda x: set_provider("auto"),
        background_normal='', background_down='',
        size_hint_y=None, height=dp(35)
    )

    btn_box.add_widget(btn_groq)
    btn_box.add_widget(btn_gemini)
    btn_box.add_widget(btn_auto)
    main_box.add_widget(btn_box)

    # Инициализация цветов кнопок
    normal_color = theme.get('widget_bg', (0.141, 0.145, 0.149, 1))
    selected_color = theme.get('btn_success_bg', (0.2, 0.5, 0.2, 1))

    # Сначала сбрасываем все на нормальный цвет
    btn_groq.background_color = normal_color
    btn_gemini.background_color = normal_color
    btn_auto.background_color = normal_color

    # Затем выделяем выбранную
    if provider_state[0] == "groq":
        btn_groq.background_color = selected_color
    elif provider_state[0] == "gemini":
        btn_gemini.background_color = selected_color
    elif provider_state[0] == "auto":
        btn_auto.background_color = selected_color

    # Информация о ключах
    main_box.add_widget(Label(
        text="Get keys:\n• Groq > console.groq.com/keys\n• Gemini > aistudio.google.com/apikey" if locale == "en" else "Получить ключи:\n• Groq > console.groq.com/keys\n• Gemini > aistudio.google.com/apikey",
        size_hint_y=None,
        height=dp(70)
    ))

    # Кнопки внизу
    button_box = BoxLayout(
        orientation="horizontal",
        size_hint_y=None,
        height=dp(50),
        spacing=dp(10),
        padding=dp(10)
    )

    def _save():
        try:
            agent.set_keys(groq_field.text.strip(), gemini_field.text.strip(), provider_state[0])
            if on_save:
                on_save()
            modal.dismiss()
        except Exception as e:
            print(f"Error saving AI settings: {e}")
            modal.dismiss()

    cancel_btn = Button(
        text="Cancel" if locale == "en" else "Отмена",
        on_release=lambda x: modal.dismiss(),
        background_normal='', background_down='',
        size_hint_y=None, height=dp(35)
    )
    save_btn = Button(
        text="Save" if locale == "en" else "Сохранить",
        on_release=lambda x: _save(),
        background_normal='', background_down='',
        size_hint_y=None, height=dp(35)
    )

    # Применяем цвета кнопок
    cancel_btn.background_color = theme.get('widget_bg', (0.141, 0.145, 0.149, 1))
    save_btn.background_color = theme.get('btn_success_bg', (0.2, 0.5, 0.2, 1))

    button_box.add_widget(cancel_btn)
    button_box.add_widget(save_btn)
    main_box.add_widget(button_box)

    # Оборачиваем в ScrollView для прокрутки если контент не помещается
    scroll = ScrollView(
        do_scroll_x=False,
        do_scroll_y=True,
        size_hint=(1, 1)
    )
    scroll.add_widget(main_box)

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

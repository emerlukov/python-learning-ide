"""
Окно чата с ИИ-тьютором
"""

from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDIconButton
from kivymd.uix.label import MDLabel
from kivymd.uix.card import MDCard 
from kivymd.uix.scrollview import MDScrollView
from kivy.uix.modalview import ModalView
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.core.window import Window
from ide_core.themes import DARK_THEME, LIGHT_THEME, ThemeManager
from widgets.markdown_label import MarkdownLabel


class AiChatScreen(MDBoxLayout):
    def __init__(self, agent, locale="ru", get_context_callback=None, **kwargs):
        super().__init__(**kwargs)
        self.agent = agent
        self.locale = locale
        self.get_context = get_context_callback or (lambda: "")
        self.modal = None
        self._is_generating = False
        self._current_bot_card = None
        self._current_bot_label = None
        self._user_scrolled = False  # Флаг, чтобы определить, скроллил ли пользователь

        # Получаем тему
        self._update_theme()

        # НЕ слушаем клавиатуру для скролла
        # Window.bind(keyboard_height=self._on_keyboard_height)  # УБИРАЕМ!
        
        # Layout
        self.orientation = "vertical"
        self.spacing = dp(10)
        self.padding = dp(16)
        self.md_bg_color = self.theme['popup_bg']
        
        # Верхняя панель
        header_box = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(50),
            spacing=dp(0),
            padding=dp(10)
        )
        
        title_label = MDLabel(
            text="ИИ-тьютор" if locale == "ru" else "AI Tutor",
            size_hint_x=0.8,
            font_style="H6",
            theme_text_color="Custom",
            text_color=self.theme['text_color']
        )
        
        close_btn = Button(
            text='X',
            size_hint_x=None,
            width=dp(40),
            background_color=self.theme.get('btn_danger_bg', (0.5, 0.2, 0.2, 1)),
            background_normal='', background_down='',
            color=(1, 1, 1, 1),
            font_size=dp(16),
            bold=True
        )
        close_btn.bind(on_release=self.close_modal)
        
        header_box.add_widget(title_label)
        header_box.add_widget(close_btn)
        self.add_widget(header_box)
        
        # Контейнер
        content_box = MDBoxLayout(
            orientation="vertical",
            size_hint_y=1
        )
        
        # ScrollView с сообщениями
        self.scroll = ScrollView(
            do_scroll_x=False,
            do_scroll_y=True,
            size_hint_y=1
        )
        
        self.messages_box = BoxLayout(
            orientation="vertical",
            spacing=dp(10),
            size_hint_y=None,
            padding=dp(8)
        )
        
        # ВАЖНО: НЕ привязываем minimum_height к высоте!
        # Вместо этого устанавливаем высоту вручную при добавлении виджетов
        self.scroll.add_widget(self.messages_box)
        content_box.add_widget(self.scroll)

        # Быстрые действия
        actions_box = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(40),
            spacing=dp(8)
        )
        
        btn_clear = MDIconButton(
            icon="delete",
            on_release=lambda x: self._quick("clear"),
            size_hint_x=None,
            width=dp(40),
            theme_text_color="Custom",
            text_color=self.theme['text_color']
        )
        btn_error = MDIconButton(
            icon="alert-circle",
            on_release=lambda x: self._quick("error"),
            size_hint_x=None,
            width=dp(40),
            theme_text_color="Custom",
            text_color=self.theme['text_color']
        )
        btn_review = MDIconButton(
            icon="code-tags",
            on_release=lambda x: self._quick("review"),
            size_hint_x=None,
            width=dp(40),
            theme_text_color="Custom",
            text_color=self.theme['text_color']
        )

        self.stop_btn = MDIconButton(
            icon="stop",
            size_hint_x=None,
            width=dp(40),
            height=dp(40),
            theme_text_color="Custom",
            text_color=self.theme['text_color'],
            md_bg_color=self.theme['widget_bg'],
            on_release=self._stop_generation
        )
        self.stop_btn.disabled = True

        actions_box.add_widget(btn_clear)
        actions_box.add_widget(btn_error)
        actions_box.add_widget(btn_review)
        actions_box.add_widget(self.stop_btn)
        content_box.add_widget(actions_box)

        # Поле ввода
        input_box = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(80),
            spacing=dp(10)
        )
        
        self.text_input = TextInput(
            hint_text="Спроси что-нибудь..." if locale == "ru" else "Ask something...",
            size_hint_x=1,
            multiline=True,
            foreground_color=self.theme['text_color'],
            hint_text_color=self.theme['text_color'],
            background_color=self.theme['widget_bg'],
            cursor_color=self.theme['text_color'],
            padding=[dp(10), dp(10)],
            input_type='text'
        )

        send_btn = MDIconButton(
            icon="send",
            size_hint_x=None,
            width=dp(30),
            height=dp(30),
            icon_size=dp(16),
            theme_text_color="Custom",
            text_color=(0, 0, 0, 1),
            md_bg_color=self.theme.get('run_btn_bg', (0.596, 0.486, 1.0, 1)),
            on_release=self._send
        )

        input_box.add_widget(self.text_input)
        input_box.add_widget(send_btn)
        content_box.add_widget(input_box)

        self.add_widget(content_box)

        # Загружаем историю
        Clock.schedule_once(lambda dt: self._load_history(), 0.05)

    def _load_history(self):
        """Загружает историю без автоскролла"""
        with self.agent._lock:
            history = self.agent.history.copy()

        if not history:
            self._add_bot(
                "Привет! Я ИИ-тьютор по Python. Задавай вопросы о коде, ошибках или уроках!" if self.locale == "ru"
                else "Hi! I'm an AI Python tutor. Ask about code, errors or lessons!"
            )
            return

        for msg in history:
            if msg["role"] == "user":
                self._add_user(msg["content"])
            elif msg["role"] == "assistant":
                self._add_bot(msg["content"])

        # НЕ скроллим вниз - оставляем наверху
    
    def _update_theme(self):
        try:
            if ThemeManager:
                theme = ThemeManager.get_theme()
                if theme and theme.get('name') == 'light':
                    self.theme = LIGHT_THEME
                else:
                    self.theme = DARK_THEME
        except:
            self.theme = DARK_THEME
    
    def close_modal(self, *args):
        if self.modal:
            self.modal.dismiss()
    
    def _add_user(self, text):
        self._update_theme()
        
        card = MDCard(
            size_hint_y=None,
            padding=dp(10),
            radius=[12],
            pos_hint={"right": 1},
            md_bg_color=self.theme['widget_bg'],
        )
        
        label = Label(
            text=text,
            size_hint_y=None,
            valign='top',
            halign='right',
            text_size=(None, None),
            color=self.theme['text_color'],
            font_size=dp(14)
        )
        
        card.add_widget(label)
        self.messages_box.add_widget(card)
        
        # ОБНОВЛЯЕМ ВЫСОТУ ВРУЧНУЮ
        def update_height(dt):
            if hasattr(label, 'texture_size') and label.texture_size:
                label.text_size = (card.width - dp(24), None)
                label.height = label.texture_size[1]
                card.height = label.height + dp(20)
                
                # ОБНОВЛЯЕМ ОБЩУЮ ВЫСОТУ КОНТЕЙНЕРА
                self._update_messages_height()
        
        Clock.schedule_once(update_height, 0.1)
    
    def _update_messages_height(self):
        """Обновляет общую высоту контейнера сообщений"""
        total_height = dp(8)  # padding
        for child in self.messages_box.children:
            if hasattr(child, 'height'):
                total_height += child.height + dp(10)  # spacing
        
        # Устанавливаем высоту контейнера
        self.messages_box.height = total_height
        
        # НЕ скроллим автоматически!
    
    def _add_bot(self, text, is_streaming=False):
        self._update_theme()

        if is_streaming and self._current_bot_card:
            # Обновляем существующую карточку
            self._current_bot_label.set_text(text)
            self._update_bot_height()
            return

        card = MDCard(
            size_hint_y=None,
            padding=dp(10),
            radius=[12],
            md_bg_color=self.theme['widget_bg'],
        )

        label = MarkdownLabel(
            text=text,
            font_size=dp(14)
        )

        card.add_widget(label)
        self.messages_box.add_widget(card)

        self._current_bot_card = card
        self._current_bot_label = label

        # Устанавливаем высоту
        def update_height(dt):
            if hasattr(label, 'height') and label.height > 0:
                card.height = label.height + dp(20)
            else:
                card.height = dp(60)
            
            # ОБНОВЛЯЕМ ОБЩУЮ ВЫСОТУ КОНТЕЙНЕРА
            self._update_messages_height()
        
        Clock.schedule_once(update_height, 0.1)

    def _update_bot_height(self):
        """Обновляет высоту карточки бота"""
        if self._current_bot_card and self._current_bot_label:
            def update_height(dt):
                if hasattr(self._current_bot_label, 'height') and self._current_bot_label.height > 0:
                    self._current_bot_card.height = self._current_bot_label.height + dp(20)
                else:
                    self._current_bot_card.height = dp(60)
                
                # ОБНОВЛЯЕМ ОБЩУЮ ВЫСОТУ
                self._update_messages_height()
            
            Clock.schedule_once(update_height, 0.05)
    
    def _send(self, *args):
        text = self.text_input.text.strip()
        if not text:
            return
        self.text_input.text = ""
        self._add_user(text)

        self._is_generating = True
        self.text_input.disabled = True
        self.stop_btn.disabled = False

        self._add_bot("", is_streaming=True)

        def stream_callback(chunk):
            if not self._is_generating:
                return
            try:
                current_text = self._current_bot_label.text if self._current_bot_label else ""
                new_text = current_text + chunk
                self._add_bot(new_text, is_streaming=True)
            except Exception as e:
                print(f"[AI Chat] Stream callback error: {e}")

        def ok(answer):
            self._is_generating = False
            self.text_input.disabled = False
            self.stop_btn.disabled = True
            self._add_bot(answer, is_streaming=True)
            self._current_bot_card = None
            self._current_bot_label = None
            # НЕ скроллим

        def err(e):
            self._is_generating = False
            self.text_input.disabled = False
            self.stop_btn.disabled = True
            self._add_bot(f"Ошибка: {e}")
            self._current_bot_card = None
            self._current_bot_label = None

        context = self.get_context()
        self.agent.ask(
            text,
            context=context,
            locale=self.locale,
            on_success=ok,
            on_error=err,
            stream=True,
            stream_callback=stream_callback
        )

    def _stop_generation(self, *args):
        if self._is_generating:
            self._is_generating = False
            self.agent.stop_generation()
            self.text_input.disabled = False
            self.stop_btn.disabled = True
            self._current_bot_card = None
            self._current_bot_label = None

    def _quick(self, action):
        if action == "clear":
            self.agent.clear_history()
            self.messages_box.clear_widgets()
            self.text_input.text = ""
            self._add_bot("Чат очищен." if self.locale == "ru" else "Chat cleared.")
            return
        
        context = self.get_context()
        
        def ok(answer):
            self._add_bot(answer)
            # НЕ скроллим
        
        def err(e):
            self._add_bot(f"Ошибка: {e}")
        
        if action == "error":
            self.agent.explain_error(
                "Последняя ошибка выполнения (если была)",
                code=context,
                locale=self.locale,
                on_success=ok,
                on_error=err,
            )
        elif action == "review":
            if not context.strip():
                self._add_bot("Нет кода для проверки." if self.locale == "ru" else "No code to check.")
                return
            self.agent.review_code(context, locale=self.locale, on_success=ok, on_error=err)


def open_ai_chat(agent, locale="ru", get_context_callback=None):
    print(f"[AI Chat] Opening AI chat screen...")

    chat_screen = AiChatScreen(agent, locale=locale, get_context_callback=get_context_callback)
    chat_screen.name = "ai_chat_screen"

    try:
        if ThemeManager:
            theme = ThemeManager.get_theme()
            bg_color = theme.get('window_bg', (0.15, 0.15, 0.2, 0.95))
        else:
            bg_color = (0.15, 0.15, 0.2, 0.95)
    except:
        bg_color = (0.15, 0.15, 0.2, 0.95)

    modal = ModalView(
        size_hint=(0.95, 0.85),
        background_color=bg_color,
    )

    chat_screen.modal = modal

    Window.softinput_mode = 'pan'
    original_size_hint_y = modal.size_hint_y

    def on_keyboard_height(instance, keyboard_height):
        if keyboard_height > 0:
            window_height = Window.height
            available_height = window_height - keyboard_height
            modal.size_hint_y = min(0.85, available_height / window_height)
        else:
            modal.size_hint_y = original_size_hint_y

    Window.bind(keyboard_height=on_keyboard_height)

    modal.add_widget(chat_screen)
    modal.open()

    def on_dismiss(instance):
        Window.unbind(keyboard_height=on_keyboard_height)
        Window.softinput_mode = 'below_target'

    modal.bind(on_dismiss=on_dismiss)

    return modal
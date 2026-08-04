"""
Окно чата с ИИ-тьютором
"""

from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDIconButton, MDRaisedButton, MDFlatButton
from kivymd.uix.label import MDLabel
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.card import MDCard
from kivymd.uix.dialog import MDDialog
from kivymd.uix.snackbar import Snackbar
from kivy.uix.screenmanager import Screen
from kivy.uix.modalview import ModalView
from kivy.uix.button import Button  # Добавляем обычный Button
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.uix.label import Label  # Добавляем обычный Label
from kivy.uix.textinput import TextInput  # Добавляем обычный TextInput
from kivy.core.clipboard import Clipboard
from ide_core.themes import DARK_THEME, LIGHT_THEME, ThemeManager
from widgets.markdown_label import MarkdownLabel


class AiChatScreen(MDBoxLayout):
    def __init__(self, agent, locale="ru", get_context_callback=None, **kwargs):
        super().__init__(**kwargs)
        self.agent = agent
        self.locale = locale
        self.get_context = get_context_callback or (lambda: "")
        self.modal = None  # Ссылка на modal для закрытия
        self._is_generating = False  # Флаг генерации
        self._current_bot_card = None  # Текущая карточка бота для streaming
        self._current_bot_label = None  # Текущий label бота для streaming

        # Получаем тему динамически
        self._update_theme()
        
        # Layout свойства
        self.orientation = "vertical"
        self.spacing = dp(10)
        self.padding = dp(16)
        self.md_bg_color = self.theme['popup_bg']
        
        # Верхняя панель с заголовком и кнопкой закрытия
        header_box = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(50),
            spacing=dp(0),  # Убираем отступы
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
            font_name='DejaVuSans',
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
        
        # Создаем контейнер для ScrollView и нижних элементов
        content_box = MDBoxLayout(
            orientation="vertical",
            size_hint_y=1  # Занимает всё оставшееся пространство
        )
        
        # ScrollView с сообщениями
        self.scroll = MDScrollView(
            do_scroll_x=False,
            do_scroll_y=True,
            size_hint_y=1  # Занимает всё доступное пространство в content_box
        )
        
        self.messages_box = MDBoxLayout(
            orientation="vertical",
            spacing=dp(10),
            size_hint_y=None,
            padding=dp(8)
        )
        self.messages_box.bind(minimum_height=self.messages_box.setter('height'))
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

        # Кнопка остановки генерации
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
        self.stop_btn.disabled = True  # Сначала отключена

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
            foreground_color=self.theme['text_color'],  # Вместо text_color
            hint_text_color=self.theme['text_color'],
            background_color=self.theme['widget_bg'],
            cursor_color=self.theme['text_color'],
            padding=[dp(10), dp(10)],
        )

        send_btn = MDIconButton(
            icon="send",
            size_hint_x=None,
            width=dp(30),
            height=dp(30),
            icon_size=dp(16),
            theme_text_color="Custom",
            text_color=(0, 0, 0, 1),  # Черный цвет иконки для контраста
            md_bg_color=self.theme.get('run_btn_bg', (0.596, 0.486, 1.0, 1)),
            on_release=self._send
        )

        input_box.add_widget(self.text_input)
        input_box.add_widget(send_btn)
        content_box.add_widget(input_box)

        self.add_widget(content_box)

        # Загружаем историю при открытии
        Clock.schedule_once(lambda dt: self._load_history(), 0.2)

    def _load_history(self):
        """Загружает и отображает историю чата"""
        with self.agent._lock:
            history = self.agent.history.copy()

        # Если история пуста, показываем приветствие
        if not history:
            self._add_bot(
                "Привет! Я ИИ-тьютор по Python. Задавай вопросы о коде, ошибках или уроках!" if self.locale == "ru"
                else "Hi! I'm an AI Python tutor. Ask about code, errors, or lessons!"
            )
            return

        # Отображаем историю
        for msg in history:
            if msg["role"] == "user":
                self._add_user(msg["content"])
            elif msg["role"] == "assistant":
                self._add_bot(msg["content"])

        self._scroll_to_bottom()
    
    def _update_theme(self):
        """Получает текущую тему динамически"""
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
        self._update_theme()  # Обновляем тему перед добавлением
        
        card = MDCard(
            size_hint_y=None,
            padding=dp(10),
            radius=[12],
            pos_hint={"right": 1},
            md_bg_color=self.theme['widget_bg'],  # Фон карточки из темы
        )
        
        # Используем обычный Label с динамическим text_size
        label = Label(
            text=text,
            size_hint_y=None,
            valign='top',
            halign='right',
            text_size=(None, None),  # Сначала без ограничений
            color=self.theme['text_color'],
            font_size=dp(14)
        )
        
        card.add_widget(label)
        self.messages_box.add_widget(card)
        
        def update_layout(dt):
            # Сначала устанавливаем text_size для автопереноса
            if card.width > 0:
                label.text_size = (card.width - dp(24), None)
                
                # Ждем пересчета texture_size с новым text_size
                def update_height(dt2):
                    if label.texture_size:
                        label.height = label.texture_size[1]
                        card.height = label.height + dp(20)
                
                Clock.schedule_once(update_height, 0.05)
            else:
                # Если ширина еще не известна, используем фиксированную ширину
                label.text_size = (dp(350), None)
                
                def update_height_fallback(dt2):
                    if label.texture_size:
                        label.height = label.texture_size[1]
                        card.height = label.height + dp(20)
                
                Clock.schedule_once(update_height_fallback, 0.05)
        
        Clock.schedule_once(update_layout, 0.1)
        self._scroll_to_bottom()
    
    def _add_bot(self, text, is_streaming=False):
        self._update_theme()  # Обновляем тему перед добавлением

        if is_streaming and self._current_bot_card:
            # Обновляем существующую карточку при streaming
            self._current_bot_label.set_text(text)
            self._update_bot_height()
            return

        card = MDCard(
            size_hint_y=None,
            padding=dp(10),
            radius=[12],
            md_bg_color=self.theme['widget_bg'],  # Фон карточки из темы
        )

        # Используем MarkdownLabel для поддержки кодовых блоков с копированием
        label = MarkdownLabel(
            text=text,
            font_size=dp(14)
        )

        card.add_widget(label)
        self.messages_box.add_widget(card)

        # Сохраняем ссылки для streaming
        self._current_bot_card = card
        self._current_bot_label = label

        # Многократное обновление высоты карточки для корректного рендеринга
        def update_height(dt):
            if label.height > 0:
                card.height = label.height + dp(20)
            else:
                # Если высота еще не рассчитана, используем минимальную
                card.height = dp(60)
            self._scroll_to_bottom()

        # Обновляем высоту несколько раз с разной задержкой
        Clock.schedule_once(update_height, 0.05)
        Clock.schedule_once(update_height, 0.1)
        Clock.schedule_once(update_height, 0.2)
        Clock.schedule_once(update_height, 0.3)

    def _update_bot_height(self):
        """Обновляет высоту текущей карточки бота"""
        if self._current_bot_card and self._current_bot_label:
            def update_height(dt):
                if self._current_bot_label and self._current_bot_label.height > 0:
                    self._current_bot_card.height = self._current_bot_label.height + dp(20)
                self._scroll_to_bottom()
            Clock.schedule_once(update_height, 0.05)
    
    def _scroll_to_bottom(self):
        Clock.schedule_once(lambda dt: setattr(self.scroll, 'scroll_y', 0), 0.1)
    
    def _add_thinking(self):
        # Убираем индикатор "Думаю..." - не нужен
        return None
    
    def _send(self, *args):
        text = self.text_input.text.strip()
        if not text:
            return
        self.text_input.text = ""
        self._add_user(text)

        # Блокируем ввод и включаем кнопку остановки
        self._is_generating = True
        self.text_input.disabled = True
        self.stop_btn.disabled = False

        # Создаем пустую карточку для streaming
        self._add_bot("", is_streaming=True)

        def stream_callback(chunk):
            """Callback для потоковой передачи"""
            if not self._is_generating:
                return
            # Получаем текущий текст и добавляем новый кусочек
            current_text = self._current_bot_label.text if self._current_bot_label else ""
            new_text = current_text + chunk
            self._add_bot(new_text, is_streaming=True)

        def ok(answer):
            self._is_generating = False
            self.text_input.disabled = False
            self.stop_btn.disabled = True
            # Финальное обновление
            self._add_bot(answer, is_streaming=True)
            self._current_bot_card = None
            self._current_bot_label = None

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
        """Останавливает генерацию"""
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
            self._add_bot("Чат очищен." if self.locale == "ru" else "Chat cleared.")
            return
        
        context = self.get_context()
        thinking = self._add_thinking()
        
        def ok(answer):
            self._add_bot(answer)
        
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
                self.messages_box.remove_widget(thinking)
                self._add_bot("Нет кода для проверки." if self.locale == "ru" else "No code to check.")
                return
            self.agent.review_code(context, locale=self.locale, on_success=ok, on_error=err)

def open_ai_chat(agent, locale="ru", get_context_callback=None):
    print(f"[AI Chat] Opening AI chat screen...")
    
    from kivy.uix.modalview import ModalView
    
    # Создаем экран чата
    chat_screen = AiChatScreen(agent, locale=locale, get_context_callback=get_context_callback)
    chat_screen.name = "ai_chat_screen"
    
    # Получаем тему для background_color modal
    try:
        if ThemeManager:
            theme = ThemeManager.get_theme()
            bg_color = theme.get('window_bg', (0.15, 0.15, 0.2, 0.95))
        else:
            bg_color = (0.15, 0.15, 0.2, 0.95)
    except:
        bg_color = (0.15, 0.15, 0.2, 0.95)
    
    # Создаем ModalView (подобие popup)
    modal = ModalView(
        size_hint=(0.95, 0.85),
        background_color=bg_color,
    )
    
    # Передаем ссылку на modal в chat_screen
    chat_screen.modal = modal
    
    modal.add_widget(chat_screen)
    
    print(f"[AI Chat] Modal created, opening...")
    modal.open()
    print(f"[AI Chat] Modal opened")
    
    return modal

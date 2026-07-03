"""
Enhanced autocomplete popup - appears above symbol bar without shifting it
Поддержка Google Keyboard и других IME
"""
import re
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.metrics import dp

from utils.screen_utils import get_screen_category
from ide_core.themes import ThemeManager


class AutoCompletePopup:
    """Всплывающее окно автодополнения - появляется над панелью символов"""

    def __init__(self):
        self.popup = None
        self.code_input = None
        self._words_cache = []
        self._filtered_words = []
        self._current_word = ""
        self._suggestion_buttons = []
        self._search_box = None
        self._suggestions_grid = None
        self._popup_visible = False

        # Кеш для быстрого поиска
        self._base_words = self._build_word_list()
        self._last_code_hash = None
        self._context_words = set()

    def _build_word_list(self):
        """Строит базовый список ключевых слов Python"""
        return sorted(set([
            # Ключевые слова Python
            'False', 'None', 'True', 'and', 'as', 'assert', 'async', 'await',
            'break', 'class', 'continue', 'def', 'del', 'elif', 'else',
            'except', 'finally', 'for', 'from', 'global', 'if', 'import',
            'in', 'is', 'lambda', 'nonlocal', 'not', 'or', 'pass', 'raise',
            'return', 'try', 'while', 'with', 'yield',
            # Встроенные функции
            'print', 'input', 'len', 'range', 'int', 'str', 'float',
            'list', 'dict', 'set', 'tuple', 'open', 'type', 'abs',
            'max', 'min', 'sum', 'sorted', 'enumerate', 'zip',
            # Методы списков
            'append', 'extend', 'insert', 'remove', 'pop',
            # Методы словарей
            'keys', 'values', 'items', 'get', 'update',
            # Методы строк
            'split', 'join', 'replace', 'strip', 'lower', 'upper',
            'startswith', 'endswith',
            # Специальные
            'self', '__init__', '__name__', '__main__',
            # Google Keyboard и другие IME поддерживают эти методы
            'help', 'dir', 'vars', 'globals', 'locals', 'callable'
        ]))

    def _update_context_words(self):
        """Извлекает слова из текущего кода для контекстного автодополнения"""
        if not self.code_input:
            return

        text = self.code_input.text
        code_hash = hash(text)

        # Используем кеш, чтобы не пересканивать постоянно
        if code_hash == self._last_code_hash:
            return

        self._last_code_hash = code_hash

        # Извлекаем идентификаторы из кода (последние 1000 символов для перформанса)
        recent_text = text[-1000:] if len(text) > 1000 else text
        words = re.findall(r'[a-zA-Z_]\w+', recent_text)
        self._context_words = set(words)

    def _get_suggestions(self, partial_word):
        """Получает подсказки для частичного слова"""
        if not partial_word or len(partial_word) < 1:
            return []

        self._update_context_words()

        # Объединяем базовые слова и контекстные слова
        all_words = set(self._base_words) | self._context_words

        # Ищем совпадения начиная с partial_word
        word_lower = partial_word.lower()
        matches = sorted([
            w for w in all_words
            if w.lower().startswith(word_lower)
        ])

        # Приоритизируем: сначала точные совпадения, потом с большей буквы, потом остальные
        exact = [w for w in matches if w == partial_word]
        capitalized = [w for w in matches if w != partial_word and w[0].isupper()]
        lowercase = [w for w in matches if w != partial_word and w[0].islower()]

        return exact + capitalized + lowercase[:20]

    def show(self, current_word, code_input):
        """Показывает всплывающее окно автодополнения"""
        if not code_input:
            return

        self.code_input = code_input
        self._current_word = current_word

        # Получаем подсказки
        suggestions = self._get_suggestions(current_word)

        if not suggestions or len(current_word) < 1:
            self.hide()
            return

        # Создаём UI для всплывающего окна
        self._create_popup_ui(suggestions, current_word)

        # Позиционируем окно над текущей позицией курсора
        if not self.popup.parent:
            self.popup.open()
            self._popup_visible = True

    def _create_popup_ui(self, suggestions, current_word):
        """Создаёт UI всплывающего окна"""
        theme = ThemeManager.get_theme()
        category = get_screen_category()

        # Адаптивные размеры
        if category == 'tablet':
            popup_width = 0.6
            popup_height = 0.5
            btn_height = dp(32)
            font_size = dp(14)
            search_height = dp(32)
        elif category == 'large_phone':
            popup_width = 0.75
            popup_height = 0.55
            btn_height = dp(28)
            font_size = dp(12)
            search_height = dp(28)
        else:
            popup_width = 0.85
            popup_height = 0.6
            btn_height = dp(24)
            font_size = dp(11)
            search_height = dp(24)

        # Главный контейнер
        main_layout = BoxLayout(orientation='vertical', spacing=dp(4), padding=dp(4))

        # Поле поиска для фильтрации
        self._search_box = TextInput(
            hint_text='Filter...',
            multiline=False,
            font_size=font_size,
            background_color=theme['input_bg'],
            foreground_color=theme['input_text'],
            cursor_color=theme.get('input_cursor', (1, 1, 1, 1)),
            hint_text_color=theme.get('hint_text', (0.7, 0.7, 0.7, 1)),
            size_hint_y=None,
            height=search_height,
            padding=[dp(4), dp(2)]
        )
        self._search_box.bind(text=self._on_search_text_changed)
        main_layout.add_widget(self._search_box)

        # Прокручиваемая область с подсказками
        scroll = ScrollView(
            size_hint=(1, 1),
            do_scroll_x=False,
            do_scroll_y=True,
            bar_width=dp(3),
            bar_color=theme.get('scroll_bar_color', (0.4, 0.4, 0.4, 0.7))
        )

        # Сетка с кнопками
        self._suggestions_grid = GridLayout(
            cols=2,
            spacing=dp(3),
            size_hint_x=1,
            size_hint_y=None,
            padding=dp(2)
        )
        self._suggestions_grid.bind(minimum_height=self._suggestions_grid.setter('height'))

        scroll.add_widget(self._suggestions_grid)
        main_layout.add_widget(scroll)

        # Заполняем сетку подсказками
        self._populate_suggestions(suggestions)

        # Закрытие окна
        close_btn = Button(
            text='Close',
            size_hint_y=None,
            height=btn_height,
            font_size=font_size,
            background_color=theme['widget_bg'],
            background_normal='',
            background_down='',
            color=theme['text_color']
        )
        close_btn.bind(on_release=self._close_popup)
        main_layout.add_widget(close_btn)

        # Создаём или обновляем popup
        if self.popup:
            self.popup.dismiss()

        self.popup = Popup(
            title=f'Autocomplete: {current_word}',
            title_color=theme.get('popup_title', (1, 1, 1, 1)),
            title_size=font_size,
            background_color=theme.get('popup_bg', theme['widget_bg']),
            background='',
            content=main_layout,
            size_hint=(popup_width, popup_height),
            auto_dismiss=True
        )

    def _populate_suggestions(self, suggestions):
        """Заполняет сетку подсказками"""
        theme = ThemeManager.get_theme()
        category = get_screen_category()

        if category == 'tablet':
            btn_height = dp(32)
            font_size = dp(14)
        elif category == 'large_phone':
            btn_height = dp(28)
            font_size = dp(12)
        else:
            btn_height = dp(24)
            font_size = dp(11)

        self._suggestions_grid.clear_widgets()
        self._suggestion_buttons = []

        for word in suggestions[:20]:  # Максимум 20 подсказок
            btn = Button(
                text=word,
                size_hint_y=None,
                height=btn_height,
                font_size=font_size,
                font_name='SourceBold',
                background_color=theme['input_bg'],
                background_normal='',
                background_down='',
                color=theme['input_text']
            )
            btn.word = word
            btn.bind(on_release=self._on_suggestion_selected)
            self._suggestions_grid.add_widget(btn)
            self._suggestion_buttons.append(btn)

    def _on_search_text_changed(self, instance, value):
        """Обновляет подсказки при изменении текста поиска"""
        # Ищем подсказки с учётом фильтра поиска
        search_term = value.lower() if value else ''
        all_suggestions = self._get_suggestions(self._current_word)

        if search_term:
            filtered = [w for w in all_suggestions if search_term in w.lower()]
        else:
            filtered = all_suggestions

        self._populate_suggestions(filtered)

    def _on_suggestion_selected(self, instance):
        """Вставляет выбранное слово"""
        if not self.code_input:
            return

        word = instance.word
        text = self.code_input.text
        cursor_pos = self.code_input.cursor_index()

        # Находим начало текущего слова
        start = cursor_pos
        while start > 0 and (text[start - 1].isalnum() or text[start - 1] == '_'):
            start -= 1

        # Заменяем слово
        new_text = text[:start] + word + text[cursor_pos:]
        self.code_input.text = new_text

        # Устанавливаем курсор после вставленного слова
        new_pos = start + len(word)
        try:
            self.code_input.cursor = self.code_input.get_cursor_from_index(new_pos)
        except:
            pass

        self.hide()
        self.code_input.focus = True

    def _close_popup(self, instance=None):
        """Закрывает всплывающее окно"""
        self.hide()

    def hide(self):
        """Скрывает всплывающее окно"""
        if self.popup and self.popup.parent:
            self.popup.dismiss()
        self._popup_visible = False

    def reset(self):
        """Сбрасывает кеш"""
        self._base_words = self._build_word_list()
        self._context_words.clear()
        self._last_code_hash = None



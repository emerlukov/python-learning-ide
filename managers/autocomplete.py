"""
Autocomplete widget for code editor - Оптимизированная версия
"""
import re
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivy.metrics import dp

from utils.screen_utils import get_screen_category
from ide_core.themes import ThemeManager


class AutoCompleteWidget(BoxLayout):
    """Панель автодополнения - оптимизированная версия"""

    # Максимальное количество подсказок
    MAX_SUGGESTIONS = 8
    # Минимальная длина слова для показа подсказок
    MIN_WORD_LEN = 2
    # Максимальная длина слова для показа подсказок
    MAX_WORD_LEN = 15
    # Задержка обновления словаря (секунды)
    UPDATE_DELAY = 0.5
    # Количество строк контекста для сканирования
    CONTEXT_LINES = 5

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.size_hint_y = None
        self.height = 0
        self.code_input = None
        self.visible = False

        # Кешированные данные
        self._base_words = None
        self._all_words_cache = []
        self._last_text_hash = 0
        self._update_timer = None

        # UI компоненты
        self.suggestions_box = BoxLayout(
            orientation='horizontal',
            size_hint_x=None,
            height=dp(23),
            spacing=dp(2),
            padding=[dp(3), dp(3)]
        )
        self.suggestions_box.bind(minimum_width=self.suggestions_box.setter('width'))

        self.scroll = ScrollView(
            size_hint=(1, 1),
            do_scroll_x=True,
            do_scroll_y=False,
            bar_width=dp(2)
        )
        self.scroll.add_widget(self.suggestions_box)
        self.add_widget(self.scroll)

    def _get_base_words(self):
        """Возвращает базовый список ключевых слов Python (кешированный)"""
        if self._base_words is None:
            self._base_words = self._build_word_list()
        return self._base_words

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
            'self', '__init__', '__name__', '__main__'
        ]))

    def update_words_from_code(self):
        """Запускает отложенное обновление словаря из кода"""
        if not self.code_input:
            return

        # Отменяем предыдущий таймер
        if self._update_timer:
            self._update_timer.cancel()

        # Планируем обновление с задержкой
        self._update_timer = Clock.schedule_once(self._do_update_words, self.UPDATE_DELAY)

    def _do_update_words(self, dt):
        """Выполняет обновление словаря из кода (вызывается с задержкой)"""
        if not self.code_input:
            return

        text = self.code_input.text
        if not text:
            self._all_words_cache = self._get_base_words()
            return

        # Проверяем, изменился ли текст (через хеш)
        text_hash = hash(text)
        if text_hash == self._last_text_hash:
            return
        self._last_text_hash = text_hash

        # Берем только контекст (текущая строка + предыдущие)
        cursor_pos = self.code_input.cursor_index()
        text_before = text[:cursor_pos]
        lines = text_before.split('\n')

        # Берем последние N строк
        context_lines = lines[-self.CONTEXT_LINES:] if len(lines) > self.CONTEXT_LINES else lines
        context = '\n'.join(context_lines)

        # Сканируем только контекст
        code_words = set(re.findall(r'[a-zA-Z_]\w+', context))

        # Объединяем с базовыми словами
        base_words = self._get_base_words()
        combined = set(base_words) | code_words

        # Ограничиваем размер кеша
        if len(combined) > 500:
            # Оставляем базовые слова и последние использованные
            combined = set(base_words) | set(list(code_words)[:200])

        self._all_words_cache = sorted(combined)

    def show_suggestions(self, current_word):
        """Показывает подсказки для текущего слова"""
        self.suggestions_box.clear_widgets()

        # Проверяем, нужно ли показывать подсказки
        if not current_word:
            self.height = 0
            self.visible = False
            return

        word_len = len(current_word)
        if word_len < self.MIN_WORD_LEN or word_len > self.MAX_WORD_LEN:
            self.height = 0
            self.visible = False
            return

        # Обновляем словарь из кода (с debounce)
        if self.code_input and self.code_input.text.strip():
            self.update_words_from_code()

        # Ищем подходящие слова
        word_lower = current_word.lower()
        matches = [w for w in self._all_words_cache if w.lower().startswith(word_lower)]
        matches = matches[:self.MAX_SUGGESTIONS]

        if not matches:
            self.height = 0
            self.visible = False
            return

        # Адаптивные размеры для разных экранов
        theme = ThemeManager.get_theme()
        category = get_screen_category()

        if category == 'tablet':
            btn_height = dp(26)
            btn_font_size = dp(16)
            char_width = dp(9)
        elif category == 'large_phone':
            btn_height = dp(22)
            btn_font_size = dp(14)
            char_width = dp(8)
        else:
            btn_height = dp(18)
            btn_font_size = dp(13)
            char_width = dp(7)

        # Создаём кнопки для каждой подсказки
        for word in matches:
            btn = Button(
                text=word,
                size_hint_x=None,
                width=len(word) * char_width + dp(10),
                height=btn_height,
                font_size=btn_font_size,
                font_name='SourceBold',
                background_color=theme['widget_bg'],
                background_normal='',
                background_down='',
                color=theme['text_color']
            )
            btn.word = word
            btn.bind(on_release=self._on_suggestion_click)
            self.suggestions_box.add_widget(btn)

        self.height = dp(23)
        self.visible = True

    def _on_suggestion_click(self, instance):
        """Обрабатывает выбор подсказки"""
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

    def hide(self):
        """Скрывает панель автодополнения"""
        self.height = 0
        self.visible = False
        self.suggestions_box.clear_widgets()

        # Отменяем запланированное обновление
        if self._update_timer:
            self._update_timer.cancel()
            self._update_timer = None

    def reset_cache(self):
        """Сбрасывает кеш (вызывать при смене языка или теме)"""
        self._base_words = None
        self._all_words_cache = []
        self._last_text_hash = 0
        if self._update_timer:
            self._update_timer.cancel()
            self._update_timer = None
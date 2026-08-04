"""
Autocomplete widget for code editor - Оптимизированная версия
"""
import re
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.clock import Clock
from kivy.metrics import dp

from utils.screen_utils import get_screen_category
from ide_core.themes import ThemeManager


class AutoCompleteWidget(BoxLayout):
    """Панель автодополнения - оптимизированная версия

    Улучшения:
    - Не сдвигает панель символов (использует overlay позиционирование)
    - Более быстрая работа
    - Поддержка Google Keyboard
    - Адаптивный UI
    """

    # Максимальное количество подсказок
    MAX_SUGGESTIONS = 10
    # Минимальная длина слова для показа подсказок
    MIN_WORD_LEN = 1
    # Максимальная длина слова для показа подсказок
    MAX_WORD_LEN = 20
    # Задержка обновления словаря (секунды)
    UPDATE_DELAY = 0.3
    # Количество строк контекста для сканирования
    CONTEXT_LINES = 10

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
        self._filter_text = ''
        self._filter_input = None
        self._showing_full_list = False

        # UI компоненты
        self.filter_box = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=0,
            spacing=dp(2),
            padding=[dp(3), dp(3)]
        )
        self.filter_box.opacity = 0
        
        self._filter_input = TextInput(
            hint_text='Filter...',
            multiline=False,
            size_hint=(1, 1),
            font_size=dp(12),
            font_name='SourceBold',
            padding=[dp(5), dp(5), dp(5), dp(5)],
            background_color=ThemeManager.get_theme()['input_bg'],
            foreground_color=ThemeManager.get_theme()['input_text'],
            cursor_color=ThemeManager.get_theme()['input_cursor'],
            hint_text_color=ThemeManager.get_theme()['hint_text']
        )
        self._filter_input.bind(text=self._on_filter_changed)
        self.filter_box.add_widget(self._filter_input)
        
        self.suggestions_box = BoxLayout(
            orientation='horizontal',
            size_hint_x=None,
            height=dp(26),
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
        
        # Контейнер для фильтра и подсказок
        self.main_container = BoxLayout(orientation='vertical', size_hint=(1, 1))
        self.main_container.add_widget(self.filter_box)
        self.main_container.add_widget(self.scroll)
        self.add_widget(self.main_container)
        
        # Регистрируем в ThemeManager
        ThemeManager.register(self)

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
            'map', 'filter', 'reduce', 'lambda', 'all', 'any',
            'bool', 'complex', 'divmod', 'eval', 'exec', 'hash', 'id',
            'isinstance', 'issubclass', 'iter', 'next', 'object', 'ord',
            'pow', 'repr', 'round', 'slice', 'super', 'bin', 'hex', 'oct',
            'chr', 'bytes', 'bytearray', 'memoryview', 'frozenset',
            # Методы списков
            'append', 'extend', 'insert', 'remove', 'pop', 'clear', 'index', 'count', 'sort', 'reverse', 'copy',
            # Методы словарей
            'keys', 'values', 'items', 'get', 'update', 'pop', 'clear', 'copy', 'fromkeys', 'setdefault',
            # Методы строк
            'split', 'join', 'replace', 'strip', 'lower', 'upper',
            'startswith', 'endswith', 'find', 'format', 'capitalize', 'swapcase',
            'title', 'lstrip', 'rstrip', 'ljust', 'rjust', 'center',
            'isalpha', 'isdigit', 'isalnum', 'isspace', 'islower', 'isupper', 'istitle',
            'rfind', 'rindex', 'expandtabs', 'partition', 'rpartition', 'splitlines', 'zfill',
            # Методы множеств
            'add', 'remove', 'discard', 'pop', 'clear', 'union', 'intersection', 'difference',
            'symmetric_difference', 'issubset', 'issuperset', 'isdisjoint',
            # Специальные (для Google Keyboard и IME)
            'self', '__init__', '__name__', '__main__',
            'help', 'dir', 'vars', 'globals', 'locals', 'callable', 'hasattr', 'getattr', 'setattr', 'delattr'
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

    def _on_filter_changed(self, instance, value):
        """Обрабатывает изменение текста фильтра"""
        self._filter_text = value
        if self._showing_full_list:
            self._show_full_list_internal()
        elif self.visible:
            # Если панель видна, обновляем подсказки с учётом фильтра
            self._refresh_suggestions()

    def _refresh_suggestions(self):
        """Обновляет подсказки с учётом текущего фильтра"""
        if not self.visible:
            return
        
        # Получаем текущее слово из редактора
        if not self.code_input:
            return
        
        text = self.code_input.text
        cursor_pos = self.code_input.cursor_index()
        before_cursor = text[:cursor_pos]
        match = re.search(r'([a-zA-Z_]\w*)$', before_cursor)
        current_word = match.group(1) if match else ""
        
        self._render_suggestions(current_word)

    def show_suggestions(self, current_word):
        """Показывает подсказки для текущего слова"""
        self.suggestions_box.clear_widgets()
        self._showing_full_list = False
        self._filter_text = ''
        if self._filter_input:
            self._filter_input.text = ''

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

        self._render_suggestions(current_word)

    def _render_suggestions(self, current_word):
        """Отрисовывает подсказки для текущего слова"""
        self.suggestions_box.clear_widgets()
        
        # Ищем подходящие слова
        word_lower = current_word.lower()
        matches = [w for w in self._all_words_cache if w.lower().startswith(word_lower)]
        
        # Применяем фильтр, если есть
        if self._filter_text:
            filter_lower = self._filter_text.lower()
            matches = [w for w in matches if filter_lower in w.lower()]

        # Приоритизируем точные совпадения и с большой буквы
        exact = [w for w in matches if w == current_word]
        capitalized = [w for w in matches if w != current_word and w and w[0].isupper()]
        lowercase = [w for w in matches if w != current_word and w and w[0].islower()]

        matches = exact + capitalized + lowercase[:self.MAX_SUGGESTIONS]

        if not matches:
            self.height = 0
            self.visible = False
            return

        # Адаптивные размеры для разных экранов
        theme = ThemeManager.get_theme()
        category = get_screen_category()

        if category == 'tablet':
            btn_height = dp(28)
            btn_font_size = dp(14)
            char_width = dp(8.5)
            self.suggestions_box.height = dp(28)
        elif category == 'large_phone':
            btn_height = dp(24)
            btn_font_size = dp(12)
            char_width = dp(7.5)
            self.suggestions_box.height = dp(24)
        else:
            btn_height = dp(20)
            btn_font_size = dp(11)
            char_width = dp(6.5)
            self.suggestions_box.height = dp(20)

        # Создаём кнопки для каждой подсказки
        for word in matches[:self.MAX_SUGGESTIONS]:
            btn = Button(
                text=word,
                size_hint_x=None,
                width=max(len(word) * char_width + dp(8), dp(35)),
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

        # Показываем фильтр только при полном списке
        self.filter_box.height = dp(28) if self._showing_full_list else 0
        self.filter_box.opacity = 1 if self._showing_full_list else 0
        self.height = self.filter_box.height + self.suggestions_box.height
        self.visible = True

    def show_full_list(self):
        """Показывает полный список ключевых слов"""
        # Если уже показывается полный список, скрываем его
        if self._showing_full_list and self.visible:
            self.hide()
            return
        
        self._showing_full_list = True
        self._filter_text = ''
        if self._filter_input:
            self._filter_input.text = ''
        
        # Обновляем словарь из кода
        if self.code_input and self.code_input.text.strip():
            self.update_words_from_code()
        
        self._show_full_list_internal()

    def _show_full_list_internal(self):
        """Внутренний метод для показа полного списка"""
        self.suggestions_box.clear_widgets()
        
        # Получаем все слова
        all_words = self._all_words_cache
        
        # Применяем фильтр, если есть
        if self._filter_text:
            filter_lower = self._filter_text.lower()
            all_words = [w for w in all_words if filter_lower in w.lower()]
        
        # Ограничиваем количество
        all_words = all_words[:50]
        
        if not all_words:
            self.height = 0
            self.visible = False
            return
        
        # Адаптивные размеры
        theme = ThemeManager.get_theme()
        category = get_screen_category()

        if category == 'tablet':
            btn_height = dp(28)
            btn_font_size = dp(14)
            char_width = dp(8.5)
            self.suggestions_box.height = dp(28)
        elif category == 'large_phone':
            btn_height = dp(24)
            btn_font_size = dp(12)
            char_width = dp(7.5)
            self.suggestions_box.height = dp(24)
        else:
            btn_height = dp(20)
            btn_font_size = dp(11)
            char_width = dp(6.5)
            self.suggestions_box.height = dp(20)
        
        # Создаём кнопки
        for word in all_words:
            btn = Button(
                text=word,
                size_hint_x=None,
                width=max(len(word) * char_width + dp(8), dp(35)),
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
        
        # Показываем фильтр
        self.filter_box.height = dp(28)
        self.filter_box.opacity = 1
        self.height = self.filter_box.height + self.suggestions_box.height
        self.visible = True
        
        # Фокус на фильтр
        if self._filter_input:
            self._filter_input.focus = True

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
        self._showing_full_list = False
        self._filter_text = ''
        if self._filter_input:
            self._filter_input.text = ''
            self._filter_input.focus = False
        self.suggestions_box.clear_widgets()
        
        # Скрываем поле фильтра
        self.filter_box.height = 0
        self.filter_box.opacity = 0

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

    def apply_theme(self, theme):
        """Применяет тему к виджету"""
        if self._filter_input:
            self._filter_input.background_color = theme['input_bg']
            self._filter_input.foreground_color = theme['input_text']
            self._filter_input.cursor_color = theme['input_cursor']
            self._filter_input.hint_text_color = theme['hint_text']
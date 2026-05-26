"""
Autocomplete widget for code editor
"""
import re
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivy.metrics import dp

from utils.screen_utils import get_screen_category, adaptive_dp, adaptive_sp
from core.themes import ThemeManager

class AutoCompleteWidget(BoxLayout):
    """Панель автодополнения"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.size_hint_y = None
        self.height = 0
        self.code_input = None
        self.visible = False
        self.all_words = self._build_word_list()
        self.suggestions_box = BoxLayout(orientation='horizontal', size_hint_x=None, height=dp(23), spacing=dp(2),
                                         padding=[dp(3), dp(3)])
        self.suggestions_box.bind(minimum_width=self.suggestions_box.setter('width'))
        self.scroll = ScrollView(size_hint=(1, 1), do_scroll_x=True, do_scroll_y=False, bar_width=dp(2))
        self.scroll.add_widget(self.suggestions_box)
        self.add_widget(self.scroll)

    def _build_word_list(self):
        words = ['False', 'None', 'True', 'and', 'as', 'assert', 'async', 'await', 'break', 'class', 'continue', 'def',
                 'del', 'elif', 'else', 'except', 'finally', 'for', 'from', 'global', 'if', 'import', 'in', 'is',
                 'lambda', 'nonlocal', 'not', 'or', 'pass', 'raise', 'return', 'try', 'while', 'with', 'yield', 'print',
                 'input', 'len', 'range', 'int', 'str', 'float', 'list', 'dict', 'set', 'tuple', 'open', 'type', 'abs',
                 'max', 'min', 'sum', 'sorted', 'enumerate', 'zip', 'append', 'extend', 'insert', 'remove', 'pop',
                 'keys', 'values', 'items', 'get', 'update', 'split', 'join', 'replace', 'strip', 'lower', 'upper',
                 'startswith', 'endswith', 'self', '__init__', '__name__', '__main__']
        return sorted(set(words))

    def update_words_from_code(self):
        if not self.code_input:
            return
        text = self.code_input.text
        code_words = set(re.findall(r'[a-zA-Z_]\w+', text))
        self.all_words = sorted(set(self._build_word_list() + list(code_words)))

    def show_suggestions(self, current_word):
        self.suggestions_box.clear_widgets()
        if self.code_input and self.code_input.text.strip():
            self.update_words_from_code()
        if not current_word or len(current_word) < 2:
            self.height = 0
            self.visible = False
            return
        word_lower = current_word.lower()
        starts_with = [w for w in self.all_words if w.lower().startswith(word_lower)]
        contains = [w for w in self.all_words if word_lower in w.lower() and not w.lower().startswith(word_lower)]
        matches = starts_with + contains
        matches = matches[:8]
        if not matches:
            self.height = 0
            self.visible = False
            return
        theme = ThemeManager.get_theme()
        for word in matches:
            # Адаптивные размеры для автодополнения
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

            btn = Button(text=word, size_hint_x=None, width=len(word) * char_width + dp(10), height=btn_height,
                         font_size=btn_font_size, font_name='SourceBold', background_color=theme['widget_bg'],
                         background_normal='', background_down='', color=theme['text_color'])
            btn.word = word
            btn.bind(on_release=self._on_suggestion_click)
            self.suggestions_box.add_widget(btn)
        self.height = dp(23)
        self.visible = True

    def _on_suggestion_click(self, instance):
        if not self.code_input:
            return
        word = instance.word
        text = self.code_input.text
        cursor_pos = self.code_input.cursor_index()
        start = cursor_pos
        while start > 0 and (text[start - 1].isalnum() or text[start - 1] == '_'):
            start -= 1
        new_text = text[:start] + word + text[cursor_pos:]
        self.code_input.text = new_text
        new_pos = start + len(word)
        try:
            self.code_input.cursor = self.code_input.get_cursor_from_index(new_pos)
        except:
            pass
        self.hide()
        self.code_input.focus = True

    def hide(self):
        self.height = 0
        self.visible = False
        self.suggestions_box.clear_widgets()
# widgets/markdown_label.py
"""
Markdown Label with monospace font support
"""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.metrics import dp
from kivy.graphics import Color, Rectangle
from kivy.core.window import Window
from kivy.clock import Clock
import re

from ide_core.themes import ThemeManager


def _force_defocus(widget):
    """
    Рекурсивно снимает фокус и выделение со всех TextInput.
    На Android дополнительно скрывает клавиатуру и убирает handle-маркеры.
    """
    if isinstance(widget, TextInput):
        if widget.focus:
            widget.focus = False
        # cancel_selection сбрасывает selection_from/to и убирает маркеры
        widget.cancel_selection()
        # На Android явно убираем handle через внутренний _handle
        try:
            if hasattr(widget, '_handle_left'):
                widget._handle_left.opacity = 0
            if hasattr(widget, '_handle_right'):
                widget._handle_right.opacity = 0
            if hasattr(widget, '_handle_middle'):
                widget._handle_middle.opacity = 0
        except Exception:
            pass
    for child in widget.children:
        _force_defocus(child)


class CodeScrollView(ScrollView):
    """
    Горизонтальный ScrollView для блоков кода внутри MarkdownLabel.
    - Горизонтальный свайп → скролит код.
    - Вертикальный свайп → пропускает наверх (листает вкладку).
    - Тап вне → снимает выделение.
    Порог определения направления — dp(6).
    """
    THRESHOLD = dp(6)

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            _force_defocus(self)
            return False
        touch.ud['csv_ox'] = touch.x
        touch.ud['csv_oy'] = touch.y
        touch.ud['csv_dir'] = None   # 'h', 'v', или None (не определено)
        touch.grab(self)
        return True

    def on_touch_move(self, touch):
        if touch.grab_current is not self:
            return False
        dx = touch.x - touch.ud['csv_ox']
        dy = touch.y - touch.ud['csv_oy']
        direction = touch.ud['csv_dir']

        if direction is None:
            if abs(dx) > self.THRESHOLD or abs(dy) > self.THRESHOLD:
                touch.ud['csv_dir'] = 'h' if abs(dx) >= abs(dy) else 'v'
            return True  # ждём определения направления

        if direction == 'v':
            # Вертикальный — отпускаем, пусть внешний ScrollView листает
            touch.ungrab(self)
            return False

        # Горизонтальный — скролим сами
        if self.do_scroll_x and self.content_width > self.width:
            sw = self.content_width - self.width
            if sw > 0:
                self.scroll_x = max(0.0, min(1.0,
                    self.scroll_x - dx / sw))
                touch.ud['csv_ox'] = touch.x
        return True

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            # Короткий тап — снимаем выделение
            if touch.ud.get('csv_dir') is None:
                _force_defocus(self)
            return True
        if not self.collide_point(*touch.pos):
            return False
        return super().on_touch_up(touch)

    @property
    def content_width(self):
        if self.children:
            return self.children[0].width
        return self.width


class MarkdownLabel(BoxLayout):
    """
    Виджет для отображения Markdown текста.
    BoxLayout с size_hint_y=None — высота по содержимому.
    Не перехватывает вертикальный скролл родителя.
    """

    def __init__(self, text="", font_size=dp(13), **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.spacing = dp(4)
        # left, top, right, bottom — правый отступ dp(8) чтобы текст не обрезался
        self.padding = [dp(4), dp(8), dp(8), dp(8)]
        self.font_size = font_size

        self.size_hint_y = None
        self.bind(minimum_height=self.setter('height'))

        self._update_background()
        self.bind(size=self._update_background, pos=self._update_background)

        if text:
            self.set_text(text)

    def _update_background(self, *args):
        theme = ThemeManager.get_theme()
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*theme.get('editor_bg', (0.188, 0.204, 0.251, 1)))
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg_rect, size=self._update_bg_rect)

    def _update_bg_rect(self, instance, value):
        if hasattr(self, 'bg_rect'):
            self.bg_rect.pos = instance.pos
            self.bg_rect.size = instance.size

    def set_text(self, text):
        self.clear_widgets()

        if not text or not text.strip():
            self.add_widget(Label(size_hint_y=None, height=dp(20)))
            return

        lines = text.split('\n')
        i = 0
        in_code_block = False
        code_lines = []

        while i < len(lines):
            line = lines[i]

            if line.strip().startswith('```'):
                if not in_code_block:
                    in_code_block = True
                    code_lines = []
                else:
                    in_code_block = False
                    self._add_code_block('\n'.join(code_lines))
                i += 1
                continue

            if in_code_block:
                code_lines.append(line)
                i += 1
                continue

            if not line.strip():
                self._add_spacer(dp(4))
                i += 1
                continue

            stripped = line.strip()

            if stripped.startswith('### '):
                self._add_heading(stripped[4:], 3)
            elif stripped.startswith('## '):
                self._add_heading(stripped[3:], 2)
            elif stripped.startswith('# '):
                self._add_heading(stripped[2:], 1)
            elif stripped.startswith('>'):
                self._add_quote(stripped[1:].strip())
            elif stripped.startswith('- ') or stripped.startswith('* '):
                self._add_list_item(stripped[2:])
            elif stripped in ('---', '___', '***') or (len(stripped) >= 3 and
                    all(c == stripped[0] for c in stripped) and stripped[0] in '-_*'):
                self._add_divider()
            else:
                self._add_paragraph(line)

            i += 1

        Clock.schedule_once(self._update_height, 0.1)

    def _update_height(self, dt=None):
        self.height = self.minimum_height

    # ── label helpers ──────────────────────────────────────────────────

    def _label_kwargs(self, font_size=None, bold=False, color_key='text_color'):
        theme = ThemeManager.get_theme()
        return dict(
            font_size=font_size or self.font_size,
            font_name='JetBrainsMono',
            color=theme.get(color_key, (0.85, 0.88, 0.90, 1)),
            size_hint_y=None,
            halign='left',
            valign='top',
            bold=bold,
        )

    def _bind_label_width(self, label, extra_margin=dp(16)):
        """Привязывает text_size к ширине label минус отступ."""
        def _upd(inst, val):
            inst.text_size = (max(1, val - extra_margin), None)
        label.bind(width=_upd)
        label.bind(texture_size=lambda inst, sz: setattr(inst, 'height', sz[1] + dp(6)))
        # Инициируем сразу если ширина уже известна
        if label.width:
            label.text_size = (max(1, label.width - extra_margin), None)

    def _add_heading(self, text, level):
        sizes = {1: dp(20), 2: dp(17), 3: dp(15)}
        font_size = sizes.get(level, dp(16))
        text = self._strip_inline_markdown(text)
        kw = self._label_kwargs(font_size=font_size, bold=True)
        label = Label(text=text, height=font_size + dp(12), **kw)
        self._bind_label_width(label, dp(16))
        self.add_widget(label)
        self._add_spacer(dp(4))

    def _add_paragraph(self, text):
        text, has_markup = self._convert_to_kivy_markup(text)
        kw = self._label_kwargs()
        label = Label(text=text, markup=has_markup, height=dp(20), **kw)
        self._bind_label_width(label, dp(16))
        self.add_widget(label)

    def _add_list_item(self, text):
        text, has_markup = self._convert_to_kivy_markup(text)
        kw = self._label_kwargs()
        label = Label(text=f'• {text}', markup=has_markup, height=dp(20), **kw)
        self._bind_label_width(label, dp(24))
        self.add_widget(label)

    def _add_quote(self, text):
        theme = ThemeManager.get_theme()
        text, has_markup = self._convert_to_kivy_markup(text)

        row = BoxLayout(orientation='horizontal', size_hint_y=None,
                        spacing=dp(6), padding=[dp(4), dp(2), dp(4), dp(2)])

        bar = Label(text='▌', font_size=self.font_size * 1.4,
                    font_name='JetBrainsMono',
                    color=theme.get('stats_text', (0.6, 0.63, 0.65, 1)),
                    size_hint=(None, None), width=dp(10), height=dp(20))
        row.add_widget(bar)

        kw = self._label_kwargs(color_key='stats_text')
        label = Label(text=text, markup=has_markup, height=dp(20), **kw)
        self._bind_label_width(label, dp(24))
        row.add_widget(label)

        label.bind(height=lambda inst, h: setattr(row, 'height', h + dp(4)))
        row.height = dp(24)
        self.add_widget(row)

    def _add_code_block(self, code):
        theme = ThemeManager.get_theme()

        lines = code.split('\n')
        if lines:
            non_empty = [l for l in lines if l.strip()]
            if non_empty:
                min_indent = min(len(l) - len(l.lstrip()) for l in non_empty)
                if min_indent > 0:
                    lines = [l[min_indent:] if l.strip() else '' for l in lines]
            code = '\n'.join(lines)

        lines_count = len(lines)
        max_line_length = max((len(l) for l in lines), default=0)

        line_height = dp(18)
        code_height = int(max(dp(16) + lines_count * line_height, dp(60)))

        # Используем наш CodeScrollView вместо обычного ScrollView
        code_scroll = CodeScrollView(
            size_hint=(1, None),
            height=code_height,
            do_scroll_x=True,
            do_scroll_y=False,
            bar_width=dp(4),
            bar_color=(0.5, 0.5, 0.5, 0.8),
            bar_inactive_color=(0.3, 0.3, 0.3, 0.5),
        )

        # Ширина контента: не меньше ширины виджета и не меньше длины строк
        def _compute_w():
            return max(self.width - dp(4),
                       max_line_length * dp(7) + dp(24))

        code_input = TextInput(
            text=code,
            readonly=True,
            font_size=dp(12),
            font_name='JetBrainsMono',
            background_color=theme.get('lesson_input_bg', (0.25, 0.30, 0.40, 1)),
            foreground_color=theme.get('lesson_input_text', (0.95, 0.95, 0.95, 1)),
            background_normal='',
            background_active='',
            size_hint=(None, None),
            width=_compute_w(),
            height=code_height,
            padding=(dp(8), dp(8)),
            do_wrap=False,
        )

        code_scroll.add_widget(code_input)
        self.add_widget(code_scroll)
        self._add_spacer(dp(4))

        def _update_code_width(instance, value):
            code_input.width = _compute_w()

        self.bind(width=_update_code_width)

    def _add_divider(self):
        theme = ThemeManager.get_theme()
        label = Label(
            text='─' * 20,
            font_size=dp(10),
            font_name='JetBrainsMono',
            color=theme.get('stats_text', (0.6, 0.63, 0.65, 1)),
            size_hint_y=None,
            height=dp(20),
            halign='center',
        )
        self.add_widget(label)

    def _add_spacer(self, height=dp(8)):
        self.add_widget(Label(size_hint_y=None, height=height))

    def _convert_to_kivy_markup(self, text):
        has_markup = False
        if '**' in text:
            text = re.sub(r'\*\*(.+?)\*\*', r'[b]\1[/b]', text)
            has_markup = True
        if '`' in text:
            text = re.sub(r'`([^`]+)`', r'\1', text)
        return text, has_markup

    def _strip_inline_markdown(self, text):
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
        text = re.sub(r'\*(.+?)\*', r'\1', text)
        text = re.sub(r'`([^`]+)`', r'\1', text)
        return text

    # ── touch: не перехватываем вертикальный скролл ────────────────────

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            # Тап вне — снимаем выделение
            _force_defocus(self)
            return False
        # Передаём вниз сразу — CodeScrollView сам разберётся с направлением
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if not self.collide_point(*touch.pos) and touch.grab_current is None:
            return False
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if not self.collide_point(*touch.pos) and touch.grab_current is None:
            return False
        return super().on_touch_up(touch)

    def apply_theme(self):
        self._update_background()

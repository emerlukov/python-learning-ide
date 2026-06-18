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


class MarkdownLabel(BoxLayout):
    """
    Виджет для отображения Markdown текста.
    Теперь это BoxLayout, а не ScrollView — чтобы не перехватывать касания.
    """

    def __init__(self, text="", font_size=dp(13), **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.spacing = dp(4)
        self.padding = [dp(2), dp(8), dp(10), dp(8)]  # правый отступ dp(10)
        self.font_size = font_size

        # Размер по содержимому
        self.size_hint_y = None
        self.bind(minimum_height=self.setter('height'))

        self._update_background()
        self.bind(size=self._update_background, pos=self._update_background)

        if text:
            self.set_text(text)

    def _update_background(self, *args):
        """Обновляет фон"""
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
        """Устанавливает и отображает Markdown текст"""
        self.clear_widgets()

        if not text or not text.strip():
            empty_label = Label(size_hint_y=None, height=dp(20))
            self.add_widget(empty_label)
            return

        # Парсим Markdown построчно
        lines = text.split('\n')
        i = 0
        in_code_block = False
        code_lines = []

        while i < len(lines):
            line = lines[i]

            # === БЛОК КОДА ===
            if line.strip().startswith('```'):
                if not in_code_block:
                    in_code_block = True
                    code_lines = []
                    i += 1
                    continue
                else:
                    in_code_block = False
                    self._add_code_block('\n'.join(code_lines))
                    i += 1
                    continue

            if in_code_block:
                code_lines.append(line)
                i += 1
                continue

            # Пустая строка
            if not line.strip():
                self._add_spacer(dp(4))
                i += 1
                continue

            stripped = line.strip()

            # === ЗАГОЛОВКИ ===
            if stripped.startswith('# '):
                self._add_heading(line[2:], 1)
                i += 1
                continue
            if stripped.startswith('## '):
                self._add_heading(line[3:], 2)
                i += 1
                continue
            if stripped.startswith('### '):
                self._add_heading(line[4:], 3)
                i += 1
                continue

            # === ЦИТАТЫ ===
            if stripped.startswith('>'):
                self._add_quote(line[1:].strip())
                i += 1
                continue

            # === СПИСКИ ===
            if stripped.startswith('- ') or stripped.startswith('* '):
                self._add_list_item(line[2:])
                i += 1
                continue

            # === ГОРИЗОНТАЛЬНАЯ ЛИНИЯ ===
            if stripped.startswith('---') or stripped.startswith('___') or stripped.startswith('***'):
                self._add_divider()
                i += 1
                continue

            # === ОБЫЧНЫЙ ПАРАГРАФ ===
            self._add_paragraph(line)
            i += 1

        # Обновляем высоту после добавления всех виджетов
        Clock.schedule_once(self._update_height, 0.1)

    def _update_height(self, dt=None):
        """Обновляет высоту под содержимое"""
        self.height = self.minimum_height

    # ===== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ДЛЯ СОЗДАНИЯ ВИДЖЕТОВ =====

    def _add_heading(self, text, level):
        theme = ThemeManager.get_theme()
        sizes = {1: dp(20), 2: dp(17), 3: dp(15)}
        font_size = sizes.get(level, dp(16))
        text = self._strip_inline_markdown(text)

        label = Label(
            text=text,
            font_size=font_size,
            font_name='JetBrainsMono',
            color=theme.get('text_color', (0.85, 0.88, 0.90, 1)),
            size_hint_y=None,
            height=font_size + dp(12),
            halign='left',
            valign='middle',
            text_size=(self.width - dp(30), None),
            bold=True
        )
        label.bind(
            width=lambda inst, val: setattr(inst, 'text_size', (val - dp(30), None)),
            texture_size=lambda inst, sz: setattr(inst, 'height', max(sz[1] + dp(12), font_size + dp(12)))
        )
        self.add_widget(label)
        self._add_spacer(dp(4))

    def _add_paragraph(self, text):
        theme = ThemeManager.get_theme()
        text, has_markup = self._convert_to_kivy_markup(text)

        label = Label(
            text=text,
            font_size=self.font_size,
            font_name='JetBrainsMono',
            color=theme.get('text_color', (0.85, 0.88, 0.90, 1)),
            size_hint_y=None,
            halign='left',
            valign='top',
            markup=has_markup,
            text_size=(self.width - dp(30), None)
        )
        label.bind(
            width=lambda inst, val: setattr(inst, 'text_size', (val - dp(30), None)),
            texture_size=lambda inst, sz: setattr(inst, 'height', sz[1] + dp(10))
        )
        self.add_widget(label)

    def _add_list_item(self, text):
        theme = ThemeManager.get_theme()
        text, has_markup = self._convert_to_kivy_markup(text)

        label = Label(
            text=f"• {text}",
            font_size=self.font_size,
            font_name='JetBrainsMono',
            color=theme.get('text_color', (0.85, 0.88, 0.90, 1)),
            size_hint_y=None,
            halign='left',
            valign='top',
            markup=has_markup,
            text_size=(self.width - dp(40), None)
        )
        label.bind(
            width=lambda inst, val: setattr(inst, 'text_size', (val - dp(40), None)),
            texture_size=lambda inst, sz: setattr(inst, 'height', sz[1] + dp(10))
        )
        self.add_widget(label)

    def _add_quote(self, text):
        theme = ThemeManager.get_theme()
        text, has_markup = self._convert_to_kivy_markup(text)

        quote_box = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            spacing=dp(8),
            padding=[dp(8), dp(4), dp(4), dp(4)]
        )

        line = Label(
            text="▌",
            font_size=self.font_size * 2,
            font_name='JetBrainsMono',
            color=theme.get('stats_text', (0.6, 0.63, 0.65, 1)),
            size_hint_x=None,
            width=dp(8)
        )
        quote_box.add_widget(line)

        label = Label(
            text=text,
            font_size=self.font_size,
            font_name='JetBrainsMono',
            color=theme.get('stats_text', (0.6, 0.63, 0.65, 1)),
            size_hint_y=None,
            halign='left',
            valign='top',
            markup=has_markup,
            text_size=(self.width - dp(40), None)
        )
        label.bind(
            width=lambda inst, val: setattr(inst, 'text_size', (val - dp(40), None)),
            texture_size=lambda inst, sz: setattr(inst, 'height', sz[1] + dp(10))
        )
        quote_box.add_widget(label)

        quote_box.bind(
            height=lambda inst, val: setattr(inst, 'height', max(label.height + dp(8), dp(30)))
        )
        self.add_widget(quote_box)

    def _add_code_block(self, code):
        theme = ThemeManager.get_theme()

        lines = code.split('\n')
        if lines:
            min_indent = min((len(l) - len(l.lstrip())) for l in lines if l.strip())
            if min_indent > 0:
                lines = [l[min_indent:] if l.strip() else '' for l in lines]
            code = '\n'.join(lines)

        lines_count = len(lines)
        max_line_length = max((len(l) for l in lines), default=0)

        line_height = dp(18)
        base_height = dp(16)
        calculated_height = base_height + lines_count * line_height

        # БЕЗ ОГРАНИЧЕНИЯ — блок занимает ровно столько, сколько нужно
        code_height = max(calculated_height, dp(80))
        code_height = int(code_height)

        code_scroll = ScrollView(
            size_hint_y=None,
            height=code_height,
            do_scroll_x=True,
            do_scroll_y=False,
            bar_width=dp(4),
            bar_color=(0.5, 0.5, 0.5, 0.8),
            bar_inactive_color=(0.3, 0.3, 0.3, 0.5)
        )

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
            width=max(self.width - dp(20), max_line_length * dp(7) + dp(20)),
            height=code_height,
            padding=(dp(8), dp(8)),
            do_wrap=False
        )

        code_scroll.add_widget(code_input)
        self.add_widget(code_scroll)
        self._add_spacer(dp(4))

        # Обновляем ширину при изменении размера
        def update_code_width(instance, value):
            code_input.width = max(instance.width - dp(20), max_line_length * dp(7) + dp(20))

        self.bind(width=update_code_width)

    def _add_divider(self):
        theme = ThemeManager.get_theme()
        label = Label(
            text="────────────────────",
            font_size=dp(10),
            font_name='JetBrainsMono',
            color=theme.get('stats_text', (0.6, 0.63, 0.65, 1)),
            size_hint_y=None,
            height=dp(20),
            halign='center'
        )
        self.add_widget(label)

    def _add_spacer(self, height=dp(8)):
        spacer = Label(size_hint_y=None, height=height)
        self.add_widget(spacer)

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

    def on_touch_down(self, touch):
        """Пропускаем touch дальше если он не попадает в нашу область.
        Снимаем выделение с TextInput при тапе вне."""
        if not self.collide_point(*touch.pos):
            # Тап вне — снимаем фокус со всех TextInput внутри
            self._defocus_all_inputs()
            return False

        # Запоминаем начальную позицию для определения свайпа
        touch.ud['md_start_x'] = touch.x
        touch.ud['md_start_y'] = touch.y
        touch.ud['md_widget'] = self
        touch.ud['md_hold_decided'] = False
        touch.ud['md_is_hold'] = False

        # Назначаем задержку — если палец не двинулся, считаем это удержанием
        self._hold_trigger = Clock.schedule_once(
            lambda dt: self._on_hold(touch), 0.25
        )
        # НЕ передаём вниз сразу — ждём решения в on_touch_move / _on_hold
        touch.grab(self)
        return True

    def _on_hold(self, touch):
        """Вызывается через 0.25с — считаем удержанием, разрешаем скролл внутри"""
        touch.ud['md_is_hold'] = True
        touch.ud['md_hold_decided'] = True
        # Теперь передаём событие вложенным виджетам (ScrollView, TextInput)
        touch.ungrab(self)
        super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if not self.collide_point(*touch.pos) and touch.grab_current is not self:
            return False

        if touch.grab_current is self:
            dx = abs(touch.x - touch.ud.get('md_start_x', touch.x))
            dy = abs(touch.y - touch.ud.get('md_start_y', touch.y))

            if not touch.ud.get('md_hold_decided', False):
                if dx > dp(8) or dy > dp(8):
                    # Быстрый свайп — отменяем удержание, отдаём внешнему скролу
                    if hasattr(self, '_hold_trigger') and self._hold_trigger:
                        self._hold_trigger.cancel()
                        self._hold_trigger = None
                    touch.ud['md_hold_decided'] = True
                    touch.ud['md_is_hold'] = False
                    touch.ungrab(self)
                    # Возвращаем False — пусть родительский ScrollView обработает
                    return False
            elif touch.ud.get('md_is_hold', False):
                return super().on_touch_move(touch)

        return False

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            # Отменяем таймер удержания если ещё не сработал
            if hasattr(self, '_hold_trigger') and self._hold_trigger:
                self._hold_trigger.cancel()
                self._hold_trigger = None
            touch.ungrab(self)

            if not touch.ud.get('md_hold_decided', False) or not touch.ud.get('md_is_hold', False):
                # Короткий тап — снимаем выделение
                self._defocus_all_inputs()
                return True

        if not self.collide_point(*touch.pos):
            return False
        return super().on_touch_up(touch)

    def _defocus_all_inputs(self):
        """Снимает фокус и выделение со всех TextInput внутри"""
        def _unfocus(widget):
            if isinstance(widget, TextInput):
                widget.focus = False
                widget.cancel_selection()
            for child in widget.children:
                _unfocus(child)
        _unfocus(self)

    def apply_theme(self):
        self._update_background()

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
from kivy.core.text import Label as CoreLabel
import re

from ide_core.themes import ThemeManager


def _force_defocus(widget):
    if isinstance(widget, TextInput):
        if widget.focus:
            widget.focus = False
        widget.cancel_selection()
        try:
            for handle_name in ('_handle_left', '_handle_right', '_handle_middle'):
                h = getattr(widget, handle_name, None)
                if h:
                    h.opacity = 0
                    if hasattr(h, 'parent') and h.parent:
                        h.parent.remove_widget(h)
        except Exception:
            pass
        # Очистка bubble меню
        try:
            if hasattr(widget, '_cut_copy_paste'):
                widget._cut_copy_paste = None
            if hasattr(widget, '_popup'):
                widget._popup = None
        except Exception:
            pass
    for child in getattr(widget, 'children', []):
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
            elif stripped.startswith('|') and stripped.endswith('|'):
                # Собираем все строки таблицы
                table_lines = []
                while i < len(lines) and lines[i].strip().startswith('|'):
                    table_lines.append(lines[i].strip())
                    i += 1
                self._add_table(table_lines)
                continue  # i уже сдвинут
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

    @staticmethod
    def _get_max_line_width(lines, font_size=dp(12), font_name='JetBrainsMono'):
        """Точное вычисление ширины самой длинной строки с учетом шрифта."""
        if not lines:
            return dp(100)
        core_label = CoreLabel(font_name=font_name, font_size=font_size, text='')
        max_w = 0
        for line in lines:
            if not line.strip():
                continue
            core_label.text = line
            core_label.refresh()
            w = core_label.content_width
            if w > max_w:
                max_w = w
        return max_w + dp(4)  # небольшой запас

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

        line_height = dp(18)
        code_height = int(max(dp(40) + lines_count * line_height, dp(80)))

        code_scroll = CodeScrollView(
            size_hint=(1, None),
            height=code_height,
            do_scroll_x=True,
            do_scroll_y=False,
            bar_width=dp(4),
            bar_color=(0.5, 0.5, 0.5, 0.8),
            bar_inactive_color=(0.3, 0.3, 0.3, 0.5),
        )

        # Точная ширина по самой длинной строке
        content_width = self._get_max_line_width(lines, font_size=dp(12))
        min_width = content_width + dp(32)  # комфортный отступ

        def _compute_w():
            return max(self.width - dp(8), min_width)

        code_input = TextInput(
            text=code,
            readonly=True,
            font_size=dp(12),
            font_name='JetBrainsMono',
            background_color=theme.get('tab_bg', (0.843, 0.816, 1.0, 1)),
            foreground_color=theme.get('lesson_input_text', (0.95, 0.95, 0.95, 1)),
            background_normal='',
            background_active='',
            size_hint=(None, None),
            width=_compute_w(),
            height=code_height,
            padding=(dp(12), dp(10)),
            do_wrap=False,

            # Основные настройки — без капелек, но с меню
            use_handles=False,      # ← главное: без капелек
            use_bubble=True,        # контекстное меню (Copy, Select All)
            cursor_blink=False,
            selection_color=(0.3, 0.6, 1.0, 0.35),
            cursor_color=(0, 0, 0, 0),
        )

        code_scroll.add_widget(code_input)
        self.add_widget(code_scroll)
        self._add_spacer(dp(6))

        def _update_code_width(instance, value):
            code_input.width = _compute_w()

        self.bind(width=_update_code_width)

        # === Улучшенное поведение меню и очистка ===
        def _show_menu(*args):
            try:
                if code_input.selection_text:
                    if hasattr(code_input, '_show_cut_copy_paste'):
                        code_input._show_cut_copy_paste()
                    elif hasattr(code_input, 'show_cut_copy_paste'):
                        code_input.show_cut_copy_paste()
            except Exception:
                pass

        def _clean_handles(*args):
            try:
                for name in ('_handle_left', '_handle_right', '_handle_middle'):
                    handle = getattr(code_input, name, None)
                    if handle:
                        handle.opacity = 0
            except Exception:
                pass

        # Привязки событий
        code_input.bind(selection_from=_show_menu)
        code_input.bind(selection_to=_show_menu)
        code_input.bind(on_double_tap=lambda *a: Clock.schedule_once(_show_menu, 0.1))
        code_input.bind(focus=_clean_handles)

        # Очистка при удалении виджета
        def _on_parent_change(inst, parent):
            if parent is None:
                _force_defocus(code_input)
        code_input.bind(parent=_on_parent_change)

    def _add_table(self, table_lines):
        """
        Рендерит Markdown-таблицу. Ширина каждого столбца подстраивается
        под самую длинную строку в этом столбце (включая заголовок).
        Таблица оборачивается в горизонтальный CodeScrollView.
        """
        theme = ThemeManager.get_theme()

        # Парсим строки таблицы
        def parse_row(line):
            # Убираем крайние | и делим по |
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            return cells

        rows = []
        separator_idx = None
        for idx, line in enumerate(table_lines):
            stripped = line.strip()
            # Строка-разделитель: | --- | :---: | ---: |
            if re.match(r'^\|[\s\-:|]+\|$', stripped):
                separator_idx = idx
                continue
            rows.append(parse_row(stripped))

        if not rows:
            return

        header = rows[0] if separator_idx is not None and len(rows) > 0 else None
        data_rows = rows[1:] if header is not None else rows

        # Определяем число столбцов
        num_cols = max(len(r) for r in rows)

        # Вычисляем максимальную длину текста в каждом столбце
        CHAR_WIDTH = dp(7.5)   # ширина одного символа JetBrainsMono 12dp
        CELL_PAD   = dp(16)    # горизонтальный padding ячейки (8 с каждой стороны)
        MIN_COL_W  = dp(40)

        col_widths = [MIN_COL_W] * num_cols

        all_rows = ([header] if header else []) + data_rows
        for row in all_rows:
            for c_idx, cell in enumerate(row):
                if c_idx >= num_cols:
                    break
                text_clean = self._strip_inline_markdown(cell)
                needed = len(text_clean) * CHAR_WIDTH + CELL_PAD
                if needed > col_widths[c_idx]:
                    col_widths[c_idx] = needed

        ROW_H      = dp(30)
        HEADER_H   = dp(34)
        BORDER_W   = dp(1)

        total_w = sum(col_widths) + BORDER_W * (num_cols + 1)
        total_rows = (1 if header else 0) + len(data_rows)
        total_h = HEADER_H + ROW_H * len(data_rows) + BORDER_W * (total_rows + 1)

        # Горизонтальный скролл для таблицы
        scroll = CodeScrollView(
            size_hint=(1, None),
            height=total_h,
            do_scroll_x=True,
            do_scroll_y=False,
            bar_width=dp(3),
            bar_color=(0.5, 0.5, 0.5, 0.7),
            bar_inactive_color=(0.3, 0.3, 0.3, 0.4),
        )

        container = BoxLayout(
            orientation='vertical',
            size_hint=(None, None),
            width=total_w,
            height=total_h,
            spacing=0,
        )

        bg_header  = theme.get('lesson_input_bg',   (0.22, 0.26, 0.35, 1))
        bg_row     = theme.get('editor_bg',          (0.188, 0.204, 0.251, 1))
        bg_alt     = theme.get('tab_bg',             (0.20, 0.22, 0.28, 1))
        border_clr = theme.get('stats_text',         (0.35, 0.38, 0.42, 1))
        text_clr   = theme.get('text_color',         (0.85, 0.88, 0.90, 1))
        header_clr = theme.get('lesson_input_text',  (0, 0, 0, 1))

        def make_cell(text, width, height, bg_color, text_color, bold=False):
            cell = BoxLayout(size_hint=(None, None), width=width, height=height)
            with cell.canvas.before:
                Color(*bg_color)
                rect = Rectangle(pos=cell.pos, size=cell.size)
            def _upd(inst, _):
                rect.pos  = inst.pos
                rect.size = inst.size
            cell.bind(pos=_upd, size=_upd)

            text_clean = self._strip_inline_markdown(text)
            lbl = Label(
                text=text_clean,
                font_size=dp(12),
                font_name='JetBrainsMono',
                color=text_color,
                size_hint=(1, 1),
                halign='left',
                valign='middle',
                bold=bold,
                padding=(dp(8), 0),
            )
            lbl.bind(size=lambda inst, _: setattr(inst, 'text_size', inst.size))
            cell.add_widget(lbl)
            return cell

        def make_row(cells_text, row_height, bg_color, text_color, bold=False):
            row = BoxLayout(
                orientation='horizontal',
                size_hint=(None, None),
                width=total_w,
                height=row_height,
                spacing=0,
            )

            # Левый бордюр — отдельный виджет, как и правые
            left_border = Label(
                size_hint=(None, None),
                width=BORDER_W,
                height=row_height,
            )
            with left_border.canvas.before:
                Color(*border_clr)
                lb = Rectangle(pos=left_border.pos, size=left_border.size)
            left_border.bind(pos=lambda inst, _, _lb=lb: setattr(_lb, 'pos', inst.pos))
            row.add_widget(left_border)

            for c_idx in range(num_cols):
                cell_text = cells_text[c_idx] if c_idx < len(cells_text) else ''
                cw = col_widths[c_idx]

                cell_box = BoxLayout(
                    orientation='horizontal',
                    size_hint=(None, None),
                    width=cw + BORDER_W,
                    height=row_height,
                    spacing=0,
                    padding=[0, 0, 0, 0],
                )
                cell = make_cell(cell_text, cw, row_height, bg_color, text_color, bold)
                cell_box.add_widget(cell)

                # Правый бордюр каждой ячейки
                border = Label(
                    size_hint=(None, None),
                    width=BORDER_W,
                    height=row_height,
                )
                with border.canvas.before:
                    Color(*border_clr)
                    rb = Rectangle(pos=border.pos, size=border.size)
                border.bind(pos=lambda inst, _, _rb=rb: setattr(_rb, 'pos', inst.pos))
                cell_box.add_widget(border)
                row.add_widget(cell_box)
            return row

        # Верхний бордюр
        def add_hline(parent, width):
            line = Label(size_hint=(None, None), width=width, height=BORDER_W)
            with line.canvas.before:
                Color(*border_clr)
                r = Rectangle(pos=line.pos, size=line.size)
            line.bind(pos=lambda inst, _, _r=r: setattr(_r, 'pos', inst.pos))
            parent.add_widget(line)

        add_hline(container, total_w)

        if header:
            container.add_widget(make_row(header, HEADER_H, bg_header, header_clr, bold=True))
            add_hline(container, total_w)

        for r_idx, row_data in enumerate(data_rows):
            bg = bg_row if r_idx % 2 == 0 else bg_alt
            container.add_widget(make_row(row_data, ROW_H, bg, text_clr))
            add_hline(container, total_w)

        scroll.add_widget(container)
        self.add_widget(scroll)
        self._add_spacer(dp(6))

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

    def on_parent(self, instance, parent):
        """Дополнительная очистка при удалении из дерева (закрытие окна урока)."""
        if parent is None:
            _force_defocus(self)
            Clock.schedule_once(lambda dt: _force_defocus(self), 0.1)
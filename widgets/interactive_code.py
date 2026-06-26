# widgets/interactive_code.py
"""
Interactive code widget with fill-in-the-blank fields

ОПТИМИЗАЦИИ (v2):
  1. _build_ui строит строки порциями (CHUNK_SIZE) через Clock.schedule_once —
     UI не зависает при длинных шаблонах.
  2. Убраны десятки Clock.schedule_once на каждый label (_adjust_label_width).
     Ширина метки рассчитывается один раз после всего рендера.
  3. _finalize_row_width объединён в один проход после построения всех строк.
"""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp
from kivy.clock import Clock

from ide_core.themes import ThemeManager

CHUNK_SIZE = 6  # строк за один кадр


class InteractiveCodeWidget(BoxLayout):
    """
    Виджет для отображения кода-заготовки с полями ввода.
    Места для ввода обозначаются символом §
    """

    def __init__(self, template, font_size=dp(13), **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.template = template
        self.font_size = font_size
        self.input_fields = []
        self._rows = []
        self._line_h = int(font_size * 1.5)
        self._char_width = font_size * 0.6

        theme = ThemeManager.get_theme()
        with self.canvas.before:
            Color(*theme.get('editor_bg', (0.188, 0.204, 0.251, 1)))
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

        self._build_ui()

    def _update_bg(self, instance, value):
        if hasattr(self, 'bg_rect'):
            self.bg_rect.pos = instance.pos
            self.bg_rect.size = instance.size

    def _build_ui(self):
        theme = ThemeManager.get_theme()
        lh = self._line_h
        cw = self._char_width
        v_pad = max(0, (lh - self.font_size) / 2 - dp(1))
        PAD_H = dp(8)

        lines = self.template.split('\n')

        # Считаем максимальную ширину контента заранее
        max_content_w = 0
        for line in lines:
            if '§' in line:
                parts = line.split('§')
                w = sum(len(p) * cw for p in parts if p)
                w += dp(30) * (len(parts) - 1)
            else:
                w = len(line) * cw + dp(80)
                if len(line) > 35 or 'random.randint' in line or 'int(input' in line or 'while True' in line:
                    w = max(w, dp(800))
                elif line.startswith('#') or line.startswith('    '):
                    w = max(w, dp(600))
                else:
                    w = max(w, dp(500))
            max_content_w = max(max_content_w, w)

        self._content_w = max_content_w + PAD_H * 2

        self.scroll = ScrollView(
            size_hint=(1, 1),
            do_scroll_x=True,
            do_scroll_y=True,
            bar_width=dp(4),
            scroll_type=['bars'],
            scroll_x=0,
            scroll_y=1,
        )

        self.main_container = BoxLayout(
            orientation='vertical',
            size_hint=(None, None),
            spacing=dp(2),
            padding=[PAD_H, dp(8), PAD_H, dp(8)],
        )
        self.main_container.bind(minimum_height=self.main_container.setter('height'))

        self.scroll.add_widget(self.main_container)
        self.add_widget(self.scroll)

        # Запускаем порционное построение строк
        self._pending_lines = list(enumerate(lines))
        self._build_theme = theme
        self._build_lh = lh
        self._build_cw = cw
        self._build_v_pad = v_pad
        self._build_event = Clock.schedule_once(self._build_chunk, 0)

    def _build_chunk(self, dt):
        """Строит CHUNK_SIZE строк за один кадр."""
        theme = self._build_theme
        lh = self._build_lh
        cw = self._build_cw
        v_pad = self._build_v_pad

        chunk = self._pending_lines[:CHUNK_SIZE]
        self._pending_lines = self._pending_lines[CHUNK_SIZE:]

        for _idx, line in chunk:
            if '§' in line:
                row = self._create_line_with_input(line, theme, lh, cw, v_pad)
            else:
                row = self._create_line_text(line, theme, lh, cw)
            self.main_container.add_widget(row)
            self._rows.append(row)

        if self._pending_lines:
            # Ещё есть строки — планируем следующий чанк
            self._build_event = Clock.schedule_once(self._build_chunk, 0)
        else:
            # Всё построено — финальная инициализация размеров
            Clock.schedule_once(self._finalize_sizes, 0)
            # Освобождаем временные данные
            del self._pending_lines, self._build_theme
            del self._build_lh, self._build_cw, self._build_v_pad

    def _finalize_sizes(self, dt):
        """Один финальный проход: выравниваем ширины меток и контейнера."""
        sw = self.scroll.width or self.width
        container_w = max(self._content_w, sw)

        for row in self._rows:
            if isinstance(row, Label):
                # Уточняем по реальному texture, если готов
                if hasattr(row, 'texture') and row.texture:
                    row.width = max(row.width, row.texture_size[0] + dp(8))
            elif isinstance(row, BoxLayout):
                # Пересчитываем ширину строк с полями ввода
                total = sum(c.width for c in row.children) + dp(10)
                row.width = total
                container_w = max(container_w, total + dp(20))

        self.main_container.width = container_w
        self.scroll.scroll_x = 0
        self.scroll.scroll_y = 1

    # ------------------------------------------------------------------ #
    #  Touch — скролл пальцем                                             #
    # ------------------------------------------------------------------ #

    def on_touch_down(self, touch):
        if not self.scroll.collide_point(*touch.pos):
            return super().on_touch_down(touch)

        if super().on_touch_down(touch):
            return True

        touch.ud['icw_scrolling'] = True
        touch.ud['icw_sx'] = self.scroll.scroll_x
        touch.ud['icw_sy'] = self.scroll.scroll_y
        touch.ud['icw_ox'] = touch.x
        touch.ud['icw_oy'] = touch.y
        touch.ud['icw_locked'] = None
        touch.grab(self)
        return True

    def on_touch_move(self, touch):
        if touch.grab_current is not self:
            return super().on_touch_move(touch)
        if not touch.ud.get('icw_scrolling'):
            return super().on_touch_move(touch)

        dx = touch.ud['icw_ox'] - touch.x
        dy = touch.ud['icw_oy'] - touch.y

        locked = touch.ud['icw_locked']
        THRESHOLD = dp(8)

        if locked is None:
            if abs(dx) > THRESHOLD or abs(dy) > THRESHOLD:
                touch.ud['icw_locked'] = 'h' if abs(dx) > abs(dy) else 'v'
            return True

        sv = self.scroll
        cont_w = self.main_container.width
        cont_h = self.main_container.height
        sv_w = sv.width
        sv_h = sv.height

        if locked == 'h' and cont_w > sv_w:
            max_scroll = cont_w - sv_w
            new_sx = touch.ud['icw_sx'] + dx / max_scroll
            sv.scroll_x = max(0.0, min(1.0, new_sx))

        elif locked == 'v' and cont_h > sv_h:
            max_scroll = cont_h - sv_h
            new_sy = touch.ud['icw_sy'] + dy / max_scroll
            sv.scroll_y = max(0.0, min(1.0, new_sy))

        return True

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            return True
        return super().on_touch_up(touch)

    # ------------------------------------------------------------------ #
    #  Строки                                                              #
    # ------------------------------------------------------------------ #

    def _create_line_text(self, text, theme, lh, cw):
        base_w = len(text) * cw + dp(40)
        if text.startswith('#') or len(text) > 50:
            base_w = max(base_w, dp(1500))
        base_w = max(base_w, dp(400))

        label = Label(
            text=text,
            font_size=self.font_size,
            font_name='JetBrainsMono',
            color=theme.get('editor_text', (0.95, 0.95, 0.95, 1)),
            halign='left',
            valign='middle',
            size_hint=(None, None),
            width=base_w,
            height=lh,
            text_size=(base_w, lh),
        )
        return label

    def _create_line_with_input(self, line, theme, lh, cw, v_pad):
        parts = line.split('§')

        row = BoxLayout(
            orientation='horizontal',
            size_hint=(None, None),
            height=lh,
            spacing=dp(2),
            padding=0,
        )

        row_w = 0
        for i, part in enumerate(parts):
            if part:
                part_w = len(part) * cw + dp(15)
                label = Label(
                    text=part,
                    font_size=self.font_size,
                    font_name='JetBrainsMono',
                    color=theme.get('editor_text', (0.95, 0.95, 0.95, 1)),
                    halign='left',
                    valign='middle',
                    size_hint=(None, None),
                    width=part_w,
                    height=lh,
                    text_size=(part_w, lh),
                )
                row.add_widget(label)
                row_w += part_w

            if i < len(parts) - 1:
                field = self._make_field(theme, lh, v_pad, row)
                row.add_widget(field)
                self.input_fields.append(field)
                row_w += dp(30)

        row.width = row_w + dp(10)
        return row

    def _make_field(self, theme, lh, v_pad, parent_row):
        field = TextInput(
            text='',
            multiline=False,
            font_size=self.font_size,
            font_name='JetBrainsMono',
            size_hint=(None, None),
            width=dp(30),
            height=lh,
            padding=[dp(4), 0, dp(4), 0],
            background_color=theme.get('tab_bg', (0.25, 0.30, 0.40, 1)),
            foreground_color=theme.get('lesson_input_text', (0.95, 0.95, 0.95, 1)),
            cursor_color=theme.get('input_cursor', (1, 1, 1, 1)),
            background_normal='',
            background_active='',
            keyboard_suggestions=False,
        )

        field._parent_row = parent_row
        field._char_width = self._char_width

        def on_text(inst, val):
            new_w = max(dp(30), len(val) * inst._char_width + dp(20))
            new_w = min(new_w, dp(400))
            if abs(new_w - inst.width) < dp(1):
                return
            inst.width = new_w
            row_w = sum(c.width for c in inst._parent_row.children)
            inst._parent_row.width = row_w
            needed = row_w + dp(16)
            if needed > self.main_container.width:
                sy = self.scroll.scroll_y
                self.main_container.width = needed
                self.scroll.scroll_y = sy

        field.bind(text=on_text)

        from utils.vibration_manager import VibrationManager

        def on_focus(inst, focused):
            if focused:
                VibrationManager.vibrate(0.015)

        field.bind(focus=on_focus)
        return field

    # ------------------------------------------------------------------ #
    #  Публичный API                                                       #
    # ------------------------------------------------------------------ #

    def get_user_code(self):
        lines = self.template.split('\n')
        field_index = 0
        result_lines = []

        for line in lines:
            if '§' in line:
                parts = line.split('§')
                new_line = ''
                for i, part in enumerate(parts):
                    new_line += part
                    if i < len(parts) - 1 and field_index < len(self.input_fields):
                        new_line += self.input_fields[field_index].text
                        field_index += 1
                result_lines.append(new_line)
            else:
                result_lines.append(line)

        return '\n'.join(result_lines)

    def set_values(self, values):
        for i, value in enumerate(values):
            if i < len(self.input_fields):
                self.input_fields[i].text = value

    def get_values(self):
        return [field.text for field in self.input_fields]

    def has_unfilled_blanks(self):
        return any(not field.text.strip() for field in self.input_fields)

    def clear_values(self):
        for field in self.input_fields:
            field.text = ''

    def apply_theme(self):
        theme = ThemeManager.get_theme()
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*theme.get('editor_bg', (0.188, 0.204, 0.251, 1)))
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)

        for row in self._rows:
            if isinstance(row, Label):
                row.color = theme.get('editor_text', (0.95, 0.95, 0.95, 1))
            elif isinstance(row, BoxLayout):
                for child in row.children:
                    if isinstance(child, TextInput):
                        child.background_color = theme.get('lesson_input_bg', (0.25, 0.30, 0.40, 1))
                        child.foreground_color = theme.get('lesson_input_text', (0.95, 0.95, 0.95, 1))
                        child.cursor_color = theme.get('input_cursor', (1, 1, 1, 1))
                    elif isinstance(child, Label):
                        child.color = theme.get('editor_text', (0.95, 0.95, 0.95, 1))

        for field in self.input_fields:
            field.background_color = theme.get('lesson_input_bg', (0.25, 0.30, 0.40, 1))
            field.foreground_color = theme.get('lesson_input_text', (0.95, 0.95, 0.95, 1))
            field.cursor_color = theme.get('input_cursor', (1, 1, 1, 1))
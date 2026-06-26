"""
Code editor widget with line numbers, syntax highlighting and block folding
"""
import re
import time
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.codeinput import CodeInput
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle, Line, RoundedRectangle
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.utils import platform
from kivy.app import App

from utils.screen_utils import get_screen_category, adaptive_dp, adaptive_sp
from utils.debug_utils import log_error
from ide_core.themes import ThemeManager, HAS_PYGMENTS

if HAS_PYGMENTS:
    from pygments.lexers import PythonLexer

_FOLD_MARKER = '\u25B6'


def _get_fold_ranges(lines):
    ranges = []
    n = len(lines)
    i = 0
    _marker = _FOLD_MARKER
    while i < n:
        line = lines[i]
        # Fast path: empty lines or already-folded markers
        if not line or not line.strip():
            i += 1
            continue
        if _marker in line:
            i += 1
            continue

        lstripped = line.lstrip()
        stripped = lstripped.rstrip()
        if not stripped:
            i += 1
            continue

        indent = len(line) - len(lstripped)

        if stripped.endswith(':') and stripped[0] != '#':
            block_end = i
            j = i + 1
            while j < n:
                jline = lines[j]
                if not jline or not jline.strip():
                    j += 1
                    continue
                # Inline indent check — avoid lstrip() call
                jindent = len(jline) - len(jline.lstrip())
                if jindent > indent:
                    block_end = j
                    j += 1
                else:
                    break
            if block_end > i:
                ranges.append((i, block_end))
        i += 1
    return ranges


class FoldingManager:
    def __init__(self):
        self._orig_lines = []
        self._folds = {}
        self._fold_ranges = []

    def set_lines(self, lines):
        self._orig_lines = list(lines)
        self._folds = {}
        self._fold_ranges = _get_fold_ranges(self._orig_lines)

    def get_orig_lines(self):
        return self._orig_lines

    def get_display_lines(self):
        result = []
        i = 0
        n = len(self._orig_lines)
        while i < n:
            if i in self._folds:
                header = self._orig_lines[i]
                count = self._folds[i]['end'] - i
                result.append(header.rstrip() + f'  ... ▶ {count} lines folded')
                i = self._folds[i]['end'] + 1
            else:
                result.append(self._orig_lines[i])
                i += 1
        return result

    def is_foldable(self, orig_line):
        return any(s == orig_line for s, e in self._fold_ranges)

    def get_fold_ranges(self):
        return self._fold_ranges

    def is_folded(self, orig_line):
        return orig_line in self._folds

    def fold(self, orig_line):
        for s, e in self._fold_ranges:
            if s == orig_line and orig_line not in self._folds:
                hidden = self._orig_lines[s + 1: e + 1]
                self._folds[s] = {'end': e, 'lines': hidden}
                return True
        return False

    def unfold(self, orig_line):
        if orig_line in self._folds:
            del self._folds[orig_line]
            return True
        return False

    def toggle(self, orig_line):
        if orig_line in self._folds:
            self.unfold(orig_line)
        else:
            self.fold(orig_line)

    def display_to_orig(self, display_line):
        di = 0
        oi = 0
        n = len(self._orig_lines)
        while oi < n:
            if di == display_line:
                return oi
            if oi in self._folds:
                oi = self._folds[oi]['end'] + 1
            else:
                oi += 1
            di += 1
        return oi

    def orig_to_display(self, orig_line):
        di = 0
        oi = 0
        while oi < orig_line and oi < len(self._orig_lines):
            if oi in self._folds:
                oi = self._folds[oi]['end'] + 1
            else:
                oi += 1
            di += 1
        return di

    def apply_display_edit(self, new_display_lines):
        if not new_display_lines:
            self._orig_lines = []
            self._folds = {}
            self._fold_ranges = []
            return

        old_folds = self._folds.copy()
        old_orig_lines = self._orig_lines.copy()

        new_orig = []
        i = 0
        while i < len(new_display_lines):
            line = new_display_lines[i]

            if _FOLD_MARKER in line or '▶' in line:
                found = False
                for start, fold_data in old_folds.items():
                    old_header = old_orig_lines[start].rstrip()
                    if (old_header in line or
                            line.rstrip().startswith(old_header.rstrip()) or
                            old_header.startswith(line.split('...')[0].strip())):
                        end = fold_data['end']
                        new_orig.extend(old_orig_lines[start:end + 1])
                        i += 1
                        found = True
                        break

                if not found:
                    new_orig.append(line)
                    i += 1
            else:
                new_orig.append(line)
                i += 1

        self._orig_lines = new_orig
        self._folds = {}
        self._fold_ranges = _get_fold_ranges(self._orig_lines)

        for start, fold_data in old_folds.items():
            if start < len(self._orig_lines):
                old_header = old_orig_lines[start].rstrip()
                new_header = self._orig_lines[start].rstrip()

                if (old_header == new_header or
                        old_header.startswith(new_header) or
                        new_header.startswith(old_header.split(':')[0] if ':' in old_header else old_header)):
                    for s, e in self._fold_ranges:
                        if s == start:
                            self._folds[start] = {
                                'end': e,
                                'lines': self._orig_lines[s + 1:e + 1]
                            }
                            break


class VirtualLinePanel(Widget):
    def __init__(self, on_fold_toggle=None, **kwargs):
        super().__init__(**kwargs)
        self._line_count = 0
        self._line_height = 16
        self._font_size = 12
        self._theme = {}
        self._scroll_y = 1.0
        self._editor_height = 0
        self._redraw_ev = None
        self._fold_ranges = []
        self._folded_set = set()
        self._display_to_orig = {}
        self._on_fold_toggle = on_fold_toggle
        self.bind(pos=self._schedule_redraw, size=self._schedule_redraw)

    def update(self, line_count, line_height, font_size, theme, scroll_y,
               editor_height, fold_ranges=None, folded_set=None, display_to_orig=None):
        self._line_count = line_count
        self._line_height = line_height
        self._font_size = font_size
        self._theme = theme
        self._scroll_y = scroll_y
        self._editor_height = editor_height
        self._fold_ranges = fold_ranges or []
        self._folded_set = folded_set or set()
        self._display_to_orig = display_to_orig or {}
        self._schedule_redraw()

    def _schedule_redraw(self, *args):
        if self._redraw_ev:
            self._redraw_ev.cancel()
        self._redraw_ev = Clock.schedule_once(self._redraw, 0)

    def _redraw(self, dt=None):
        self.canvas.clear()
        if self._line_count == 0 or self._line_height <= 0:
            return

        lh = self._line_height
        n = self._line_count
        total_height = n * lh
        panel_width = self.width

        theme = self._theme
        bg_color = theme.get('panel_bg', (0.12, 0.13, 0.14, 1))
        text_color = theme.get('panel_text', (0.45, 0.48, 0.50, 1))
        fold_color = theme.get('fold_button_color', (0.4, 0.6, 0.9, 0.85))
        folded_bg = theme.get('fold_button_folded_bg', (0.3, 0.5, 0.8, 0.3))

        editor_h = self._editor_height or self.height
        scroll_y = self._scroll_y
        max_scroll_offset = max(0, total_height - editor_h)
        scroll_offset = (1.0 - scroll_y) * max_scroll_offset

        first_visible = max(0, int(scroll_offset / lh) - 1)
        visible_count = int(editor_h / lh) + 3
        last_visible = min(n, first_visible + visible_count)

        foldable_orig = {s for s, e in self._fold_ranges}

        from kivy.core.text import Label as CoreLabel

        # Texture cache keyed by (line_number, font_size) to avoid re-creating
        # CoreLabel objects for unchanged line numbers on every redraw.
        if not hasattr(self, '_num_tex_cache'):
            self._num_tex_cache = {}
        cache = self._num_tex_cache
        fs = self._font_size

        btn_size = min(lh * 0.55, dp(13))
        btn_margin_right = dp(3)
        num_pad_right = btn_size + btn_margin_right * 2 + dp(2)

        with self.canvas:
            Color(*bg_color)
            Rectangle(pos=self.pos, size=self.size)

            for di in range(first_visible, last_visible):
                orig_i = self._display_to_orig.get(di, di)
                y = self.y + self.height - (di + 1) * lh + scroll_offset
                if y + lh < self.y or y > self.y + self.height:
                    continue

                is_foldable = orig_i in foldable_orig
                is_folded = orig_i in self._folded_set

                # --- line number texture (cached) ---
                cache_key = (orig_i + 1, fs)
                if cache_key not in cache:
                    lbl = CoreLabel(text=str(orig_i + 1), font_size=fs,
                                    halign='right', valign='middle')
                    lbl.refresh()
                    cache[cache_key] = lbl.texture
                tex = cache[cache_key]
                if tex:
                    Color(*text_color)
                    tw, th = tex.size
                    tx = self.x + panel_width - num_pad_right - tw
                    ty = y + (lh - th) / 2
                    Rectangle(texture=tex, pos=(tx, ty), size=(tw, th))

                if is_foldable:
                    btn_x = self.x + panel_width - btn_size - btn_margin_right
                    btn_y = y + (lh - btn_size) / 2
                    if is_folded:
                        Color(*folded_bg)
                        RoundedRectangle(pos=(btn_x, btn_y), size=(btn_size, btn_size),
                                         radius=[dp(2)])
                    Color(*fold_color)
                    arrow = '▶' if is_folded else '▼'
                    # Arrow textures are small; cache them too
                    arrow_key = (arrow, btn_size)
                    if arrow_key not in cache:
                        albl = CoreLabel(text=arrow, font_name='SourceBold',
                                         font_size=btn_size * 0.85,
                                         halign='center', valign='middle')
                        albl.refresh()
                        cache[arrow_key] = albl.texture
                    atex = cache[arrow_key]
                    if atex:
                        aw, ah = atex.size
                        ax = btn_x + (btn_size - aw) / 2
                        ay = btn_y + (btn_size - ah) / 2
                        Rectangle(texture=atex, pos=(ax, ay), size=(aw, ah))

        # Limit cache size to avoid unbounded growth (keep last 1000 entries)
        if len(cache) > 1000:
            keys = list(cache.keys())
            for k in keys[:200]:
                del cache[k]

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return False
        if not self._on_fold_toggle:
            return False

        lh = self._line_height
        n = self._line_count
        total_height = n * lh
        editor_h = self._editor_height or self.height
        scroll_y = self._scroll_y
        max_scroll_offset = max(0, total_height - editor_h)
        scroll_offset = (1.0 - scroll_y) * max_scroll_offset

        btn_size = min(lh * 0.55, dp(13))
        btn_margin_right = dp(3)
        foldable_orig = {s for s, e in self._fold_ranges}

        rel_y = self.y + self.height - touch.y + scroll_offset
        di = int(rel_y / lh)
        if 0 <= di < n:
            orig_i = self._display_to_orig.get(di, di)
            if orig_i in foldable_orig:
                btn_left = self.x + self.width - btn_size - btn_margin_right - dp(2)
                if touch.x >= btn_left:
                    self._on_fold_toggle(orig_i)
                    return True
        return False


class LineNumberTextInput(BoxLayout):
    """Основной компонент редактора кода с нумерацией строк и сворачиванием блоков"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        ThemeManager.register(self)
        self.original_lines = []
        self.current_syntax_style = 'monokai'
        self._ensuring_trailing = False
        self._keyboard_visible = True
        self._current_line_highlight = None
        self._indent_guides = []
        self._undo_stack = []
        self._redo_stack = []
        self._undo_max = 50
        self._undo_lock = False
        self._redraw_pending = False
        self._indent_guides_pending = False

        self._tab_indenting = False
        self._ensuring_trailing = False

        self._panel_update_scheduled = False
        self._cached_line_count = 0
        self._cached_max_line_length = 0
        self._text_width_ev = None
        self._width_cache = {}

        self._folding = FoldingManager()
        self._ignore_text_change = False

        self._create_ui()
        self.apply_theme(ThemeManager.get_theme())
        Window.bind(on_keyboard=self._on_window_keyboard)
        self.text_input.bind(on_key_down=self._on_key_down)
        self.text_input.bind(font_name=self._on_font_changed)
        Window.bind(on_key_down=self._on_window_key_down)

        self._scroll_timer = None
        self._last_cursor_pos = None

        self._auto_scroll_ev = None
        self._last_touch_pos = None
        self._is_selecting = False

        self._undo_debounce_ev = None
        self._undo_last_text = ''

        self._highlight_timer = None

        self._last_scroll_time = 0

        self._cached_display_to_orig = {}
        self._display_map_version = 0

        self._touch_start_time = 0

        self._cached_max_line_n = -1

        # Автозакрытие скобок и кавычек
        self._auto_close_pairs = {
            '(': ')',
            '[': ']',
            '{': '}',
            '"': '"',
            "'": "'"
        }
        self._auto_close_enabled = True

        # Подсветка парных скобок
        self._bracket_pairs = {
            '(': ')',
            ')': '(',
            '[': ']',
            ']': '[',
            '{': '}',
            '}': '{'
        }
        self._bracket_highlight_enabled = True
        self._highlighted_brackets = None  # (start_pos, end_pos)

    def cleanup(self):
        """Очищает ресурсы при уничтожении редактора"""
        if hasattr(self, 'line_panel') and hasattr(self.line_panel, '_num_tex_cache'):
            self.line_panel._num_tex_cache.clear()
        if hasattr(self, '_width_cache'):
            self._width_cache.clear()

    # ------------------------------------------------------------------ автозакрытие скобок и кавычек

    def _handle_auto_close(self, text_input, key, *args):
        """Обрабатывает автозакрытие скобок и кавычек"""
        if not self._auto_close_enabled:
            return

        # Проверяем, является ли нажатая клавиша открывающей скобкой или кавычкой
        if key in self._auto_close_pairs:
            closing_char = self._auto_close_pairs[key]

            # Получаем текущий текст и позицию курсора
            cursor_col = text_input.cursor_col
            cursor_row = text_input.cursor_row
            text = text_input.text

            # Вставляем открывающий символ и закрывающий
            # Но сначала проверяем, не стоит ли после курсора закрывающий символ
            lines = text.split('\n')
            if cursor_row < len(lines):
                current_line = lines[cursor_row]
                if cursor_col < len(current_line):
                    next_char = current_line[cursor_col]
                    # Если следующий символ - это закрывающий, просто пропускаем курсор
                    if next_char == closing_char:
                        text_input.cursor = (cursor_row, cursor_col + 1)
                        return True

            # Вставляем пару скобок/кавычек
            from kivy.clock import Clock
            def insert_pair(dt):
                try:
                    cursor_idx = text_input.cursor_index()
                    text_before = text[:cursor_idx]
                    text_after = text[cursor_idx:]
                    new_text = text_before + key + closing_char + text_after
                    text_input.text = new_text
                    text_input.cursor = (cursor_row, cursor_col + 1)
                except Exception as e:
                    log_error(f"Auto-close error: {e}")

            Clock.schedule_once(insert_pair, 0)
            return True

        # Обработка закрывающих скобок - если пользователь вводит закрывающую скобку,
        # которая совпадает с ожидаемой, просто пропускаем курсор
        elif key in self._auto_close_pairs.values():
            cursor_col = text_input.cursor_col
            cursor_row = text_input.cursor_row
            text = text_input.text
            lines = text.split('\n')

            if cursor_row < len(lines):
                current_line = lines[cursor_row]
                if cursor_col < len(current_line) and current_line[cursor_col] == key:
                    # Пропускаем курсор через закрывающую скобку
                    text_input.cursor = (cursor_row, cursor_col + 1)
                    return True

        return False

    # ------------------------------------------------------------------ scroll freeze

    def _freeze_scroll(self):
        """Полностью блокирует скролл редактора на время операции."""
        sv = getattr(self, 'editor_scroll', None)
        if sv is None:
            return
        self._frozen_scroll_y = sv.scroll_y
        self._frozen_scroll_x = sv.scroll_x
        sv.do_scroll_y = False
        sv.do_scroll_x = False

    def _unfreeze_scroll(self, dt=None):
        """Разблокирует скролл и восстанавливает позицию."""
        sv = getattr(self, 'editor_scroll', None)
        if sv is None:
            return
        sv.scroll_y = self._frozen_scroll_y
        sv.scroll_x = self._frozen_scroll_x
        sv.do_scroll_y = True
        sv.do_scroll_x = True

    # ------------------------------------------------------------------ folding

    def _on_fold_toggle(self, orig_line):
        try:
            self._folding.toggle(orig_line)
            self._apply_folding_to_editor(toggled_orig_line=orig_line)
        except Exception as e:
            log_error(f"fold toggle error: {e}")

    def _apply_folding_to_editor(self, toggled_orig_line=None):
        try:
            sv = getattr(self, 'editor_scroll', None)
            lh = getattr(self.text_input, 'line_height', self._font_size * 1.2)

            # Запоминаем, на каком пикселе экрана находится строка-заголовок ДО fold.
            # Это позволяет после изменения числа строк вычислить новый scroll_y
            # такой, чтобы заголовок остался визуально на том же месте.
            if toggled_orig_line is not None and sv is not None:
                old_display_header = self._folding.orig_to_display(toggled_orig_line)
                old_total_lines = len(self._folding.get_display_lines())
                old_total_h = old_total_lines * lh
                editor_h = sv.height
                old_max_offset = max(0, old_total_h - editor_h)
                old_scroll_offset = (1.0 - sv.scroll_y) * old_max_offset
                # пиксельное расстояние от верха viewport до верха строки-заголовка
                header_px_from_top = old_display_header * lh - old_scroll_offset
            else:
                # Нет конкретной строки — просто фризим
                header_px_from_top = None

            # Замораживаем скролл на время изменения текста
            self._freeze_scroll()

            # Сохраняем позицию курсора
            try:
                old_cursor_idx = self.text_input.cursor_index()
                old_display_line = self.text_input.text[:old_cursor_idx].count('\n')
            except:
                old_display_line = 0

            # Применяем изменения текста
            display_lines = self._folding.get_display_lines()
            new_text = '\n'.join(display_lines)

            self._ignore_text_change = True
            self.text_input.text = new_text
            self.original_lines = display_lines
            self._display_map_version = 0
            self._ignore_text_change = False

            # Восстанавливаем позицию курсора
            if toggled_orig_line is not None:
                target_display_line = self._folding.orig_to_display(toggled_orig_line)
            else:
                target_display_line = min(old_display_line, len(display_lines) - 1)
                target_display_line = max(0, target_display_line)

            try:
                lines_before = display_lines[:target_display_line]
                char_pos = sum(len(l) + 1 for l in lines_before)
                char_pos = min(char_pos, len(new_text))
                self.text_input.cursor = self.text_input.get_cursor_from_index(char_pos)
            except:
                pass

            # Вычисляем новый scroll_y чтобы заголовок остался на том же месте экрана
            if header_px_from_top is not None and sv is not None:
                new_total_lines = len(display_lines)
                new_total_h = new_total_lines * lh
                editor_h = sv.height
                new_max_offset = max(0, new_total_h - editor_h)
                if new_max_offset > 0:
                    new_header_display = self._folding.orig_to_display(toggled_orig_line)
                    # offset такой, чтобы заголовок был на той же пиксельной позиции
                    desired_offset = new_header_display * lh - header_px_from_top
                    desired_offset = max(0.0, min(float(new_max_offset), desired_offset))
                    self._frozen_scroll_y = 1.0 - desired_offset / new_max_offset
                else:
                    self._frozen_scroll_y = 1.0
                self._frozen_scroll_x = sv.scroll_x

            self._refresh_virtual_panel()

            # Размораживаем на следующем кадре — Kivy к этому моменту пересчитал layout
            Clock.schedule_once(self._unfreeze_scroll, 0)
            Clock.schedule_once(self._draw_indent_guides, 0.15)

        except Exception as e:
            self._unfreeze_scroll()
            log_error(f"_apply_folding_to_editor error: {e}")

    def _scroll_to_display_line(self, display_line):
        try:
            lh = getattr(self.text_input, 'line_height', self._font_size * 1.2)
            total_lines = len(self.original_lines)
            total_height = total_lines * lh
            editor_h = self.editor_scroll.height
            if total_height <= editor_h:
                return
            line_top = display_line * lh
            line_bot = line_top + lh
            scroll_y = self.editor_scroll.scroll_y
            max_offset = total_height - editor_h
            current_top = (1.0 - scroll_y) * max_offset
            current_bot = current_top + editor_h
            margin = lh * 2
            if line_top >= current_top + margin and line_bot <= current_bot - margin:
                return
            desired_top = line_top - editor_h / 2 + lh / 2
            desired_top = max(0, min(desired_top, max_offset))
            new_scroll_y = 1.0 - desired_top / max_offset
            self.editor_scroll.scroll_y = max(0.0, min(1.0, new_scroll_y))
        except Exception as e:
            log_error(f"_scroll_to_display_line error: {e}")

    def fold_line(self, line_num):
        orig = self._folding.display_to_orig(line_num)
        if self._folding.fold(orig):
            self._apply_folding_to_editor()

    def unfold_line(self, line_num):
        orig = self._folding.display_to_orig(line_num)
        if self._folding.unfold(orig):
            self._apply_folding_to_editor()

    def fold_all(self):
        for s, e in self._folding.get_fold_ranges():
            self._folding.fold(s)
        self._apply_folding_to_editor()

    def unfold_all(self):
        self._folding._folds.clear()
        self._apply_folding_to_editor()

    # ------------------------------------------------------------------ fonts

    def _on_font_changed(self, instance, value):
        Clock.schedule_once(self.force_full_font_reset, 0.1)
        Clock.schedule_once(self.force_full_font_reset, 0.4)

    def force_full_font_reset(self, dt=None):
        try:
            ti = self.text_input
            if not ti:
                return
            old_text = ti.text
            old_cursor = ti.cursor_index() if hasattr(ti, 'cursor_index') else 0
            ti.text = ""
            if hasattr(ti, '_label'):
                ti._label.font_name = ti.font_name
                ti._label.font_size = ti.font_size
                ti._label.refresh()
            ti.text = old_text
            self._rebuild_line_panel_completely()
            Clock.schedule_once(self._update_text_width, 0.05)
            Clock.schedule_once(self._update_separator, 0.1)
            Clock.schedule_once(self._refresh_virtual_panel, 0.15)
            Clock.schedule_once(self._force_line_panel_refresh, 0.2)
            if old_cursor <= len(ti.text):
                Clock.schedule_once(lambda x: setattr(ti, 'cursor', ti.get_cursor_from_index(old_cursor)), 0.25)
        except Exception as e:
            log_error(f"force_full_font_reset error: {e}")

    def _rebuild_line_panel_completely(self):
        self._refresh_virtual_panel()
        self._update_separator()

    # ------------------------------------------------------------------ theme

    def apply_theme(self, theme):
        self.current_theme_name = theme['name']
        Window.clearcolor = theme['window_bg']

        if hasattr(self, 'bg_color'):
            self.bg_color.rgba = theme['app_bg']

        app = App.get_running_app()
        if app and hasattr(app, '_update_top_panels'):
            app._update_top_panels()

        if hasattr(self, 'text_input'):
            new_style = ThemeManager.get_syntax_style()
            self.text_input.background_color = theme['editor_bg']
            self.text_input.foreground_color = theme['editor_text']
            self.text_input.cursor_color = theme['editor_cursor']
            if 'editor_selection' in theme:
                self.text_input.selection_color = theme['editor_selection']
            if hasattr(self.text_input, 'style') and new_style != self.current_syntax_style:
                self.current_syntax_style = new_style
                try:
                    current_text = self.text_input.text
                    try:
                        cursor_pos = self.text_input.cursor_index()
                    except:
                        cursor_pos = 0
                    self.text_input.style = new_style
                    self.text_input.text = ''
                    self.text_input.text = current_text
                    # Invalidate line-number texture cache after style change
                    if hasattr(self, 'line_panel') and hasattr(self.line_panel, '_num_tex_cache'):
                        self.line_panel._num_tex_cache.clear()

                    def restore_cursor(dt):
                        try:
                            if cursor_pos <= len(self.text_input.text):
                                self.text_input.cursor = self.text_input.get_cursor_from_index(cursor_pos)
                        except:
                            pass

                    Clock.schedule_once(restore_cursor, 0.1)
                except Exception as e:
                    log_error(f"Error changing syntax style: {e}")
        if hasattr(self, 'separator_color'):
            self.separator_color.rgba = (0.3, 0.3, 0.3, 0.3)
        if hasattr(self, 'original_lines') and self.original_lines:
            self._refresh_virtual_panel()

    # ------------------------------------------------------------------ public

    def get_text(self):
        orig = self._folding.get_orig_lines()
        if orig:
            # Обрезаем пустые строки в конце
            while len(orig) > 1 and orig[-1].strip() == '':
                orig.pop()
            return '\n'.join(orig)
        return self.text_input.text if hasattr(self, 'text_input') else ""

    def set_text(self, text):
        if hasattr(self, 'text_input'):
            self._undo_stack.clear()
            self._redo_stack.clear()
            lines = (text or '').split('\n')
            self._folding.set_lines(lines)
            display = self._folding.get_display_lines()
            display_text = '\n'.join(display)
            self._ignore_text_change = True
            self.text_input.text = display_text
            self.original_lines = display
            self._ignore_text_change = False
            if hasattr(self, '_cached_max_line_length'):
                del self._cached_max_line_length
            if hasattr(self, '_cached_max_line_index'):
                del self._cached_max_line_index
            self._refresh_virtual_panel()
            Clock.schedule_once(self._draw_indent_guides, 0.3)

    # ------------------------------------------------------------------ undo/redo

    def undo(self):
        if not self._undo_stack:
            return False
        self._undo_lock = True
        self._redo_stack.append({'text': self.text_input.text, 'cursor': self.text_input.cursor_index()})
        state = self._undo_stack.pop()
        self.text_input.text = state['text']
        self.original_lines = state['text'].split('\n')
        self._folding.apply_display_edit(self.original_lines)
        self._refresh_virtual_panel()
        try:
            pos = min(state['cursor'], len(state['text']))
            self.text_input.cursor = self.text_input.get_cursor_from_index(pos)
        except Exception as e:
            log_error(f"Undo cursor error: {e}")
        self._undo_lock = False
        return True

    def redo(self):
        if not self._redo_stack:
            return False
        self._undo_lock = True
        self._undo_stack.append({'text': self.text_input.text, 'cursor': self.text_input.cursor_index()})
        state = self._redo_stack.pop()
        self.text_input.text = state['text']
        self.original_lines = state['text'].split('\n')
        self._folding.apply_display_edit(self.original_lines)
        self._refresh_virtual_panel()
        try:
            pos = min(state['cursor'], len(state['text']))
            self.text_input.cursor = self.text_input.get_cursor_from_index(pos)
        except Exception as e:
            log_error(f"Redo cursor error: {e}")
        self._undo_lock = False
        return True

    # ------------------------------------------------------------------ UI creation

    def _create_ui(self):
        self.layout = BoxLayout(orientation='horizontal', spacing=0)
        self._create_line_panel_scroll()
        self._create_code_input_scroll()
        theme = ThemeManager.get_theme()
        with self.layout.canvas.after:
            self.separator_color = Color(*theme.get('separator_color', (0.5, 0.5, 0.5, 0.3)))
            self.separator_line = Line(points=[0, 0, 0, 0], width=dp(0.5))
        self.layout.bind(pos=self._update_separator, size=self._update_separator)
        self.layout.add_widget(self.line_panel_scroll)
        self.layout.add_widget(self.editor_scroll)
        self.add_widget(self.layout)
        Clock.schedule_once(self._bind_scroll_sync, 0.1)

    def _create_line_panel_scroll(self):
        category = get_screen_category()
        if category == 'tablet':
            panel_width = dp(65)
        elif category == 'large_phone':
            panel_width = dp(55)
        else:
            panel_width = dp(45)
        self._panel_width = panel_width
        self.line_panel = VirtualLinePanel(
            on_fold_toggle=self._on_fold_toggle,
            size_hint=(None, 1),
            width=panel_width,
        )
        self.line_panel_scroll = BoxLayout(size_hint=(None, 1), width=panel_width)
        self.line_panel_scroll.add_widget(self.line_panel)

    def _create_code_input_scroll(self):
        theme = ThemeManager.get_theme()
        try:
            from pygments.lexers import PythonLexer
            from kivy.uix.codeinput import CodeInput
            has_lexer = HAS_PYGMENTS
        except:
            has_lexer = False
            CodeInput = None
        style_name = ThemeManager.get_syntax_style()
        self.current_syntax_style = style_name
        category = get_screen_category()
        if category == 'tablet':
            font_size = dp(16)
        elif category == 'large_phone':
            font_size = dp(14)
        else:
            font_size = dp(12)
        padding_top = 0
        padding_bottom = 0

        is_mobile = platform in ('android', 'ios')

        if has_lexer and CodeInput:
            # Используем стандартный CodeInput с включёнными ручками
            if is_mobile:
                self.text_input = CodeInput(
                    lexer=PythonLexer(),
                    style=style_name,
                    size_hint=(None, None),
                    font_size=font_size,
                    background_color=theme['editor_bg'],
                    foreground_color=theme['editor_text'],
                    cursor_color=theme['editor_cursor'],
                    selection_color=theme.get('editor_selection', (0.3, 0.5, 0.8, 0.4)),
                    multiline=True,
                    do_wrap=False,
                    padding=(dp(8), padding_top, dp(8), padding_bottom),
                    background_normal='',
                    background_active='',
                    use_bubble=False,
                    use_handles=True,
                    write_tab=False
                )
            else:
                self.text_input = CodeInput(
                    lexer=PythonLexer(),
                    style=style_name,
                    size_hint=(None, None),
                    font_size=font_size,
                    background_color=theme['editor_bg'],
                    foreground_color=theme['editor_text'],
                    cursor_color=theme['editor_cursor'],
                    selection_color=theme.get('editor_selection', (0.3, 0.5, 0.8, 0.4)),
                    multiline=True,
                    do_wrap=False,
                    padding=(dp(8), padding_top, dp(8), padding_bottom),
                    background_normal='',
                    background_active='',
                    use_bubble=False,
                    use_handles=True,
                    write_tab=False
                )
        else:
            # Без подсветки - используем TextInput с ручками
            self.text_input = TextInput(
                size_hint=(None, None),
                font_size=font_size,
                background_color=theme['editor_bg'],
                foreground_color=theme['editor_text'],
                cursor_color=theme['editor_cursor'],
                selection_color=theme.get('editor_selection', (0.3, 0.5, 0.8, 0.4)),
                multiline=True,
                do_wrap=False,
                padding=(dp(8), padding_top, dp(8), padding_bottom),
                background_normal='',
                background_active='',
                use_bubble=False,
                use_handles=True,
                write_tab=False
            )

        self._font_size = font_size
        self._padding_top = padding_top
        self._padding_bottom = padding_bottom
        self.text_input.bind(minimum_height=self.text_input.setter('height'))
        if hasattr(self.text_input, 'minimum_width'):
            self.text_input.bind(minimum_width=self.text_input.setter('width'))
        self.text_input.width = dp(400)
        scroll_bar_color = theme.get('scroll_bar_color', (0.4, 0.4, 0.4, 0.9))
        scroll_bar_inactive = theme.get('scroll_bar_inactive', (0.25, 0.25, 0.25, 0.6))
        self.editor_scroll = ScrollView(size_hint=(1, 1), do_scroll_x=True, do_scroll_y=True,
                                        scroll_type=['bars', 'content'], bar_width=dp(8), bar_color=scroll_bar_color,
                                        bar_inactive_color=scroll_bar_inactive, effect_cls='ScrollEffect',
                                        scroll_distance=dp(17), scroll_timeout=dp(33))

        self.editor_scroll.add_widget(self.text_input)
        self.text_input.bind(text=self._on_text_change)
        self.text_input.bind(focus=self._on_focus)
        self.text_input.bind(on_copy=self._on_copy)
        self._current_line_highlight = None
        self.text_input.bind(cursor=self._update_current_line_highlight)
        self._bind_auto_scroll()

    # ------------------------------------------------------------------ scroll sync

    def _bind_scroll_sync(self, *args):
        def sync_scroll(instance, value):
            # Панель строк обновляем ВСЕГДА (без throttle)
            self._refresh_virtual_panel()

            # Throttle только для направляющих (они тяжелые)
            now = time.time()
            if now - self._last_scroll_time < 0.066:
                return
            self._last_scroll_time = now
            Clock.unschedule(self._draw_indent_guides)
            Clock.schedule_once(self._draw_indent_guides, 0.1)

        self.editor_scroll.bind(scroll_y=sync_scroll)
        self.editor_scroll.bind(size=self._on_editor_scroll_resize)

    def _on_editor_scroll_resize(self, instance, new_size):
        """При изменении размера viewport (например, при скрытии клавиатуры)
        пересчитываем scroll_y так, чтобы верхняя видимая строка осталась на месте."""
        self._refresh_virtual_panel()

        # Если скролл заморожен — не трогаем, freeze/unfreeze сам разберётся
        if not getattr(instance, 'do_scroll_y', True):
            return

        try:
            lh = getattr(self.text_input, 'line_height', self._font_size * 1.2)
            total_lines = len(self.original_lines)
            total_h = total_lines * lh
            new_editor_h = new_size[1]
            new_max_offset = max(0, total_h - new_editor_h)
            if new_max_offset <= 0:
                return

            # Вычисляем какая строка сейчас наверху viewport
            old_editor_h = getattr(self, '_last_editor_h', new_editor_h)
            old_max_offset = max(0, total_h - old_editor_h)
            current_offset = (1.0 - instance.scroll_y) * old_max_offset

            # Выставляем scroll_y чтобы та же строка осталась сверху
            new_scroll_y = 1.0 - current_offset / new_max_offset
            instance.scroll_y = max(0.0, min(1.0, new_scroll_y))
        except Exception as e:
            log_error(f"_on_editor_scroll_resize error: {e}")
        finally:
            self._last_editor_h = new_size[1]

    def _get_display_to_orig(self):
        """Возвращает кешированный display_to_orig"""
        # Вычисляем текущую версию на основе состояния
        orig_lines = self._folding.get_orig_lines()
        folds = self._folding._folds
        current_version = (len(orig_lines), len(folds), id(orig_lines))

        # Если версия изменилась — перестраиваем
        if current_version != self._display_map_version:
            self._cached_display_to_orig = {}
            oi = 0
            di = 0
            n_orig = len(orig_lines)
            while oi < n_orig:
                self._cached_display_to_orig[di] = oi
                if oi in folds:
                    oi = folds[oi]['end'] + 1
                else:
                    oi += 1
                di += 1
            self._display_map_version = current_version

        return self._cached_display_to_orig

    def _refresh_virtual_panel(self, *args):
        if not hasattr(self, 'line_panel') or not isinstance(self.line_panel, VirtualLinePanel):
            return
        lh = getattr(self.text_input, 'line_height', self._font_size * 1.2)
        theme = ThemeManager.get_theme()
        scroll_y = getattr(self.editor_scroll, 'scroll_y', 1.0)
        editor_h = self.editor_scroll.height

        self.line_panel.update(
            line_count=len(self.original_lines),
            line_height=lh,
            font_size=self._font_size,
            theme=theme,
            scroll_y=scroll_y,
            editor_height=editor_h,
            fold_ranges=self._folding.get_fold_ranges(),
            folded_set=set(self._folding._folds.keys()),
            display_to_orig = self._get_display_to_orig(),
        )

    # ------------------------------------------------------------------ text change

    def _get_real_selection_text(self):
        try:
            ti = self.text_input
            if not ti.selection_text:
                return ti.selection_text

            if _FOLD_MARKER not in ti.selection_text:
                return ti.selection_text

            selected = ti.selection_text
            selected_lines = selected.split('\n')
            orig_lines = self._folding.get_orig_lines()
            folds = self._folding._folds

            result_lines = []

            for line in selected_lines:
                if _FOLD_MARKER in line:
                    if '▶' in line:
                        clean_header = line.split('▶')[0].strip()
                    else:
                        clean_header = line.split(_FOLD_MARKER)[0].strip()

                    clean_header = clean_header.rstrip(' .')

                    found_block = False
                    for i, orig_line in enumerate(orig_lines):
                        if orig_line.rstrip() == clean_header:
                            if i in folds:
                                fold_end = folds[i]['end']
                                block_lines = orig_lines[i:fold_end + 1]
                                result_lines.extend(block_lines)
                                found_block = True
                                break

                    if not found_block:
                        clean_stripped = clean_header.strip()
                        for i, orig_line in enumerate(orig_lines):
                            if orig_line.strip() == clean_stripped:
                                if i in folds:
                                    fold_end = folds[i]['end']
                                    block_lines = orig_lines[i:fold_end + 1]
                                    result_lines.extend(block_lines)
                                    found_block = True
                                    break

                    if not found_block:
                        result_lines.append(line)
                else:
                    result_lines.append(line)

            if result_lines:
                return '\n'.join(result_lines)
            else:
                return selected
        except Exception as e:
            log_error(f"_get_real_selection_text error: {e}")
            return self.text_input.selection_text

    def _on_copy(self, instance):
        try:
            real_text = self._get_real_selection_text()
            if real_text:
                from kivy.core.clipboard import Clipboard
                Clipboard.copy(real_text)
        except Exception as e:
            log_error(f"_on_copy error: {e}")

    def _on_text_change(self, instance, value):
        if self._ignore_text_change:
            return

        new_lines = value.split('\n')
        self.original_lines = new_lines
        self._display_map_version = 0
        self._folding.apply_display_edit(new_lines)
        new_line_count = len(new_lines)

        if not self._undo_lock:
            self._save_undo_state(immediate=False)

        app = App.get_running_app()
        if app and hasattr(app, 'autocomplete'):
            try:
                cursor_index = instance.cursor_index()
                before_cursor = value[:cursor_index]
                match = re.search(r'([a-zA-Z_]\w*)$', before_cursor)
                current_word = match.group(1) if match else ''
                app.autocomplete.show_suggestions(current_word)
            except:
                pass

        if new_line_count != self._cached_line_count:
            self._cached_line_count = new_line_count
            if not self._redraw_pending:
                self._redraw_pending = True
                Clock.schedule_once(self._delayed_update_panel, 0.05)
        else:
            # Only schedule a refresh if not already pending from _delayed_update_panel
            if not self._redraw_pending:
                self._refresh_virtual_panel()

        if self._text_width_ev:
            self._text_width_ev.cancel()
        self._text_width_ev = Clock.schedule_once(self._update_text_width, 0.3)

        if not self._indent_guides_pending:
            self._indent_guides_pending = True
            Clock.schedule_once(self._draw_indent_guides, 0.15)

        # НЕ добавляем пустые строки во время табуляции и сворачивания
        if not self._tab_indenting and not self._ensuring_trailing:
            # Отменяем предыдущий и планируем новый с задержкой
            Clock.unschedule(self._ensure_trailing)
            Clock.schedule_once(self._ensure_trailing, 0.3)

    def _save_undo_state(self, immediate=False):
        if self._undo_lock:
            return
        if immediate:
            self._do_save_undo_state()
        else:
            if self._undo_debounce_ev:
                self._undo_debounce_ev.cancel()
            self._undo_debounce_ev = Clock.schedule_once(
                lambda dt: self._do_save_undo_state(), 0.8
            )

    def _do_save_undo_state(self):
        if self._undo_lock:
            return
        try:
            current_text = self.text_input.text
            cursor = self.text_input.cursor_index()
        except:
            return
        if self._undo_stack and self._undo_stack[-1]['text'] == current_text:
            return
        self._undo_stack.append({'text': current_text, 'cursor': cursor})
        if len(self._undo_stack) > self._undo_max:
            self._undo_stack.pop(0)
        self._redo_stack.clear()

    def _ensure_trailing(self, dt):
        """Вызывает добавление пустых строк"""
        # Не запускаем если табуляция активна
        if self._tab_indenting or self._ensuring_trailing:
            return
        self._ensure_trailing_empty_lines()

    def _ensure_trailing_empty_lines(self):
        """Умное добавление пустых строк в конце для прокрутки над клавиатурой"""
        if self._ensuring_trailing:
            return
        if getattr(self, '_tab_indenting', False):
            return

        # Умный TARGET: меньше строк если клавиатура не видна
        if self._keyboard_visible:
            TARGET = 20  # достаточно для прокрутки над клавиатурой
        else:
            TARGET = 5  # минимальный запас когда клавиатуры нет

        if not self.original_lines:
            return

        # Находим последнюю непустую строку
        last_non_empty = -1
        for i in range(len(self.original_lines) - 1, -1, -1):
            if self.original_lines[i].strip() != '':
                last_non_empty = i
                break

        if last_non_empty == -1:
            return

        # Сколько пустых строк в конце
        trailing = len(self.original_lines) - last_non_empty - 1

        # Если уже достаточно, выходим
        if trailing >= TARGET:
            return

        self._ensuring_trailing = True
        try:
            # Сохраняем позицию курсора
            cursor_index = self.text_input.cursor_index()
            lines_to_add = TARGET - trailing

            # Добавляем строки
            self.text_input.unbind(text=self._on_text_change)
            self.text_input.text = self.text_input.text + '\n' * lines_to_add
            self.text_input.bind(text=self._on_text_change)

            # Обновляем внутреннее состояние
            self.original_lines = self.text_input.text.split('\n')

            # Восстанавливаем курсор (если он был в конце)
            try:
                if cursor_index <= len(self.text_input.text):
                    self.text_input.cursor = self.text_input.get_cursor_from_index(cursor_index)
            except:
                pass

        except Exception as e:
            log_error(f"_ensure_trailing_empty_lines error: {e}")
        finally:
            self._ensuring_trailing = False

    def _trim_trailing_lines(self, dt=None):
        """Обрезает лишние пустые строки когда клавиатура скрыта"""
        if self._ensuring_trailing:
            return
        if getattr(self, '_tab_indenting', False):
            return
        if not self.original_lines:
            return

        MAX_TRAILING_WHEN_HIDDEN = 3

        # Находим последнюю непустую строку
        last_non_empty = -1
        for i in range(len(self.original_lines) - 1, -1, -1):
            if self.original_lines[i].strip() != '':
                last_non_empty = i
                break

        if last_non_empty == -1:
            return

        trailing = len(self.original_lines) - last_non_empty - 1
        if trailing <= MAX_TRAILING_WHEN_HIDDEN:
            return

        self._ensuring_trailing = True

        # Сохраняем текущую позицию курсора
        cursor_index = self.text_input.cursor_index()

        # Сохраняем, какая строка сейчас вверху экрана (по пикселям)
        sv = self.editor_scroll
        lh = getattr(self.text_input, 'line_height', self._font_size * 1.2)
        total_lines_before = len(self.original_lines)
        total_h_before = total_lines_before * lh
        editor_h = sv.height
        max_offset_before = max(0, total_h_before - editor_h)
        current_offset = (1.0 - sv.scroll_y) * max_offset_before
        top_line_index = int(current_offset / lh) if lh > 0 else 0

        # Обрезаем строки
        try:
            lines = self.original_lines[:last_non_empty + MAX_TRAILING_WHEN_HIDDEN + 1]
            new_text = '\n'.join(lines)

            self.text_input.unbind(text=self._on_text_change)
            self.text_input.text = new_text
            self.text_input.bind(text=self._on_text_change)

            self.original_lines = new_text.split('\n')

            # Восстанавливаем курсор
            try:
                if cursor_index <= len(new_text):
                    self.text_input.cursor = self.text_input.get_cursor_from_index(cursor_index)
            except:
                pass

            # Пересчитываем scroll_y чтобы сохранить ту же строку вверху
            total_lines_after = len(self.original_lines)
            total_h_after = total_lines_after * lh
            max_offset_after = max(0, total_h_after - editor_h)

            # Позиция той же строки в новых координатах
            top_line_index = min(top_line_index, total_lines_after - 1)
            new_offset = top_line_index * lh

            if max_offset_after > 0:
                new_scroll_y = 1.0 - new_offset / max_offset_after
                new_scroll_y = max(0.0, min(1.0, new_scroll_y))
                sv.scroll_y = new_scroll_y
            else:
                sv.scroll_y = 1.0

        except Exception as e:
            log_error(f"_trim_trailing_lines error: {e}")
        finally:
            self._ensuring_trailing = False
            # Принудительно обновляем панель строк
            self._refresh_virtual_panel()
            # И ещё раз через кадр для синхронизации
            Clock.schedule_once(lambda dt: self._refresh_virtual_panel(), 0.05)
            Clock.schedule_once(lambda dt: self._refresh_virtual_panel(), 0.1)

    def _delayed_update_panel(self, dt):
        if self._panel_update_scheduled:
            return
        self._panel_update_scheduled = True
        try:
            self._refresh_virtual_panel()
        finally:
            self._panel_update_scheduled = False
        self._redraw_pending = False

    # ------------------------------------------------------------------ layout helpers

    def _update_separator(self, instance=None, value=None):
        if hasattr(self, 'separator_line') and hasattr(self, 'line_panel_scroll'):
            x = self.layout.x + self.line_panel_scroll.width
            y1 = self.layout.y
            y2 = self.layout.y + self.layout.height
            self.separator_line.points = [x, y1, x, y2]

    def _update_text_width(self, *args):
        if not self.original_lines:
            return
        n = len(self.original_lines)
        cached_n = getattr(self, '_cached_max_line_n', -1)
        if cached_n != n:
            # Line count changed — find new longest line
            max_len = max((len(line) for line in self.original_lines), default=0)
            self._cached_max_line_length = max_len
            self._cached_max_line_n = n
        else:
            max_len = getattr(self, '_cached_max_line_length', 0)
        char_width = self.text_input.font_size * 0.6
        min_width = dp(400)
        calculated_width = max(min_width, max_len * char_width + dp(33))
        new_width = min(calculated_width, dp(3333))
        if abs(self.text_input.width - new_width) > 1:
            self.text_input.width = new_width
            self._update_separator()

    def _force_line_panel_refresh(self, dt=None):
        self._refresh_virtual_panel()
        self._update_separator()

    # ------------------------------------------------------------------ keyboard

    def _on_window_keyboard(self, window, key, scancode, codepoint, modifier):
        if key == 27:
            self._keyboard_visible = False
        return False

    def _on_window_key_down(self, window, key, scancode, codepoint, modifier):
        if not self.text_input.focus:
            return False
        if key == 8:
            try:
                self._save_undo_state(immediate=True)
                cursor_index = self.text_input.cursor_index()
                if cursor_index == 0:
                    return False
                text = self.text_input.text
                space_count = 0
                pos = cursor_index - 1
                while pos >= 0 and text[pos] == ' ':
                    space_count += 1
                    pos -= 1
                if space_count == 0:
                    return False
                if space_count < 4:
                    delete_count = 1
                elif space_count == 4:
                    delete_count = 4
                else:
                    if space_count % 4 == 0:
                        delete_count = 4
                    else:
                        delete_count = 1
                delete_start = cursor_index - delete_count
                new_text = text[:delete_start] + text[cursor_index:]
                self.text_input.unbind(text=self._on_text_change)
                self.text_input.text = new_text
                self.text_input.bind(text=self._on_text_change)
                try:
                    self.text_input.cursor = self.text_input.get_cursor_from_index(delete_start)
                except:
                    pass
                self.original_lines = new_text.split('\n')
                self._folding.apply_display_edit(self.original_lines)
                self._refresh_virtual_panel()
                return True
            except Exception as e:
                log_error(f"Backspace error: {e}")
                return False
        return False

    def _on_key_down(self, instance, key, scancode, codepoint, modifier):
        # Автозакрытие скобок и кавычек
        if self._handle_auto_close(instance, codepoint):
            return True

        if key == 9:  # Tab
            try:
                if hasattr(instance, 'selection_text') and instance.selection_text:
                    start_idx, end_idx = instance.selection_from, instance.selection_to
                    if start_idx > end_idx:
                        start_idx, end_idx = end_idx, start_idx
                    text = instance.text
                    start_line = text[:start_idx].count('\n')
                    end_line = text[:end_idx].count('\n')

                    # Если выделение в одной строке — вставляем пробелы без прыжка
                    if start_line == end_line:
                        self._freeze_scroll()
                        instance.insert_text('    ')
                        # разморозка через кадр — после того как insert_text отработал
                        Clock.schedule_once(self._unfreeze_scroll, 0)
                        return True

                    self._save_undo_state(immediate=True)

                    lines = text.split('\n')
                    for i in range(start_line, end_line + 1):
                        if i < len(lines):
                            lines[i] = '    ' + lines[i]
                    new_text = '\n'.join(lines)
                    new_start = start_idx + 4
                    new_end = end_idx + 4 * (end_line - start_line + 1)

                    self._tab_indenting = True
                    self._ensuring_trailing = True
                    self._freeze_scroll()

                    instance.unbind(text=self._on_text_change)
                    instance.text = new_text
                    instance.bind(text=self._on_text_change)

                    self.original_lines = new_text.split('\n')
                    self._folding.apply_display_edit(self.original_lines)
                    self._refresh_virtual_panel()

                    def restore(dt):
                        try:
                            instance.focus = True
                            instance.select_text(new_start, new_end)
                            # select_text вызывает авто-скролл Kivy к позиции выделения,
                            # поэтому размораживаем ещё через кадр — уже после select_text
                            Clock.schedule_once(self._unfreeze_scroll, 0)
                        except Exception as e:
                            self._unfreeze_scroll()
                            log_error(f"restore selection error: {e}")
                        finally:
                            self._tab_indenting = False
                            self._ensuring_trailing = False

                    Clock.schedule_once(restore, 0)
                    return True

                # Нет выделения — одиночный таб
                self._freeze_scroll()
                instance.insert_text('    ')
                Clock.schedule_once(self._unfreeze_scroll, 0)
                return True
            except Exception as e:
                self._ensuring_trailing = False
                self._tab_indenting = False
                self._unfreeze_scroll()
                log_error(f"Tab handler error: {e}")
                return False
        return False

    # ------------------------------------------------------------------ auto-scroll on selection

    def _bind_auto_scroll(self):
        self.text_input.bind(on_touch_down=self._on_editor_touch_down)
        self.text_input.bind(on_touch_move=self._on_editor_touch_move)
        self.text_input.bind(on_touch_up=self._on_editor_touch_up)
        self.text_input.bind(cursor=self._on_cursor_for_scroll)

    def _on_editor_touch_down(self, instance, touch):
        """Запоминаем начало касания"""
        if instance.collide_point(*touch.pos):
            self._touch_start_time = time.time()
            self._is_selecting = False
            self._last_touch_pos = touch.pos
        return False

    def _on_editor_touch_move(self, instance, touch):
        """При движении запускаем автоскролл только если это не долгий тап"""
        # Если прошло больше 0.3 сек — это долгий тап, не запускаем автоскролл
        if time.time() - self._touch_start_time > 0.3:
            return False

        if not instance.collide_point(*touch.pos) or self._last_touch_pos is None:
            self._last_touch_pos = touch.pos
            self._is_selecting = True
            self._schedule_auto_scroll()
            return False

        self._last_touch_pos = touch.pos
        self._is_selecting = True
        self._schedule_auto_scroll()
        return False

    def _on_editor_touch_up(self, instance, touch):
        """Останавливаем автоскролл при отпускании"""
        self._is_selecting = False
        self._last_touch_pos = None
        self._stop_auto_scroll()
        return False

    def _on_cursor_for_scroll(self, instance, cursor_pos):
        if getattr(self, '_tab_indenting', False):
            return
        if not hasattr(instance, 'selection_text'):
            return
        if instance.selection_text:
            self._ensure_cursor_visible()

    def _ensure_cursor_visible(self):
        """Принудительно доскроллить до текущего курсора"""
        try:
            ti = self.text_input
            sv = self.editor_scroll

            cursor_col, cursor_row = ti.cursor
            lh = getattr(ti, 'line_height', self._font_size * 1.2)
            total_lines = len(self.original_lines)
            total_height = total_lines * lh
            editor_h = sv.height

            if total_height <= editor_h:
                return

            # Вертикаль
            line_top = cursor_row * lh
            line_bot = line_top + lh
            max_offset = total_height - editor_h
            cur_offset = (1.0 - sv.scroll_y) * max_offset
            margin = lh * 1.5

            if line_top < cur_offset + margin:
                new_offset = max(0, line_top - margin)
                sv.scroll_y = 1.0 - new_offset / max_offset
            elif line_bot > cur_offset + editor_h - margin:
                new_offset = min(max_offset, line_bot + margin - editor_h)
                sv.scroll_y = 1.0 - new_offset / max_offset

            # Горизонталь
            if not sv.do_scroll_x:
                return
            char_w = self._font_size * 0.6
            cursor_x = cursor_col * char_w + 8  # 8 = padding
            editor_w = sv.width
            total_w = ti.width
            if total_w <= editor_w:
                return

            max_x_offset = total_w - editor_w
            cur_x_offset = sv.scroll_x * max_x_offset
            h_margin = char_w * 5

            if cursor_x < cur_x_offset + h_margin:
                new_x = max(0, cursor_x - h_margin)
                sv.scroll_x = new_x / max_x_offset
            elif cursor_x > cur_x_offset + editor_w - h_margin:
                new_x = min(max_x_offset, cursor_x + h_margin - editor_w)
                sv.scroll_x = new_x / max_x_offset

        except Exception as e:
            from utils.debug_utils import log_error
            log_error(f"_ensure_cursor_visible error: {e}")

    def _schedule_auto_scroll(self):
        """Запускаем таймер автоскролла (или рестартуем)"""
        if self._auto_scroll_ev is None:
            from kivy.clock import Clock
            self._auto_scroll_ev = Clock.schedule_interval(self._do_auto_scroll, 1 / 30)

    def _stop_auto_scroll(self):
        """Останавливаем таймер автоскролла"""
        if self._auto_scroll_ev is not None:
            self._auto_scroll_ev.cancel()
            self._auto_scroll_ev = None

    def _do_auto_scroll(self, dt):
        """
        Вызывается 30 раз в секунду пока идёт выделение.
        Скролл следует за направлением движения пальца.
        """
        if not self._is_selecting or self._last_touch_pos is None:
            self._stop_auto_scroll()
            return

        try:
            from kivy.metrics import dp
            sv = self.editor_scroll
            touch_x, touch_y = self._last_touch_pos

            sv_x = sv.x
            sv_y = sv.y
            sv_w = sv.width
            sv_h = sv.height

            # Зона активации автоскролла у краёв
            dead = dp(40)
            # Максимальная скорость скролла
            max_speed_v = 0.02
            max_speed_h = 0.015

            scroll_dy = 0.0
            scroll_dx = 0.0

            # ---- Вертикаль ----
            # scroll_y = 1.0 (верх), scroll_y = 0.0 (низ)

            if touch_y < sv_y + dead:
                # Палец у ВЕРХНЕГО края — скроллим ВВЕРХ
                factor = min(1.0, (sv_y + dead - touch_y) / dead)
                scroll_dy = max_speed_v * factor
            elif touch_y > sv_y + sv_h - dead:
                # Палец у НИЖНЕГО края — скроллим ВНИЗ
                factor = min(1.0, (touch_y - (sv_y + sv_h - dead)) / dead)
                scroll_dy = -max_speed_v * factor

            # ---- Горизонталь ----
            if sv.do_scroll_x:
                if touch_x < sv_x + dead:
                    # Палец у ЛЕВОГО края — скроллим ВЛЕВО
                    factor = min(1.0, (sv_x + dead - touch_x) / dead)
                    scroll_dx = -max_speed_h * factor
                elif touch_x > sv_x + sv_w - dead:
                    # Палец у ПРАВОГО края — скроллим ВПРАВО
                    factor = min(1.0, (touch_x - (sv_x + sv_w - dead)) / dead)
                    scroll_dx = max_speed_h * factor

            # Применяем скролл
            if scroll_dy != 0:
                new_y = sv.scroll_y + scroll_dy
                sv.scroll_y = max(0.0, min(1.0, new_y))
            if scroll_dx != 0:
                new_x = sv.scroll_x + scroll_dx
                sv.scroll_x = max(0.0, min(1.0, new_x))

            # Синхронизируем панель номеров строк
            if scroll_dy != 0:
                self._refresh_virtual_panel()

        except Exception as e:
            from utils.debug_utils import log_error
            log_error(f"_do_auto_scroll error: {e}")
            self._stop_auto_scroll()

    # ------------------------------------------------------------------ focus

    def _on_focus(self, instance, focused):
        if focused:
            self._keyboard_visible = True
            self._freeze_scroll()
            Clock.schedule_once(lambda dt: self._show_keyboard(), 0.05)
            Clock.schedule_once(lambda dt: self._show_keyboard(), 0.15)
            # Добавляем пустые строки при появлении фокуса (клавиатуры),
            # размораживаем скролл уже после этого
            def _ensure_and_unfreeze(dt):
                self._ensure_trailing_empty_lines()
                self._unfreeze_scroll()
            Clock.schedule_once(_ensure_and_unfreeze, 0.3)
        else:
            self._keyboard_visible = False
            # Обрезаем лишние строки когда клавиатура скрыта
            #Clock.schedule_once(self._trim_trailing_lines, 0.1)

    def _show_keyboard(self, dt=None):
        try:
            if self.text_input and self.text_input.focus:
                if hasattr(self.text_input, 'show_keyboard'):
                    self.text_input.show_keyboard()
                if platform == 'android':
                    try:
                        from jnius import autoclass
                        PythonActivity = autoclass('org.kivy.android.PythonActivity')
                        activity = PythonActivity.mActivity
                        if activity:
                            # ADJUST_NOTHING — запрещаем системе двигать/ресайзить
                            # окно при появлении клавиатуры. Без этого Android
                            # делает adjustPan и поднимает всё приложение вверх.
                            # SOFT_INPUT_ADJUST_NOTHING = 0x00000030
                            activity.getWindow().setSoftInputMode(0x00000030)
                            InputMethodManager = autoclass('android.view.inputmethod.InputMethodManager')
                            Context = autoclass('android.content.Context')
                            imm = activity.getSystemService(Context.INPUT_METHOD_SERVICE)
                            imm.showSoftInput(activity.getCurrentFocus(), InputMethodManager.SHOW_FORCED)
                    except:
                        pass
        except Exception as e:
            log_error(f"Error showing keyboard: {e}")

    # ------------------------------------------------------------------ indent guides

    def _draw_indent_guides(self, *args):
        return
        self._indent_guides_pending = False
        if not hasattr(self, 'text_input') or not self.text_input:
            return
        if not self.original_lines:
            return

        ti = self.text_input
        total_lines = len(self.original_lines)
        lh = ti.line_height if hasattr(ti, 'line_height') else self._font_size * 1.2
        char_width = self._font_size * 0.6
        left_padding = dp(8)

        # Удаляем старые линии
        for guide in self._indent_guides:
            try:
                ti.canvas.after.remove(guide)
            except:
                pass
        self._indent_guides = []

        # Вычисляем видимую область
        scroll_y = 1.0
        parent = ti.parent
        while parent:
            if isinstance(parent, ScrollView):
                scroll_y = parent.scroll_y
                break
            parent = parent.parent

        editor_height = ti.parent.height if ti.parent else 800
        visible_lines_count = int(editor_height / lh) + 1
        first_visible = max(0, int((1.0 - scroll_y) * total_lines))
        first_line = max(0, first_visible - 50)
        last_line = min(total_lines, first_visible + visible_lines_count + 50)

        theme = ThemeManager.get_theme()
        guide_color = theme.get('indent_guide_color', (0.35, 0.38, 0.40, 0.30))

        # Создаём отдельные линии для каждой направляющей
        for line_idx in range(first_line, last_line):
            if line_idx >= total_lines:
                break
            line_text = self.original_lines[line_idx]
            indent = len(line_text) - len(line_text.lstrip(' '))
            if indent < 4:
                continue
            num_guides = indent // 4
            line_y = ti.y + ti.height - (line_idx + 1) * lh
            pad = lh * 0.2
            y_start = line_y + pad
            y_end = line_y + lh - pad
            for g in range(1, num_guides + 1):
                x_pos = ti.x + left_padding + (g * 4) * char_width
                with ti.canvas.after:
                    Color(*guide_color)
                    line = Line(points=[x_pos, y_start, x_pos, y_end], width=dp(0.3))
                    self._indent_guides.append(line)

    # ------------------------------------------------------------------ current line highlight

    def _update_current_line_highlight(self, instance, cursor_pos):
        if not hasattr(self, 'text_input') or not self.text_input:
            return

        # Debounce: отменяем предыдущий вызов
        if self._highlight_timer:
            self._highlight_timer.cancel()

        # Планируем через 0.05 сек
        self._highlight_timer = Clock.schedule_once(
            lambda dt: self._do_update_current_line_highlight(), 0.05
        )

    def _do_update_current_line_highlight(self):
        if not hasattr(self, 'text_input') or not self.text_input:
            return
        if self._current_line_highlight:
            try:
                self.text_input.canvas.after.remove(self._current_line_highlight)
            except:
                pass
            self._current_line_highlight = None
        try:
            cursor_index = self.text_input.cursor_index()
            current_line_num = self.text_input.text[:cursor_index].count('\n')
            lh = self.text_input.line_height if hasattr(self.text_input, 'line_height') else self._font_size * 1.2
            x = self.text_input.x
            y = self.text_input.y + self.text_input.height - (current_line_num + 1) * lh
            theme = ThemeManager.get_theme()
            highlight_color = theme.get('current_line_highlight', (1, 1, 1, 0.04))
            with self.text_input.canvas.after:
                Color(*highlight_color)
                self._current_line_highlight = Rectangle(pos=(x, y), size=(self.text_input.width, lh))
        except:
            pass

    # ------------------------------------------------------------------ cleanup

    def _update_line_panel(self, *args):
        self._refresh_virtual_panel()

    def cleanup(self):
        ThemeManager.unregister(self)
        if hasattr(self, '_undo_stack'):
            self._undo_stack.clear()
        if hasattr(self, '_redo_stack'):
            self._redo_stack.clear()
        Window.unbind(on_keyboard=self._on_window_keyboard)
        Window.unbind(on_key_down=self._on_window_key_down)
        self._stop_auto_scroll()

    def _sync_scroll_position(self, dt=None):
        """Принудительная синхронизация скролла после операций"""
        if hasattr(self, 'editor_scroll') and hasattr(self, '_target_scroll_y'):
            self.editor_scroll.scroll_y = self._target_scroll_y
            if hasattr(self, '_target_scroll_x'):
                self.editor_scroll.scroll_x = self._target_scroll_x
            self._refresh_virtual_panel()

    def debug_folding(self):
        print("=== FOLDING DEBUG ===")
        print(f"Original lines count: {len(self._folding.get_orig_lines())}")
        print(f"Display lines count: {len(self._folding.get_display_lines())}")
        print(f"Folds: {self._folding._folds}")
        print(f"Fold ranges: {self._folding.get_fold_ranges()}")
        print("===================")
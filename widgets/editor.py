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
from core.themes import ThemeManager, HAS_PYGMENTS

# Try to import pygments lexer
if HAS_PYGMENTS:
    from pygments.lexers import PythonLexer

# Маркер свёрнутого блока — уникальный, не встречается в обычном коде
_FOLD_MARKER = '\u25B6'  # ▶


def _get_fold_ranges(lines):
    """Улучшенная версия с защитой от строк с маркерами"""
    ranges = []
    n = len(lines)
    i = 0
    while i < n:
        line = lines[i]
        stripped = line.rstrip()
        if not stripped or _FOLD_MARKER in line or '▶' in line:
            i += 1
            continue

        indent = len(line) - len(line.lstrip())
        lstripped = line.lstrip()

        if stripped.endswith(':') and not lstripped.startswith('#'):
            block_end = i
            j = i + 1
            while j < n:
                jline = lines[j]
                jstripped = jline.strip()
                if not jstripped:
                    j += 1
                    continue
                jindent = len(jline) - len(jline.lstrip())
                if jindent > indent:
                    block_end = j
                    j += 1
                else:
                    break
            if block_end > i:
                ranges.append((i, block_end))
            i += 1
        else:
            i += 1
    return ranges


class FoldingManager:
    """Управляет свёрнутыми блоками.

    Хранит оригинальный текст со всеми строками.
    При сворачивании/разворачивании пересчитывает «отображаемый» текст.

    Структура _folds: { display_line_index: {'orig_start', 'orig_end', 'orig_lines'} }
    """

    def __init__(self):
        self._orig_lines = []   # полный оригинал (список строк)
        self._folds = {}        # {orig_start_line: {'end': orig_end, 'lines': [...]}}
        self._fold_ranges = []  # [(start, end), ...] — все доступные блоки

    def set_lines(self, lines):
        """Вызывается при изменении текста. Сбрасывает все сворачивания."""
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
                count = self._folds[i]['end'] - i  # количество скрытых строк
                # Добавляем три точки ... и информацию
                result.append(header.rstrip() + f'  ... ▶ {count} lines folded')
                i = self._folds[i]['end'] + 1
            else:
                result.append(self._orig_lines[i])
                i += 1
        return result

    def is_foldable(self, orig_line):
        """Есть ли на этой строке (в оригинале) сворачиваемый блок."""
        return any(s == orig_line for s, e in self._fold_ranges)

    def get_fold_ranges(self):
        return self._fold_ranges

    def is_folded(self, orig_line):
        return orig_line in self._folds

    def fold(self, orig_line):
        """Свернуть блок, начинающийся с orig_line."""
        for s, e in self._fold_ranges:
            if s == orig_line and orig_line not in self._folds:
                hidden = self._orig_lines[s + 1: e + 1]
                self._folds[s] = {'end': e, 'lines': hidden}
                return True
        return False

    def unfold(self, orig_line):
        """Развернуть блок."""
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
        """Перевод номера отображаемой строки в номер оригинальной."""
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
        """Перевод номера оригинальной строки в номер отображаемой."""
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
        """Вызывается когда пользователь отредактировал текст напрямую."""
        if not new_display_lines:
            self._orig_lines = []
            self._folds = {}
            self._fold_ranges = []
            return

        old_folds = self._folds.copy()
        old_orig_lines = self._orig_lines.copy()

        # === Основная идея: восстанавливаем оригинальные строки ===
        new_orig = []
        i = 0
        while i < len(new_display_lines):
            line = new_display_lines[i]

            if _FOLD_MARKER in line or '▶' in line:  # это свёрнутый блок
                # Ищем соответствующий старый folded блок
                found = False
                for start, fold_data in old_folds.items():
                    old_header = old_orig_lines[start].rstrip()
                    # Пытаемся сопоставить заголовок
                    if (old_header in line or
                            line.rstrip().startswith(old_header.rstrip()) or
                            old_header.startswith(line.split('...')[0].strip())):
                        # Восстанавливаем весь блок из старого оригинала
                        end = fold_data['end']
                        new_orig.extend(old_orig_lines[start:end + 1])
                        i += 1
                        found = True
                        break

                if not found:
                    # Не смогли восстановить — вставляем как обычную строку
                    new_orig.append(line)
                    i += 1
            else:
                new_orig.append(line)
                i += 1

        # Обновляем состояние
        self._orig_lines = new_orig
        self._folds = {}  # временно сбрасываем

        # Пересчитываем возможные диапазоны сворачивания
        self._fold_ranges = _get_fold_ranges(self._orig_lines)

        # Восстанавливаем сворачивания там, где заголовки совпадают
        for start, fold_data in old_folds.items():
            if start < len(self._orig_lines):
                old_header = old_orig_lines[start].rstrip()
                new_header = self._orig_lines[start].rstrip()

                if (old_header == new_header or
                        old_header.startswith(new_header) or
                        new_header.startswith(old_header.split(':')[0] if ':' in old_header else old_header)):

                    # Проверяем, что блок всё ещё существует
                    for s, e in self._fold_ranges:
                        if s == start:
                            self._folds[start] = {
                                'end': e,
                                'lines': self._orig_lines[s + 1:e + 1]
                            }
                            break


class VirtualLinePanel(Widget):
    """Панель номеров строк + кнопки сворачивания на Canvas.
    Рисует только видимые строки, касания обрабатывает напрямую."""

    def __init__(self, on_fold_toggle=None, **kwargs):
        super().__init__(**kwargs)
        self._line_count = 0
        self._line_height = 16
        self._font_size = 12
        self._theme = {}
        self._scroll_y = 1.0
        self._editor_height = 0
        self._redraw_ev = None
        self._fold_ranges = []      # [(start, end), ...] оригинальные диапазоны
        self._folded_set = set()    # {orig_line, ...} свёрнутые заголовки
        self._display_to_orig = {}  # {display_i: orig_i} — для хит-теста
        self._on_fold_toggle = on_fold_toggle  # callback(orig_line)
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

        # Набор orig-строк с foldable блоками (для быстрого поиска)
        foldable_orig = {s for s, e in self._fold_ranges}

        from kivy.core.text import Label as CoreLabel

        with self.canvas:
            Color(*bg_color)
            Rectangle(pos=self.pos, size=self.size)

            btn_size = min(lh * 0.55, dp(13))
            btn_margin_right = dp(3)   # отступ кнопки от правого края панели
            num_pad_right = btn_size + btn_margin_right * 2 + dp(2)  # цифры левее кнопки

            for di in range(first_visible, last_visible):
                orig_i = self._display_to_orig.get(di, di)
                y = self.y + self.height - (di + 1) * lh + scroll_offset
                if y + lh < self.y or y > self.y + self.height:
                    continue

                is_foldable = orig_i in foldable_orig
                is_folded = orig_i in self._folded_set

                # ── Номер строки — выровнен правее середины, левее кнопки ──
                Color(*text_color)
                num_text = str(orig_i + 1)
                lbl = CoreLabel(text=num_text, font_size=self._font_size,
                                halign='right', valign='middle')
                lbl.refresh()
                tex = lbl.texture
                if tex:
                    tw, th = tex.size
                    tx = self.x + panel_width - num_pad_right - tw
                    ty = y + (lh - th) / 2
                    Rectangle(texture=tex, pos=(tx, ty), size=(tw, th))

                # ── Кнопка свернуть/развернуть — крайняя правая ──
                if is_foldable:
                    btn_x = self.x + panel_width - btn_size - btn_margin_right
                    btn_y = y + (lh - btn_size) / 2
                    if is_folded:
                        Color(*folded_bg)
                        RoundedRectangle(pos=(btn_x, btn_y), size=(btn_size, btn_size),
                                         radius=[dp(2)])
                    Color(*fold_color)
                    arrow = '▶' if is_folded else '▼'
                    albl = CoreLabel(text=arrow, font_name='SourceBold', font_size=btn_size * 0.85,
                                     halign='center', valign='middle')
                    albl.refresh()
                    atex = albl.texture
                    if atex:
                        aw, ah = atex.size
                        ax = btn_x + (btn_size - aw) / 2
                        ay = btn_y + (btn_size - ah) / 2
                        Rectangle(texture=atex, pos=(ax, ay), size=(aw, ah))

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

        # Определяем строку по Y касания
        rel_y = self.y + self.height - touch.y + scroll_offset
        di = int(rel_y / lh)
        if 0 <= di < n:
            orig_i = self._display_to_orig.get(di, di)
            if orig_i in foldable_orig:
                # Кнопка — правый край панели
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
        self._undo_max = 200
        self._undo_lock = False
        self._redraw_pending = False
        self._indent_guides_pending = False

        # Throttle
        self._panel_update_scheduled = False
        self._cached_line_count = 0
        self._cached_max_line_length = 0
        self._text_width_ev = None
        self._width_cache = {}

        # Сворачивание блоков
        self._folding = FoldingManager()
        self._ignore_text_change = False  # при fold/unfold не пересчитываем оригинал

        self._create_ui()
        self.apply_theme(ThemeManager.get_theme())
        Window.bind(on_keyboard=self._on_window_keyboard)
        self.text_input.bind(on_key_down=self._on_key_down)
        self.text_input.bind(font_name=self._on_font_changed)
        Window.bind(on_key_down=self._on_window_key_down)

        self._scroll_timer = None
        self._last_cursor_pos = None

    # ------------------------------------------------------------------ folding

    def _on_fold_toggle(self, orig_line):
        """Вызывается при тапе по кнопке ▶/▼ в панели."""
        try:
            self._folding.toggle(orig_line)
            self._apply_folding_to_editor(toggled_orig_line=orig_line)

            self.debug_folding()

        except Exception as e:
            log_error(f"fold toggle error: {e}")

    def _apply_folding_to_editor(self, toggled_orig_line=None):
        """Обновляет текст в text_input согласно текущему состоянию сворачивания.
        toggled_orig_line — оригинальная строка только что свёрнутого/развёрнутого блока.
        Курсор фиксируется на строке заголовка этого блока."""
        try:
            # Запоминаем текущую display-строку курсора до изменений
            try:
                old_cursor_idx = self.text_input.cursor_index()
                old_display_line = self.text_input.text[:old_cursor_idx].count('\n')
            except:
                old_cursor_idx = 0
                old_display_line = 0

            display_lines = self._folding.get_display_lines()
            new_text = '\n'.join(display_lines)

            self._ignore_text_change = True
            self.text_input.text = new_text
            self.original_lines = display_lines
            self._ignore_text_change = False

            # Определяем display-строку, на которой должен оказаться курсор.
            # Приоритет: строка только что свёрнутого/развёрнутого блока.
            if toggled_orig_line is not None:
                target_display_line = self._folding.orig_to_display(toggled_orig_line)
            else:
                # Сохраняем ту же display-строку, что была (она не сдвигается
                # при fold выше курсора; при fold ниже — вообще не меняется)
                target_display_line = old_display_line

            # Переводим номер display-строки в символьный индекс (начало строки)
            try:
                lines_before = display_lines[:target_display_line]
                char_pos = sum(len(l) + 1 for l in lines_before)
                char_pos = min(char_pos, len(new_text))
                self.text_input.cursor = self.text_input.get_cursor_from_index(char_pos)
                # Прокручиваем к строке заголовка
                Clock.schedule_once(lambda dt: self._scroll_to_display_line(target_display_line), 0.05)
            except:
                pass

            self._refresh_virtual_panel()
            Clock.schedule_once(self._draw_indent_guides, 0.15)
        except Exception as e:
            log_error(f"_apply_folding_to_editor error: {e}")

    def _scroll_to_display_line(self, display_line):
        """Прокручивает редактор так, чтобы display_line была видна."""
        try:
            lh = getattr(self.text_input, 'line_height', self._font_size * 1.2)
            total_lines = len(self.original_lines)
            total_height = total_lines * lh
            editor_h = self.editor_scroll.height
            if total_height <= editor_h:
                return  # всё помещается — скролл не нужен
            # Y верха целевой строки (от верха документа)
            line_top = display_line * lh
            line_bot = line_top + lh
            # Текущий viewport
            scroll_y = self.editor_scroll.scroll_y
            max_offset = total_height - editor_h
            current_top = (1.0 - scroll_y) * max_offset
            current_bot = current_top + editor_h
            # Если строка уже видна — ничего не делаем
            margin = lh * 2
            if line_top >= current_top + margin and line_bot <= current_bot - margin:
                return
            # Центрируем строку в viewport
            desired_top = line_top - editor_h / 2 + lh / 2
            desired_top = max(0, min(desired_top, max_offset))
            new_scroll_y = 1.0 - desired_top / max_offset
            self.editor_scroll.scroll_y = max(0.0, min(1.0, new_scroll_y))
        except Exception as e:
            log_error(f"_scroll_to_display_line error: {e}")

    def fold_line(self, line_num):
        """Публичный API: свернуть блок на строке line_num (0-based, display)."""
        orig = self._folding.display_to_orig(line_num)
        if self._folding.fold(orig):
            self._apply_folding_to_editor()

    def unfold_line(self, line_num):
        """Публичный API: развернуть блок на строке line_num (0-based, display)."""
        orig = self._folding.display_to_orig(line_num)
        if self._folding.unfold(orig):
            self._apply_folding_to_editor()

    def fold_all(self):
        """Свернуть все блоки верхнего уровня."""
        for s, e in self._folding.get_fold_ranges():
            self._folding.fold(s)
        self._apply_folding_to_editor()

    def unfold_all(self):
        """Развернуть все блоки."""
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
        """Пересоздаём виртуальную панель."""
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
        # panel_bg рисуется в VirtualLinePanel.canvas
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
                    chunk_size = 5000
                    for i in range(0, len(current_text), chunk_size):
                        self.text_input.text += current_text[i:i + chunk_size]

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
        """Возвращает полный текст (с развёрнутыми блоками)."""
        orig = self._folding.get_orig_lines()
        if orig:
            return '\n'.join(orig)
        return self.text_input.text if hasattr(self, 'text_input') else ""

    def set_text(self, text):
        if hasattr(self, 'text_input'):
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
        except:
            pass
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
        except:
            pass
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
        if has_lexer and CodeInput:
            self.text_input = CodeInput(
                lexer=PythonLexer(),
                style=style_name,
                size_hint=(None, None),
                font_size=font_size,
                background_color=theme['editor_bg'],
                foreground_color=theme['editor_text'],
                cursor_color=theme['editor_cursor'],
                selection_color=theme.get('editor_selection', (1, 1, 1, 0.1)),
                multiline=True,
                do_wrap=False,
                padding=(dp(8), padding_top, dp(8), padding_bottom),
                background_normal='',
                background_active='',

                # === Отключение контекстного меню и ручек выделения ===
                use_bubble=False,  # главное — отключает всплывающее меню
                use_handles=False,  # убирает ручки выделения
                write_tab = False
            )
        else:
            self.text_input = TextInput(
                size_hint=(None, None),
                font_size=font_size,
                background_color=theme['editor_bg'],
                foreground_color=theme['editor_text'],
                cursor_color=theme['editor_cursor'],
                selection_color=theme.get('editor_selection', (1, 1, 1, 0.1)),
                multiline=True,
                do_wrap=False,
                padding=(dp(8), padding_top, dp(8), padding_bottom),
                background_normal='',
                background_active='',

                # === Отключение контекстного меню и ручек выделения ===
                use_bubble=False,
                use_handles=False,
                write_tab = False
            )
        # Принудительно отключаем контекстное меню
        self.text_input.use_bubble = False
        self.text_input.use_handles = False

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
        self.text_input.bind(on_touch_move=self._on_touch_move)
        self.editor_scroll.add_widget(self.text_input)
        self.text_input.bind(text=self._on_text_change)
        self.text_input.bind(focus=self._on_focus)
        self.text_input.bind(on_touch_down=self._on_touch_down)
        self.text_input.bind(on_copy=self._on_copy)
        self._current_line_highlight = None
        self.text_input.bind(cursor=self._update_current_line_highlight)

    # ------------------------------------------------------------------ scroll sync

    def _bind_scroll_sync(self, *args):
        def sync_scroll(instance, value):
            self._refresh_virtual_panel()
            Clock.unschedule(self._draw_indent_guides)
            Clock.schedule_once(self._draw_indent_guides, 0.1)

        self.editor_scroll.bind(scroll_y=sync_scroll)
        self.editor_scroll.bind(size=lambda *a: self._refresh_virtual_panel())

    def _refresh_virtual_panel(self, *args):
        """Обновляет VirtualLinePanel без создания виджетов."""
        if not hasattr(self, 'line_panel') or not isinstance(self.line_panel, VirtualLinePanel):
            return
        lh = getattr(self.text_input, 'line_height', self._font_size * 1.2)
        theme = ThemeManager.get_theme()
        scroll_y = getattr(self.editor_scroll, 'scroll_y', 1.0)
        editor_h = self.editor_scroll.height

        # Строим mapping display → orig
        display_to_orig = {}
        oi = 0
        di = 0
        orig_lines = self._folding.get_orig_lines()
        folds = self._folding._folds
        n_orig = len(orig_lines)
        while oi < n_orig:
            display_to_orig[di] = oi
            if oi in folds:
                oi = folds[oi]['end'] + 1
            else:
                oi += 1
            di += 1

        self.line_panel.update(
            line_count=len(self.original_lines),
            line_height=lh,
            font_size=self._font_size,
            theme=theme,
            scroll_y=scroll_y,
            editor_height=editor_h,
            fold_ranges=self._folding.get_fold_ranges(),
            folded_set=set(self._folding._folds.keys()),
            display_to_orig=display_to_orig,
        )

    # ------------------------------------------------------------------ text change

    # ------------------------------------------------------------------ copy with folded content

    def _get_real_selection_text(self):
        """Возвращает текст выделения с развёрнутым содержимым свёрнутых блоков."""
        try:
            ti = self.text_input
            print(f"[DEBUG] _get_real_selection_text called")

            if not ti.selection_text:
                return ti.selection_text

            # Проверяем, есть ли в выделении маркер свёрнутого блока
            if _FOLD_MARKER not in ti.selection_text:
                return ti.selection_text

            print("[DEBUG] Fold marker found, processing...")

            # Получаем выделенный текст
            selected = ti.selection_text
            selected_lines = selected.split('\n')

            # Получаем все оригинальные строки
            orig_lines = self._folding.get_orig_lines()
            folds = self._folding._folds

            result_lines = []

            # Проходим по каждой строке выделения
            for line in selected_lines:
                if _FOLD_MARKER in line:
                    # Очищаем строку от маркеров сворачивания
                    # Убираем всё после ▶ (включая пробелы и точки)
                    if '▶' in line:
                        # Берём часть до ▶
                        clean_header = line.split('▶')[0].strip()
                    else:
                        clean_header = line.split(_FOLD_MARKER)[0].strip()

                    # Убираем три точки и пробелы в конце
                    clean_header = clean_header.rstrip(' .')
                    print(f"[DEBUG] Original line: '{line}'")
                    print(f"[DEBUG] Clean header: '{clean_header}'")

                    # Ищем этот заголовок в оригинальных строках
                    found_block = False
                    for i, orig_line in enumerate(orig_lines):
                        # Сравниваем очищенные строки
                        if orig_line.rstrip() == clean_header:
                            print(f"[DEBUG] Found exact match at index {i}")
                            if i in folds:
                                fold_end = folds[i]['end']
                                block_lines = orig_lines[i:fold_end + 1]
                                result_lines.extend(block_lines)
                                found_block = True
                                break

                    if not found_block:
                        # Пробуем найти без учета отступов
                        clean_stripped = clean_header.strip()
                        for i, orig_line in enumerate(orig_lines):
                            if orig_line.strip() == clean_stripped:
                                print(f"[DEBUG] Found stripped match at index {i}")
                                if i in folds:
                                    fold_end = folds[i]['end']
                                    block_lines = orig_lines[i:fold_end + 1]
                                    result_lines.extend(block_lines)
                                    found_block = True
                                    break

                    if not found_block:
                        # Если всё равно не нашли, пробуем найти по началу строки
                        for i, orig_line in enumerate(orig_lines):
                            if orig_line.startswith(clean_stripped.split()[0] if clean_stripped else ''):
                                print(f"[DEBUG] Found partial match at index {i}: '{orig_line}'")
                                if i in folds:
                                    fold_end = folds[i]['end']
                                    block_lines = orig_lines[i:fold_end + 1]
                                    result_lines.extend(block_lines)
                                    found_block = True
                                    break

                    if not found_block:
                        print(f"[DEBUG] No block found for: '{clean_header}'")
                        result_lines.append(line)
                else:
                    result_lines.append(line)

            if result_lines:
                result = '\n'.join(result_lines)
                print(f"[DEBUG] Result length: {len(result)}")
                print(f"[DEBUG] Result preview: {result[:200]}")
                return result
            else:
                return selected

        except Exception as e:
            log_error(f"_get_real_selection_text error: {e}")
            import traceback
            traceback.print_exc()
            return self.text_input.selection_text

    def _on_copy(self, instance):
        """Перехватываем Ctrl+C / команду Copy: кладём в буфер развёрнутый текст."""
        try:
            print("[DEBUG] _on_copy called!")  # ← ДОБАВИТЬ
            print(f"[DEBUG] Selection text: '{self.text_input.selection_text}'")  # ← ДОБАВИТЬ

            real_text = self._get_real_selection_text()
            print(f"[DEBUG] Real text length: {len(real_text)}")  # ← ДОБАВИТЬ
            print(f"[DEBUG] Real text first 100 chars: '{real_text[:100]}'")  # ← ДОБАВИТЬ

            if real_text:
                from kivy.core.clipboard import Clipboard
                Clipboard.copy(real_text)
                print("[DEBUG] Copied to clipboard!")  # ← ДОБАВИТЬ
            else:
                print("[DEBUG] No real text to copy!")  # ← ДОБАВИТЬ
        except Exception as e:
            log_error(f"_on_copy error: {e}")
            print(f"[DEBUG] Exception in _on_copy: {e}")  # ← ДОБАВИТЬ

    def _on_text_change(self, instance, value):
        if self._ignore_text_change:
            return

        old_cursor = instance.cursor_index() if hasattr(instance, 'cursor_index') else 0
        old_line_count = len(self.original_lines) if self.original_lines else 0

        new_lines = value.split('\n')
        self.original_lines = new_lines

        # Проверяем, было ли изменение в строке-заглушке
        was_fold_line = False
        for line in new_lines:
            if _FOLD_MARKER in line:
                was_fold_line = True
                break

        if was_fold_line and old_line_count > 0:
            # Пользователь редактирует свёрнутый блок
            # Нужно сохранить состояние до редактирования
            print("[DEBUG] Editing a folded line - preserving fold state")

        # Синхронизируем FoldingManager с реальным редактированием
        self._folding.apply_display_edit(new_lines)

        new_line_count = len(new_lines)

        if not self._undo_lock and hasattr(self, '_undo_stack'):
            text_len = len(value)
            if text_len > 50000:
                max_states = 20
                save_every = 5
            elif text_len > 10000:
                max_states = 50
                save_every = 2
            else:
                max_states = self._undo_max
                save_every = 1
            if not hasattr(self, '_undo_counter'):
                self._undo_counter = 0
            self._undo_counter += 1
            if self._undo_counter % save_every == 0:
                prev_text = '\n'.join(new_lines)
                if not self._undo_stack or self._undo_stack[-1]['text'] != value:
                    self._undo_stack.append({
                        'text': prev_text,
                        'cursor': instance.cursor_index() if hasattr(instance, 'cursor_index') else 0,
                    })
                    while len(self._undo_stack) > max_states:
                        self._undo_stack.pop(0)
                    self._redo_stack.clear()

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
            self._refresh_virtual_panel()

        # Дебаунс на обновление ширины
        if self._text_width_ev:
            self._text_width_ev.cancel()
        self._text_width_ev = Clock.schedule_once(self._update_text_width, 0.3)

        if not self._indent_guides_pending:
            self._indent_guides_pending = True
            Clock.schedule_once(self._draw_indent_guides, 0.15)

        Clock.unschedule(self._ensure_trailing)
        Clock.schedule_once(self._ensure_trailing, 0)

    def _ensure_trailing(self, dt):
        self._ensure_trailing_empty_lines()

    def _ensure_trailing_empty_lines(self):
        if self._ensuring_trailing:
            return
        TARGET = 45
        if not self.original_lines:
            return

        last_non_empty = -1
        for i in range(len(self.original_lines) - 1, -1, -1):
            if self.original_lines[i].strip() != '':
                last_non_empty = i
                break

        if last_non_empty == -1:
            return

        trailing = len(self.original_lines) - last_non_empty - 1
        if trailing >= TARGET:
            return

        self._ensuring_trailing = True
        try:
            cursor_index = self.text_input.cursor_index()
            lines_to_add = TARGET - trailing
            current_text = self.text_input.text
            self.text_input.text = current_text + '\n' * lines_to_add
            self.original_lines = self.text_input.text.split('\n')
            safe_cursor = min(cursor_index, len(self.text_input.text))

            def restore_cursor(dt):
                try:
                    self.text_input.cursor = self.text_input.get_cursor_from_index(safe_cursor)
                except:
                    pass

            Clock.schedule_once(restore_cursor, 0.05)
        finally:
            def reset_flag(dt):
                self._ensuring_trailing = False

            Clock.schedule_once(reset_flag, 0.3)

    def _delayed_update_panel(self, dt):
        """Throttle для обновления панели."""
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

    def _update_panel_bg(self, instance, value):
        """Фон теперь в VirtualLinePanel.canvas."""
        pass

    def _update_text_width(self, *args):
        if not self.original_lines:
            return
        n = len(self.original_lines)
        cached = getattr(self, '_cached_max_line_length', 0)
        cached_n = getattr(self, '_cached_max_line_n', -1)
        if cached_n != n:
            cached = max((len(line) for line in self.original_lines), default=0)
            self._cached_max_line_length = cached
            self._cached_max_line_n = n
        max_line_length = cached
        char_width = self.text_input.font_size * 0.6
        min_width = dp(400)
        calculated_width = max(min_width, max_line_length * char_width + dp(33))
        new_width = min(calculated_width, dp(3333))
        if abs(self.text_input.width - new_width) > 1:
            self.text_input.width = new_width
            self._update_separator()

    def _update_line_panel(self, *args):
        """Обратная совместимость — делегирует в _refresh_virtual_panel."""
        self._refresh_virtual_panel()

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
        if key == 9:
            try:
                if hasattr(instance, 'selection_text') and instance.selection_text:
                    start_idx, end_idx = instance.selection_from, instance.selection_to
                    if start_idx > end_idx:
                        start_idx, end_idx = end_idx, start_idx
                    text = instance.text
                    start_line = text[:start_idx].count('\n')
                    end_line = text[:end_idx].count('\n')
                    if start_line == end_line:
                        instance.insert_text('    ')
                        return True
                    lines = text.split('\n')
                    for i in range(start_line, end_line + 1):
                        if i < len(lines):
                            lines[i] = '    ' + lines[i]
                    new_text = '\n'.join(lines)
                    new_start = start_idx + 4
                    new_end = end_idx + 4 * (end_line - start_line + 1)
                    self._ensuring_trailing = True
                    instance.text = new_text
                    if hasattr(self, 'original_lines'):
                        self.original_lines = new_text.split('\n')
                        self._folding.apply_display_edit(self.original_lines)
                        self._refresh_virtual_panel()

                    def restore(dt):
                        try:
                            instance.focus = True
                            instance.select_text(new_start, new_end)
                        except:
                            pass
                        finally:
                            self._ensuring_trailing = False

                    Clock.schedule_once(restore, 0.2)
                    return True
                instance.insert_text('    ')
                return True
            except Exception as e:
                self._ensuring_trailing = False
                log_error(f"Tab handler error: {e}")
                return False
        return False

    # ------------------------------------------------------------------ focus / touch

    def _on_focus(self, instance, focused):
        if focused:
            self._keyboard_visible = True
            Clock.schedule_once(self._show_keyboard, 0.05)
            Clock.schedule_once(self._show_keyboard, 0.15)
        else:
            self._keyboard_visible = False

    def _on_touch_down(self, instance, touch):
        if instance.collide_point(*touch.pos):
            instance.focus = True
            
            try:
                # get_cursor_from_xy всегда возвращает (col, row)
                col, row = instance.get_cursor_from_xy(touch.x, touch.y)
                # Вычисляем индекс из col, row
                lines = instance.text.split('\n')
                clicked_cursor = 0
                for i in range(row):
                    clicked_cursor += len(lines[i]) + 1
                clicked_cursor += col
            except:
                clicked_cursor = instance.cursor_index()
            
            # Если уже есть выделение, проверяем — продолжаем или начинаем новое
            if instance.selection_text:
                sel_from = instance.selection_from
                sel_to = instance.selection_to
                
                # Определяем, к какому краю ближе касание
                dist_to_from = abs(clicked_cursor - sel_from)
                dist_to_to = abs(clicked_cursor - sel_to)
                
                if dist_to_from <= dist_to_to:
                    # Тянем за начало — якорь в конце
                    self._selection_anchor = sel_to
                    instance.select_text(clicked_cursor, self._selection_anchor)
                else:
                    # Тянем за конец — якорь в начале
                    self._selection_anchor = sel_from
                    instance.select_text(self._selection_anchor, clicked_cursor)
            else:
                # Нет выделения — начинаем новое
                self._selection_anchor = clicked_cursor
            
            Clock.schedule_once(self._show_keyboard, 0.05)
            Clock.schedule_once(self._show_keyboard, 0.1)
            return False
        else:
            app = App.get_running_app()
            if app and hasattr(app, 'autocomplete'):
                app.autocomplete.hide()
            return False
    
    
    def _on_touch_move(self, instance, touch):
        """Обрабатывает движение пальца при выделении текста"""
        if not instance.focus:
            return False
    
        try:
            if hasattr(instance, 'get_cursor_from_xy'):
                # get_cursor_from_xy всегда возвращает (col, row)
                col, row = instance.get_cursor_from_xy(touch.x, touch.y)
                lines = instance.text.split('\n')
                new_cursor = 0
                for i in range(row):
                    new_cursor += len(lines[i]) + 1
                new_cursor += col
                new_cursor = min(new_cursor, len(instance.text))
                
                if self._selection_anchor is not None:
                    # Расширяем выделение от якоря до текущей позиции
                    instance.select_text(self._selection_anchor, new_cursor)
                else:
                    # Начинаем выделение
                    self._selection_anchor = new_cursor
                    instance.select_text(new_cursor, new_cursor)
                
                self._auto_scroll_by_cursor(instance)
    
        except Exception as e:
            log_error(f"Touch move error: {e}")
    
        return False

    def _auto_scroll_by_cursor(self, text_input):
        """Прокручивает редактор, если курсор находится за пределами видимой области"""
        if not text_input or not text_input.parent:
            return

        scroll_view = None
        parent = text_input.parent
        while parent:
            from kivy.uix.scrollview import ScrollView
            if isinstance(parent, ScrollView):
                scroll_view = parent
                break
            parent = parent.parent

        if not scroll_view:
            return

        try:
            cursor_line = text_input.cursor[1]
            line_height = text_input.line_height if hasattr(text_input, 'line_height') else self._font_size * 1.2

            sv_height = scroll_view.height
            sv_width = scroll_view.width

            total_lines = max(1, len(text_input.text.split('\n')))
            total_height = total_lines * line_height

            scroll_y = scroll_view.scroll_y
            cursor_y_top = cursor_line * line_height

            visible_top = (1.0 - scroll_y) * max(0, total_height - sv_height)
            visible_bottom = visible_top + sv_height

            scroll_margin = line_height * 1.5
            scroll_speed = 0.03

            # Вертикальная прокрутка
            if cursor_y_top < visible_top + scroll_margin:
                target_scroll = 1.0 - (cursor_y_top - sv_height / 2) / max(1, total_height - sv_height)
                target_scroll = max(0.0, min(1.0, target_scroll))
                new_scroll = scroll_y + (target_scroll - scroll_y) * 0.3
                scroll_view.scroll_y = new_scroll

            elif cursor_y_top + line_height > visible_bottom - scroll_margin:
                target_scroll = 1.0 - (cursor_y_top + line_height - sv_height / 2) / max(1, total_height - sv_height)
                target_scroll = max(0.0, min(1.0, target_scroll))
                new_scroll = scroll_y + (target_scroll - scroll_y) * 0.3
                scroll_view.scroll_y = new_scroll

            # Горизонтальная прокрутка
            cursor_index = text_input.cursor_index()
            text_before_cursor = text_input.text[:cursor_index]
            current_line_start = text_before_cursor.rfind('\n') + 1
            cursor_col = cursor_index - current_line_start

            lines = text_input.text.split('\n')
            current_line = lines[cursor_line] if cursor_line < len(lines) else ""

            char_width = text_input.font_size * 0.6
            cursor_x_pos = cursor_col * char_width
            line_width = len(current_line) * char_width

            scroll_x = scroll_view.scroll_x
            visible_left = scroll_x * max(0, line_width - sv_width)
            visible_right = visible_left + sv_width

            h_margin = char_width * 5

            if cursor_x_pos < visible_left + h_margin:
                target_scroll_x = max(0.0, (cursor_x_pos - sv_width / 2) / max(1, line_width - sv_width))
                target_scroll_x = max(0.0, min(1.0, target_scroll_x))
                new_scroll_x = scroll_x + (target_scroll_x - scroll_x) * 0.4
                scroll_view.scroll_x = new_scroll_x

            elif cursor_x_pos + char_width > visible_right - h_margin:
                target_scroll_x = min(1.0, (cursor_x_pos + char_width - sv_width / 2) / max(1, line_width - sv_width))
                target_scroll_x = max(0.0, min(1.0, target_scroll_x))
                new_scroll_x = scroll_x + (target_scroll_x - scroll_x) * 0.4
                scroll_view.scroll_x = new_scroll_x

        except Exception as e:
            log_error(f"Auto scroll error: {e}")

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
        while self._indent_guides:
            try:
                guide = self._indent_guides.pop()
                ti.canvas.after.remove(guide)
            except:
                pass
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
        for line_idx in range(first_line, last_line):
            if line_idx >= total_lines:
                break
            line_text = self.original_lines[line_idx]
            indent = 0
            for ch in line_text:
                if ch == ' ':
                    indent += 1
                else:
                    break
            if indent < 4:
                continue
            num_guides = indent // 4
            line_y = ti.y + ti.height - (line_idx + 1) * lh
            for g in range(1, num_guides + 1):
                x_pos = ti.x + left_padding + (g * 4) * char_width
                pad = lh * 0.2
                y_start = line_y + pad
                y_end = line_y + lh - pad
                with ti.canvas.after:
                    Color(*guide_color)
                    line = Line(points=[x_pos, y_start, x_pos, y_end], width=dp(0.3))
                    self._indent_guides.append(line)

    # ------------------------------------------------------------------ current line highlight

    def _update_current_line_highlight(self, instance, cursor_pos):
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

    # ------------------------------------------------------------------ recreate code input

    def _recreate_code_input(self, theme):
        try:
            from pygments.lexers import PythonLexer
            from kivy.uix.codeinput import CodeInput
            saved_text = self.text_input.text if self.text_input else ''
            old_width = self.text_input.width if self.text_input else dp(400)
            cursor_pos = self.text_input.cursor_index() if self.text_input else 0
            self.text_input.unbind(text=self._on_text_change)
            self.text_input.unbind(minimum_height=self.text_input.setter('height'))
            if hasattr(self.text_input, 'minimum_width'):
                self.text_input.unbind(minimum_width=self.text_input.setter('width'))
            self.editor_scroll.remove_widget(self.text_input)
            style_name = ThemeManager.get_syntax_style()
            self.current_syntax_style = style_name
            self.text_input = CodeInput(lexer=PythonLexer(), style=style_name, size_hint=(None, None),
                                        font_size=self._font_size, background_color=theme['editor_bg'],
                                        foreground_color=theme['editor_text'], cursor_color=theme['editor_cursor'],
                                        selection_color=theme.get('editor_selection', (1, 1, 1, 0.1)), multiline=True,
                                        do_wrap=False, padding=(dp(8), self._padding_top, dp(8), self._padding_bottom),
                                        background_normal='', background_active='')
            self.text_input.bind(text=self._on_text_change, minimum_height=self.text_input.setter('height'))
            if hasattr(self.text_input, 'minimum_width'):
                self.text_input.bind(minimum_width=self.text_input.setter('width'))
            self._current_line_highlight = None
            self.text_input.bind(cursor=self._update_current_line_highlight)
            self.editor_scroll.add_widget(self.text_input)
            self.text_input.text = saved_text
            self.text_input.width = old_width
            if hasattr(self.text_input, '_trigger_refresh_text'):
                Clock.schedule_once(lambda dt: self.text_input._trigger_refresh_text(), 0.1)

            def restore_cursor(dt):
                try:
                    if cursor_pos <= len(self.text_input.text):
                        self.text_input.cursor = self.text_input.get_cursor_from_index(cursor_pos)
                except:
                    pass

            Clock.schedule_once(restore_cursor, 0.05)
            if saved_text:
                self.original_lines = saved_text.split('\n')
                self._folding.apply_display_edit(self.original_lines)
                self._refresh_virtual_panel()
        except ImportError as e:
            log_error(f"Cannot recreate CodeInput: {e}")
        except Exception as e:
            log_error(f"Error in _recreate_code_input: {e}")

    # ------------------------------------------------------------------ cleanup

    def cleanup(self):
        ThemeManager.unregister(self)
        if hasattr(self, '_undo_stack'):
            self._undo_stack.clear()
        if hasattr(self, '_redo_stack'):
            self._redo_stack.clear()
        Window.unbind(on_keyboard=self._on_window_keyboard)
        Window.unbind(on_key_down=self._on_window_key_down)

    def debug_folding(self):
        """Отладочный метод для проверки сворачивания"""
        print("=== FOLDING DEBUG ===")
        print(f"Original lines count: {len(self._folding.get_orig_lines())}")
        print(f"Display lines count: {len(self._folding.get_display_lines())}")
        print(f"Folds: {self._folding._folds}")
        print(f"Fold ranges: {self._folding.get_fold_ranges()}")
        print("===================")

























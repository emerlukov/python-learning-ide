"""
Code editor widget with line numbers and syntax highlighting
"""
import re
import time
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.codeinput import CodeInput
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle, Line
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


class LineNumberTextInput(BoxLayout):
    """Основной компонент редактора кода с нумерацией строк"""

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
        self._create_ui()
        self.apply_theme(ThemeManager.get_theme())
        Window.bind(on_keyboard=self._on_window_keyboard)
        self.text_input.bind(on_key_down=self._on_key_down)
        self.text_input.bind(font_name=self._on_font_changed)
        Window.bind(on_key_down=self._on_window_key_down)

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
            Clock.schedule_once(self._update_line_panel, 0.15)
            Clock.schedule_once(self._force_line_panel_refresh, 0.2)
            if old_cursor <= len(ti.text):
                Clock.schedule_once(lambda x: setattr(ti, 'cursor', ti.get_cursor_from_index(old_cursor)), 0.25)
        except Exception as e:
            log_error(f"force_full_font_reset error: {e}")

    def _rebuild_line_panel_completely(self):
        if not hasattr(self, 'line_panel'):
            return
        theme = ThemeManager.get_theme()
        lh = getattr(self.text_input, 'line_height', self._font_size * 1.2)
        n_lines = max(1, len(self.original_lines))

        # Определяем ширину панели
        category = get_screen_category()
        if category == 'tablet':
            panel_width = dp(65)
        elif category == 'large_phone':
            panel_width = dp(55)
        else:
            panel_width = dp(45)

        self.line_panel.clear_widgets()
        for i in range(n_lines):
            row = BoxLayout(orientation='horizontal', size_hint_y=None, height=lh)
            lbl = Label(text=str(i + 1), font_size=self._font_size, size_hint_x=None, width=panel_width,
                        color=theme.get('panel_text', (0.45, 0.48, 0.50, 1)), halign='right', valign='middle',
                        padding=(0, 0, dp(3), 0))
            row.add_widget(lbl)
            self.line_panel.add_widget(row)

        self.line_panel.height = max(self.text_input.height, n_lines * lh)
        self._update_separator()

    def apply_theme(self, theme):
        self.current_theme_name = theme['name']
        Window.clearcolor = theme['window_bg']

        if hasattr(self, 'bg_color'):
            self.bg_color.rgba = theme['app_bg']

        # Обновляем верхние панели (только если есть в главном приложении)
        app = App.get_running_app()
        if app and hasattr(app, '_update_top_panels'):
            app._update_top_panels()
        if hasattr(self, 'panel_bg_color'):
            self.panel_bg_color.rgba = theme['panel_bg']
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
            self._update_line_panel()
        if hasattr(self, 'text_input') and hasattr(self, 'line_panel'):
            if hasattr(self.text_input, 'line_height'):
                lh = self.text_input.line_height
            else:
                lh = self._font_size * 1.2
            n_lines = len(self.original_lines) if self.original_lines else 1
            self.line_panel.height = max(self.text_input.height, n_lines * lh)
            self._update_line_panel()

    def get_text(self):
        return self.text_input.text if hasattr(self, 'text_input') else ""

    def set_text(self, text):
        if hasattr(self, 'text_input'):
            self.text_input.text = text if text is not None else ""
            self.original_lines = text.split('\n')
            if hasattr(self, '_cached_max_line_length'):
                del self._cached_max_line_length
            if hasattr(self, '_cached_max_line_index'):
                del self._cached_max_line_index
            self._update_line_panel()
            Clock.schedule_once(self._draw_indent_guides, 0.3)

    def undo(self):
        if not self._undo_stack:
            return False
        self._undo_lock = True
        self._redo_stack.append({'text': self.text_input.text, 'cursor': self.text_input.cursor_index()})
        state = self._undo_stack.pop()
        self.text_input.text = state['text']
        self.original_lines = state['text'].split('\n')
        self._update_line_panel()
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
        self._update_line_panel()
        try:
            pos = min(state['cursor'], len(state['text']))
            self.text_input.cursor = self.text_input.get_cursor_from_index(pos)
        except:
            pass
        self._undo_lock = False
        return True

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
        self.line_panel = BoxLayout(orientation='vertical', size_hint=(None, None), width=panel_width, spacing=0)
        self.line_panel.bind(minimum_height=self.line_panel.setter('height'))
        theme = ThemeManager.get_theme()
        with self.line_panel.canvas.before:
            self.panel_bg_color = Color(*theme.get('panel_bg', (1, 1, 1, 1)))
            self.panel_bg_rect = Rectangle(pos=self.line_panel.pos, size=self.line_panel.size)
        self.line_panel.bind(pos=self._update_panel_bg, size=self._update_panel_bg)
        theme = ThemeManager.get_theme()
        scroll_bar_color = theme.get('scroll_bar_color', (0.4, 0.4, 0.4, 0.9))
        scroll_bar_inactive = theme.get('scroll_bar_inactive', (0.25, 0.25, 0.25, 0.6))
        self.line_panel_scroll = ScrollView(size_hint=(None, 1), width=panel_width, do_scroll_x=False, do_scroll_y=True,
                                            scroll_type=['bars'], bar_width=0, effect_cls='ScrollEffect',
                                            scroll_distance=dp(17), scroll_timeout=dp(45))
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
            self.text_input = CodeInput(lexer=PythonLexer(), style=style_name, size_hint=(None, None),
                                        font_size=font_size, background_color=theme['editor_bg'],
                                        foreground_color=theme['editor_text'], cursor_color=theme['editor_cursor'],
                                        selection_color=theme.get('editor_selection', (1, 1, 1, 0.1)), multiline=True,
                                        do_wrap=False, padding=(dp(8), padding_top, dp(8), padding_bottom),
                                        background_normal='', background_active='')
        else:
            self.text_input = TextInput(size_hint=(None, None), font_size=font_size,
                                        background_color=theme['editor_bg'], foreground_color=theme['editor_text'],
                                        cursor_color=theme['editor_cursor'],
                                        selection_color=theme.get('editor_selection', (1, 1, 1, 0.1)), multiline=True,
                                        do_wrap=False, padding=(dp(8), padding_top, dp(8), padding_bottom),
                                        background_normal='', background_active='')
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
        self.text_input.bind(on_touch_down=self._on_touch_down)
        self._current_line_highlight = None
        self.text_input.bind(cursor=self._update_current_line_highlight)

    def _bind_scroll_sync(self, *args):
        def sync_scroll(instance, value):
            self.line_panel_scroll.scroll_y = value
            Clock.unschedule(self._draw_indent_guides)
            Clock.schedule_once(self._draw_indent_guides, 0.1)

        self.editor_scroll.bind(scroll_y=sync_scroll)

    def _on_text_change(self, instance, value):
        self.original_lines = value.split('\n')
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
                prev_text = '\n'.join(self.original_lines) if self.original_lines else ''
                if not self._undo_stack or self._undo_stack[-1]['text'] != value:
                    self._undo_stack.append({'text': prev_text, 'cursor': instance.cursor_index() if hasattr(instance,
                                                                                                             'cursor_index') else 0})
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

        # ОПТИМИЗИРОВАННАЯ ЧАСТЬ - только помечаем, что нужно обновление
        if not self._redraw_pending:
            self._redraw_pending = True
            Clock.schedule_once(self._delayed_update_panel, 0.05)

        if not self._indent_guides_pending:
            self._indent_guides_pending = True
            Clock.schedule_once(self._draw_indent_guides, 0.15)

        # Убеждаемся, что в конце всегда есть пустые строки
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

        # Находим последнюю непустую строку
        last_non_empty = -1
        for i in range(len(self.original_lines) - 1, -1, -1):
            if self.original_lines[i].strip() != '':
                last_non_empty = i
                break

        if last_non_empty == -1:
            # Вообще нет текста — ничего не делаем
            return

        trailing = len(self.original_lines) - last_non_empty - 1
        if trailing >= TARGET:
            return

        self._ensuring_trailing = True
        try:
            # Сохраняем позицию курсора ДО изменений
            cursor_index = self.text_input.cursor_index()

            lines_to_add = TARGET - trailing
            current_text = self.text_input.text
            self.text_input.text = current_text + '\n' * lines_to_add
            self.original_lines = self.text_input.text.split('\n')

            # Восстанавливаем курсор на то же место
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
        self._update_line_panel()
        self._redraw_pending = False

    def _update_separator(self, instance=None, value=None):
        if hasattr(self, 'separator_line') and hasattr(self, 'line_panel_scroll'):
            x = self.layout.x + self.line_panel_scroll.width
            y1 = self.layout.y
            y2 = self.layout.y + self.layout.height
            self.separator_line.points = [x, y1, x, y2]

    def _update_panel_bg(self, instance, value):
        """Обновляет фон панели"""
        if hasattr(self, 'panel_bg_rect'):
            self.panel_bg_rect.pos = instance.pos
            self.panel_bg_rect.size = instance.size

    def _update_text_width(self, *args):
        if not self.original_lines:
            return
        max_line_length = max(len(line) for line in self.original_lines) if self.original_lines else 0
        char_width = self.text_input.font_size * 0.6
        min_width = dp(400)
        calculated_width = max(min_width, max_line_length * char_width + dp(33))
        new_width = min(calculated_width, dp(3333))
        self.text_input.width = new_width
        self._update_separator()

    def _update_line_panel(self, *args):
        if hasattr(self.text_input, 'line_height'):
            lh = self.text_input.line_height
        else:
            lh = self._font_size * 1.2
        theme = ThemeManager.get_theme()
        n_lines = len(self.original_lines)
        panel_width = self.line_panel.width
        current_widgets = len(self.line_panel.children)

        if current_widgets == n_lines:
            # Обновляем существующие метки
            for i, child in enumerate(reversed(self.line_panel.children)):
                if hasattr(child, 'children') and child.children:
                    lbl = child.children[0]
                    if isinstance(lbl, Label):
                        lbl.text = str(i + 1)
                        lbl.width = panel_width
                        lbl.text_size = (panel_width - dp(3), None)
            return
        diff = n_lines - current_widgets
        if 0 < diff <= 10:
            for i in range(current_widgets, n_lines):
                row = BoxLayout(orientation='horizontal', size_hint_y=None, height=lh)
                lbl = Label(text=str(i + 1), font_size=self._font_size, size_hint_x=None, width=panel_width,
                            color=theme['panel_text'], halign='right', valign='top', padding=(0, 0, dp(3), 0))
                lbl.text_size = (panel_width - dp(3), None)
                row.add_widget(lbl)
                self.line_panel.add_widget(row)
            self.line_panel.height = max(self.text_input.height, n_lines * lh)
            self._update_separator()
            return
        if -10 <= diff < 0:
            for _ in range(abs(diff)):
                if self.line_panel.children:
                    child = self.line_panel.children[0]
                    self.line_panel.remove_widget(child)
            for i, child in enumerate(reversed(self.line_panel.children)):
                if hasattr(child, 'children') and child.children:
                    lbl = child.children[0]
                    if isinstance(lbl, Label):
                        lbl.text = str(i + 1)
            self.line_panel.height = max(self.text_input.height, n_lines * lh)
            self._update_separator()
            return
        self.line_panel.clear_widgets()
        batch_size = 50
        for batch_start in range(0, n_lines, batch_size):
            batch_end = min(batch_start + batch_size, n_lines)
            for i in range(batch_start, batch_end):
                row = BoxLayout(orientation='horizontal', size_hint_y=None, height=lh)
                lbl = Label(text=str(i + 1), font_size=self._font_size, size_hint_x=None, width=panel_width,
                            color=theme['panel_text'], halign='right', valign='top', padding=(0, 0, dp(3), 0))
                lbl.text_size = (panel_width - dp(3), None)
                row.add_widget(lbl)
                self.line_panel.add_widget(row)
            if batch_end < n_lines:
                Clock.schedule_once(lambda dt: None, 0)
        self.line_panel.height = max(self.text_input.height, n_lines * lh)
        self._update_separator()
        Clock.schedule_once(self._force_line_panel_refresh, 0.05)

    def _force_line_panel_refresh(self, dt=None):
        """Принудительно обновляет ширину и текст всех меток с номерами строк"""
        if not hasattr(self, 'line_panel') or not self.line_panel.children:
            return

        # Получаем актуальную ширину панели
        panel_width = self.line_panel.width

        # Обновляем каждую метку
        for i, child in enumerate(reversed(self.line_panel.children)):
            if hasattr(child, 'children') and child.children:
                lbl = child.children[0]
                if isinstance(lbl, Label):
                    # Обновляем текст (номер строки)
                    lbl.text = str(i + 1)
                    # Обновляем ширину и размер текста
                    lbl.width = panel_width
                    lbl.text_size = (panel_width - dp(3), None)
                    # Принудительно перерисовываем
                    lbl.texture_update()

        # Обновляем разделитель
        self._update_separator()

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
                self._update_line_panel()
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
                        self._update_line_panel()

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
            Clock.schedule_once(self._show_keyboard, 0.05)
            Clock.schedule_once(self._show_keyboard, 0.1)
            return False
        else:
            app = App.get_running_app()
            if app and hasattr(app, 'autocomplete'):
                app.autocomplete.hide()
            return False

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
                self._update_line_panel()
        except ImportError as e:
            log_error(f"Cannot recreate CodeInput: {e}")
        except Exception as e:
            log_error(f"Error in _recreate_code_input: {e}")

    def cleanup(self):
        ThemeManager.unregister(self)
        if hasattr(self, '_undo_stack'):
            self._undo_stack.clear()
        if hasattr(self, '_redo_stack'):
            self._redo_stack.clear()
        Window.unbind(on_keyboard=self._on_window_keyboard)
        Window.unbind(on_key_down=self._on_window_key_down)
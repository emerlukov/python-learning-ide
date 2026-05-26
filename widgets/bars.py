"""
Action and symbol bars for the editor
"""
import re
import time
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.dropdown import DropDown
from kivy.uix.popup import Popup
from kivy.graphics import Color, Rectangle, Line
from kivy.core.clipboard import Clipboard
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.utils import platform
from kivy.app import App
from kivy.properties import ColorProperty, ListProperty, StringProperty
from kivy.lang import Builder

from kivymd.uix.button import MDIconButton
from kivymd.uix.label import MDIcon

from utils.screen_utils import get_screen_category, adaptive_dp, adaptive_sp
from utils.debug_utils import log_error
from utils.android_utils import android_copy
from core.themes import ThemeManager
from core.settings import SettingsManager
from widgets.dialogs import ThemedPopup


class MyActionBar(BoxLayout):
    """Панель с кнопками действий"""
    ACTION_UNDO = 'undo'
    ACTION_REDO = 'redo'
    ACTION_COPY = 'copy'
    ACTION_PASTE = 'paste'
    ACTION_CUT = 'cut'
    ACTION_SEL_ALL = 'sel_all'
    ACTION_AUTO = 'auto'
    ACTION_KEY = 'key'
    ACTION_CLEAN = 'clean'
    ACTION_FIND = 'find'
    ACTION_FIND_REPLACE = 'find_replace'
    ACTION_GOTO = 'goto'
    background_color = ColorProperty([0, 0, 0, 0])
    border = ListProperty([0, 0, 0, 0])
    background_image = StringProperty('')

    def __init__(self, text_input, **kwargs):
        kwargs.pop('background_normal', None)
        kwargs.pop('background_down', None)
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_y = None
        category = get_screen_category()
        if category == 'tablet':
            self.height = dp(52)
            self.spacing = dp(18)
            self.padding = [dp(4), dp(4), dp(4), dp(4)]
        elif category == 'large_phone':
            self.height = dp(45)
            self.spacing = dp(15)
            self.padding = [dp(3), dp(3), dp(3), dp(3)]
        else:
            self.height = dp(38)
            self.spacing = dp(12)
            self.padding = [dp(2), dp(2), dp(2), dp(2)]
        self.app = None
        self.text_input = text_input
        ThemeManager.register(self)
        self._keywords_cache = None
        self._autocomplete_cache = None
        self._keywords_popup = None
        self._autocomplete_popup = None
        self.action_keys = [self.ACTION_UNDO, self.ACTION_REDO, self.ACTION_COPY, self.ACTION_PASTE, self.ACTION_CUT,
                            self.ACTION_SEL_ALL, self.ACTION_AUTO, self.ACTION_KEY, self.ACTION_CLEAN, self.ACTION_FIND, self.ACTION_FIND_REPLACE, self.ACTION_GOTO]
        self.buttons = []
        self._create_scroll_view()
        self._create_buttons()
        self._add_buttons_to_container()
        self._create_background(ThemeManager.get_theme())
        self.apply_theme(ThemeManager.get_theme())
        Clock.schedule_once(self._clear_canvas, 0)

    def _create_scroll_view(self):
        theme = ThemeManager.get_theme()
        scroll_bar_color = theme.get('scroll_bar_color', (0.4, 0.4, 0.4, 0.7))
        scroll_bar_inactive = theme.get('scroll_bar_inactive', (0.25, 0.25, 0.25, 0.5))
        self.scroll_view = ScrollView(size_hint=(1, 1), do_scroll_x=True, do_scroll_y=False, bar_width=dp(2),
                                      bar_color=scroll_bar_color, bar_inactive_color=scroll_bar_inactive)
        self.button_container = BoxLayout(orientation='horizontal', size_hint_x=None, spacing=self.spacing,
                                          padding=self.padding)
        self.button_container.bind(minimum_width=self.button_container.setter('width'))
        self.scroll_view.add_widget(self.button_container)
        self.add_widget(self.scroll_view)

    def _create_buttons(self):
        self.buttons = []
        theme = ThemeManager.get_theme()
        action_icons = {
            self.ACTION_UNDO: 'undo', self.ACTION_REDO: 'redo', self.ACTION_COPY: 'content-copy',
            self.ACTION_PASTE: 'content-paste', self.ACTION_CUT: 'content-cut', self.ACTION_SEL_ALL: 'select-all',
            self.ACTION_AUTO: 'code-tags', self.ACTION_KEY: 'key-variant', self.ACTION_CLEAN: 'delete-sweep',
            self.ACTION_FIND: 'magnify', self.ACTION_FIND_REPLACE: 'find-replace',self.ACTION_GOTO: 'arrow-right-bold',
        }
        for key in self.action_keys:
            icon_name = action_icons.get(key, None)
            if icon_name:
                from kivymd.uix.button import MDIconButton
                btn = MDIconButton(icon=icon_name, size_hint=(None, None), size=(dp(30), dp(30)),
                                   font_size=f"{dp(12)}sp", theme_icon_color="Custom",
                                   icon_color=theme['symbol_btn_text'], pos_hint={"center_y": 0.5})
            else:
                app = App.get_running_app()
                tr = app.tr if app else TRANSLATIONS['ru']
                btn = Button(text=tr.get(key, key), size_hint=(None, 1), width=dp(32), font_size=dp(11),
                             background_color=theme['symbol_btn_bg'], background_normal='', background_down='',
                             color=theme['symbol_btn_text'], bold=True)
            btn.action_key = key
            btn.bind(on_press=self.handle_action)
            self.buttons.append(btn)

    def _add_buttons_to_container(self):
        for btn in self.buttons:
            self.button_container.add_widget(btn)

    def _create_background(self, theme):
        with self.canvas.before:
            self.bg_color = Color(*theme.get('symbol_btn_bg', theme['widget_bg']))
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

    def _update_bg(self, instance, value):
        if hasattr(self, 'bg_rect'):
            self.bg_rect.pos = instance.pos
            self.bg_rect.size = instance.size

    def _clear_canvas(self, dt):
        self.canvas.after.clear()

    def apply_theme(self, theme):
        if hasattr(self, 'bg_color'):
            self.bg_color.rgba = theme.get('symbol_btn_bg', theme['widget_bg'])
        for btn in self.buttons:
            btn.background_color = theme['symbol_btn_bg']
            btn.color = theme['symbol_btn_text']

    def handle_action(self, instance):
        # ВИБРАЦИЯ
        if self.app and hasattr(self.app, 'vibrate_short'):
            self.app.vibrate_short()

        try:
            ti = self._get_active_text_input()
            if not ti:
                return
            action_key = getattr(instance, 'action_key', None)
            if action_key == self.ACTION_UNDO:
                self._undo_action(ti)
            elif action_key == self.ACTION_REDO:
                self._redo_action(ti)
            elif action_key == self.ACTION_COPY:
                self._copy_action(ti)
            elif action_key == self.ACTION_PASTE:
                self._paste_action(ti)
            elif action_key == self.ACTION_CUT:
                self._cut_action(ti)
            elif action_key == self.ACTION_SEL_ALL:
                self._select_all_action(ti)
            elif action_key == self.ACTION_CLEAN:
                self._confirm_clean(ti)
                return
            elif action_key == self.ACTION_AUTO:
                self._show_autocomplete()
            elif action_key == self.ACTION_KEY:
                self._show_keywords()
            elif action_key == self.ACTION_FIND:
                if self.app and hasattr(self.app, 'show_search_dialog_from_button'):
                    self.app.show_search_dialog_from_button()
            elif action_key == self.ACTION_FIND_REPLACE:  # ← НОВАЯ КНОПКА
                if self.app and hasattr(self.app, 'show_search_replace_dialog'):
                    self.app.show_search_replace_dialog()
            elif action_key == self.ACTION_GOTO:
                if self.app and hasattr(self.app, 'show_goto_line_dialog'):
                    self.app.show_goto_line_dialog()
            if action_key in [self.ACTION_COPY, self.ACTION_PASTE, self.ACTION_CUT, self.ACTION_SEL_ALL,
                              self.ACTION_CLEAN, self.ACTION_UNDO, self.ACTION_REDO]:
                Clock.schedule_once(lambda dt: self._refocus(ti), 0.05)
        except Exception as e:
            log_error(f"ActionBar error: {e}")

    def _undo_action(self, ti):
        try:
            app = App.get_running_app()
            if app and hasattr(app, 'editor') and app.editor:
                app.editor.undo()
            self._refocus(ti)
        except Exception as e:
            log_error(f"Undo error: {e}")

    def _redo_action(self, ti):
        try:
            app = App.get_running_app()
            if app and hasattr(app, 'editor') and app.editor:
                app.editor.redo()
            self._refocus(ti)
        except Exception as e:
            log_error(f"Redo error: {e}")

    def _copy_action(self, ti):
        try:
            if hasattr(ti, 'selection_text') and ti.selection_text:
                Clipboard.copy(ti.selection_text)
                if platform == 'android':
                    android_copy(ti.selection_text)
        except Exception as e:
            log_error(f"Copy error: {e}")

    def _paste_action(self, ti):
        try:
            paste_text = Clipboard.paste()
            if paste_text:
                ti.insert_text(paste_text)
        except Exception as e:
            log_error(f"Paste error: {e}")

    def _cut_action(self, ti):
        try:
            if hasattr(ti, 'selection_text') and ti.selection_text:
                selected = ti.selection_text
                Clipboard.copy(selected)
                if platform == 'android':
                    android_copy(selected)
                ti.delete_selection()
        except Exception as e:
            log_error(f"Cut error: {e}")

    def _select_all_action(self, ti):
        def do_select(dt):
            try:
                if ti and ti.parent and ti.text:
                    ti.focus = True
                    lines = ti.text.split('\n')
                    last_non_empty = len(lines) - 1
                    while last_non_empty >= 0 and lines[last_non_empty].strip() == '':
                        last_non_empty -= 1
                    if last_non_empty >= 0:
                        end_pos = len('\n'.join(lines[:last_non_empty + 1]))
                        ti.select_text(0, end_pos)
                    else:
                        ti.select_all()
            except Exception as e:
                log_error(f"SelectAll error: {e}")

        Clock.schedule_once(do_select, 0.05)

    def _show_keywords(self):
        app = App.get_running_app()
        tr = app.tr if app else TRANSLATIONS['ru']

        def insert_word(word):
            if self.text_input:
                self.text_input.insert_text(word + ' ')
                self._refocus(self.text_input)
            if self._keywords_popup:
                self._keywords_popup.dismiss()
                self._keywords_popup = None

        self._keywords_popup = self._create_filterable_dialog(tr.get('keywords_title', 'Python Keywords'),
                                                              self._get_keywords_list(), insert_word)
        self._keywords_popup.open()

    def _show_autocomplete(self):
        app = App.get_running_app()
        tr = app.tr if app else TRANSLATIONS['ru']

        def insert_word(word):
            if self.text_input:
                self.text_input.insert_text(word + ' ')
                self._refocus(self.text_input)
            if self._autocomplete_popup:
                self._autocomplete_popup.dismiss()
                self._autocomplete_popup = None

        self._autocomplete_popup = self._create_filterable_dialog(tr.get('autocomplete_title', 'Autocomplete'),
                                                                  self._get_autocomplete_list(), insert_word)
        self._autocomplete_popup.open()

    def _create_filterable_dialog(self, title, items, insert_callback):
        theme = ThemeManager.get_theme()
        app = App.get_running_app()
        tr = app.tr if app else TRANSLATIONS['ru']
        layout = BoxLayout(orientation='vertical', spacing=dp(3), padding=dp(4))
        search_box = TextInput(hint_text=tr.get('search_hint', 'Search...'), multiline=False, font_size=dp(17),
                               font_name='SourceBold', background_color=theme['input_bg'],
                               foreground_color=theme['input_text'], cursor_color=theme['input_cursor'],
                               hint_text_color=theme['hint_text'], size_hint_y=None, height=dp(28),
                               padding=(dp(3), dp(3)))
        layout.add_widget(search_box)
        scroll = ScrollView(do_scroll_x=False, do_scroll_y=True)
        inner = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(1.5))
        inner.bind(minimum_height=inner.setter('height'))
        scroll.add_widget(inner)
        layout.add_widget(scroll)

        def update_buttons(filter_text=""):
            inner.clear_widgets()
            if filter_text:
                filtered = [w for w in items if filter_text.lower() in w.lower()]
            else:
                filtered = items[:50]
            for word in filtered[:50]:
                btn = Button(text=word, size_hint_y=None, height=dp(20), font_name='SourceBold',
                             background_color=theme['input_bg'], background_normal='', background_down='',
                             color=theme['input_text'], font_size=dp(17))
                btn.bind(on_release=lambda b, w=word: self._on_word_selected(w, insert_callback))
                inner.add_widget(btn)

        search_box.bind(text=lambda inst, val: update_buttons(val))
        update_buttons()
        close_btn = Button(text=tr.get('close', 'Close'), size_hint_y=None, height=dp(28), font_size=dp(17),
                           font_name='SourceBold', background_color=theme['widget_bg'], background_normal='',
                           background_down='', color=theme['text_color'])
        layout.add_widget(close_btn)
        popup = Popup(title=title, title_color=theme['popup_title'], background='',
                      background_color=theme.get('popup_bg', (1.0, 1.0, 1.0, 1)), content=layout, size_hint=(0.9, 0.8))
        close_btn.bind(on_release=popup.dismiss)
        return popup

    def _on_word_selected(self, word, callback):
        if callback:
            callback(word)

    def _get_active_text_input(self):
        if self.app and hasattr(self.app, 'current_input_widget'):
            w = self.app.current_input_widget
            if w:
                return w
        return self.text_input

    def _refocus(self, ti):
        try:
            if ti and ti.parent:
                ti.focus = True
                if hasattr(ti, 'show_keyboard'):
                    ti.show_keyboard()
        except Exception as e:
            log_error(f"Refocus error: {e}")

    def _get_keywords_list(self):
        if self._keywords_cache is None:
            try:
                import keyword
                self._keywords_cache = sorted(keyword.kwlist)
            except:
                self._keywords_cache = ['False', 'None', 'True', 'and', 'as', 'assert', 'async', 'await', 'break',
                                        'class', 'continue', 'def', 'del', 'elif', 'else', 'except', 'finally', 'for',
                                        'from', 'global', 'if', 'import', 'in', 'is', 'lambda', 'nonlocal', 'not', 'or',
                                        'pass', 'raise', 'return', 'try', 'while', 'with', 'yield']
        return self._keywords_cache

    def _get_autocomplete_list(self):
        if self._autocomplete_cache is None:
            self._autocomplete_cache = sorted(
                ['abs', 'all', 'any', 'bin', 'bool', 'callable', 'chr', 'dict', 'dir', 'enumerate', 'filter', 'float',
                 'format', 'input', 'int', 'len', 'list', 'map', 'max', 'min', 'print', 'range', 'round', 'set',
                 'sorted', 'str', 'sum', 'tuple', 'type', 'zip'])
        return self._autocomplete_cache

    def _confirm_clean(self, ti):
        theme = ThemeManager.get_theme()
        app = App.get_running_app()
        tr = app.tr if app else TRANSLATIONS['ru']
        content = BoxLayout(orientation='vertical', padding=dp(5), spacing=dp(3))
        content.add_widget(
            Label(text=tr.get('clean_confirm', 'Are you sure you want to clear all code?'), color=theme['text_color'],
                  font_size=dp(10), font_name='SourceBold', halign='center', size_hint_y=None, height=dp(20)))
        btn_layout = BoxLayout(size_hint_y=None, height=dp(18), spacing=dp(4))
        popup = ThemedPopup(title=tr.get('clean', 'Clean'), title_color=theme['popup_title'],
                            title_bg=theme.get('popup_title_bg', theme['widget_bg']),
                            popup_bg=theme.get('popup_bg', theme['widget_bg']),
                            separator_color=theme.get('popup_separator', (0.25, 0.25, 0.25, 1)), content=content,
                            size_hint=(0.8, 0.3), auto_dismiss=False)
        btn_yes = Button(text=tr.get('yes', 'Yes'), font_name='SourceBold',
                         background_color=theme.get('btn_danger_bg', (0.5, 0.2, 0.2, 1)), background_normal='',
                         background_down='', color=theme['text_color'], font_size=dp(9),
                         on_release=lambda x: self._do_clean(popup, ti))
        btn_no = Button(text=tr.get('no', 'No'), font_name='SourceBold', background_color=theme['widget_bg'],
                        background_normal='', background_down='', color=theme['text_color'], font_size=dp(9),
                        on_release=lambda x: popup.dismiss())
        btn_layout.add_widget(btn_no)
        btn_layout.add_widget(btn_yes)
        content.add_widget(btn_layout)
        popup.open()

    def _do_clean(self, popup, ti):
        popup.dismiss()
        if ti:
            empty_text = '\n'
            ti.text = empty_text
            app = App.get_running_app()
            if app and hasattr(app, 'editor') and app.editor:
                app.editor.original_lines = ['']
                app.editor._update_line_panel()

            def set_cursor(dt):
                try:
                    ti.cursor = (0, 0)
                    ti.focus = True
                except:
                    pass

            Clock.schedule_once(set_cursor, 0.1)
            self._refocus(ti)

    def cleanup(self):
        self._keywords_cache = None
        self._autocomplete_cache = None
        if self._keywords_popup:
            self._keywords_popup.dismiss()
            self._keywords_popup = None
        if self._autocomplete_popup:
            self._autocomplete_popup.dismiss()
            self._autocomplete_popup = None
        self.buttons.clear()
        ThemeManager.unregister(self)


class MySymbolScrollBar(BoxLayout):
    """Панель с часто используемыми символами"""
    background_color = ColorProperty([0, 0, 0, 0])
    border = ListProperty([0, 0, 0, 0])
    background_image = StringProperty('')

    def __init__(self, text_input, **kwargs):
        kwargs.pop('background_normal', None)
        kwargs.pop('background_down', None)
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_y = None
        category = get_screen_category()
        if category == 'tablet':
            self.height = dp(42)
            self.spacing = dp(4)
            self.padding = [dp(4), dp(4), dp(4), dp(4)]
        elif category == 'large_phone':
            self.height = dp(36)
            self.spacing = dp(3)
            self.padding = [dp(3), dp(3), dp(3), dp(3)]
        else:
            self.height = dp(30)
            self.spacing = dp(2)
            self.padding = [dp(2), dp(2), dp(2), dp(2)]
        self.app = None
        self.text_input = text_input
        self._saved_sel_start = None
        self._saved_sel_end = None
        ThemeManager.register(self)
        self.symbols = ['Tab', '#', '( )', '[ ]', '{ }', '" "', "' '", '=', ':', '.', '_', ',', '+', '-', '*', '/',
                        '\\', '%', ')', ']', '}', '<', '>', '!', '|', '&', '@', '~', '?', ';', '$', '^']
        self._action_map = self._build_action_map()
        self.buttons = []
        self._create_scroll_view()
        self._create_buttons()
        self._add_buttons_to_container()
        self._create_background(ThemeManager.get_theme())
        self.apply_theme(ThemeManager.get_theme())
        Clock.schedule_once(self._clear_canvas, 0)

    def _create_scroll_view(self):
        theme = ThemeManager.get_theme()
        scroll_bar_color = theme.get('scroll_bar_color', (0.4, 0.4, 0.4, 0.7))
        scroll_bar_inactive = theme.get('scroll_bar_inactive', (0.25, 0.25, 0.25, 0.5))
        self.scroll_view = ScrollView(size_hint=(1, 1), do_scroll_x=True, do_scroll_y=False, bar_width=dp(2),
                                      bar_color=scroll_bar_color, bar_inactive_color=scroll_bar_inactive)
        self.button_container = BoxLayout(orientation='horizontal', size_hint_x=None, spacing=self.spacing,
                                          padding=self.padding)
        self.button_container.bind(minimum_width=self.button_container.setter('width'))
        self.scroll_view.add_widget(self.button_container)
        self.add_widget(self.scroll_view)

    def _create_buttons(self):
        theme = ThemeManager.get_theme()
        wide_symbols = {'( )': dp(37), '[ ]': dp(37), '{ }': dp(37), '" "': dp(37), "' '": dp(37), 'Tab': dp(37)}
        default_width = dp(30)
        for symbol in self.symbols:
            width = wide_symbols.get(symbol, default_width)
            btn = Button(text=symbol, font_name='SourceBold', size_hint=(None, 1), width=width,
                         background_color=theme['symbol_btn_bg'], background_normal='', background_down='',
                         color=theme['symbol_btn_text'], font_size=dp(13))
            btn.bind(on_press=self.handle_action)
            self.buttons.append(btn)

    def _add_buttons_to_container(self):
        for btn in self.buttons:
            self.button_container.add_widget(btn)

    def _create_background(self, theme):
        with self.canvas.before:
            self.bg_color = Color(*theme.get('action_bar_bg', theme['widget_bg']))
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

    def _update_bg(self, instance, value):
        if hasattr(self, 'bg_rect'):
            self.bg_rect.pos = instance.pos
            self.bg_rect.size = instance.size

    def _clear_canvas(self, dt):
        self.canvas.after.clear()

    def _build_action_map(self):
        def insert_pair(ti, pair):
            cursor_pos = ti.cursor_index()
            ti.insert_text(pair)
            ti.cursor = ti.get_cursor_from_index(cursor_pos + 1)

        def insert_text(text):
            return lambda ti: ti.insert_text(text)

        return {
            'Tab': lambda ti: self._handle_tab_button(ti), '=': insert_text('='), ':': insert_text(':'),
            ',': insert_text(','), '.': insert_text('.'), '_': insert_text('_'), '+': insert_text('+'),
            '-': insert_text('-'), '*': insert_text('*'), '/': insert_text('/'), '\\': insert_text('\\'),
            '%': insert_text('%'), '#': insert_text('#'), '@': insert_text('@'), '&': insert_text('&'),
            '|': insert_text('|'), '!': insert_text('!'), ')': insert_text(')'), ']': insert_text(']'),
            '}': insert_text('}'), '<': insert_text('<'), '>': insert_text('>'), '~': insert_text('~'),
            '?': insert_text('?'), ';': insert_text(';'), '$': insert_text('$'), '^': insert_text('^'),
            '( )': lambda ti: insert_pair(ti, '()'), '[ ]': lambda ti: insert_pair(ti, '[]'),
            '{ }': lambda ti: insert_pair(ti, '{}'), '" "': lambda ti: insert_pair(ti, '""'),
            "' '": lambda ti: insert_pair(ti, "''"),
        }

    def apply_theme(self, theme):
        if hasattr(self, 'bg_color'):
            self.bg_color.rgba = theme.get('action_bar_bg', theme['widget_bg'])
        for btn in self.buttons:
            btn.background_color = theme['symbol_btn_bg']
            btn.color = theme['symbol_btn_text']

    def handle_action(self, instance):
        # ВИБРАЦИЯ
        if self.app and hasattr(self.app, 'vibrate_short'):
            self.app.vibrate_short()

        if instance.text != 'Tab':
            self._saved_sel_start = None
            self._saved_sel_end = None
        try:
            ti = self._get_active_text_input()
            if not ti:
                return
            action = self._action_map.get(instance.text)
            if action:
                action(ti)
                Clock.schedule_once(lambda dt: self._refocus(ti), 0.05)
        except Exception as e:
            log_error(f"SymbolBar error: {e}")

    def _handle_tab_button(self, ti):
        try:
            if hasattr(ti, 'selection_text') and ti.selection_text:
                start_idx, end_idx = ti.selection_from, ti.selection_to
                if start_idx > end_idx:
                    start_idx, end_idx = end_idx, start_idx
                text = ti.text
                start_line = text[:start_idx].count('\n')
                end_line = text[:end_idx].count('\n')
                if start_line == end_line:
                    ti.insert_text('    ')
                    return
                lines = text.split('\n')
                for i in range(start_line, end_line + 1):
                    if i < len(lines):
                        lines[i] = '    ' + lines[i]
                new_text = '\n'.join(lines)
                new_start = start_idx + 4
                new_end = end_idx + 4 * (end_line - start_line + 1)
                ti.text = new_text

                def restore(dt):
                    try:
                        ti.focus = True
                        ti.select_text(new_start, new_end)
                    except:
                        pass

                Clock.schedule_once(restore, 0.2)
                return
            ti.insert_text('    ')
        except Exception as e:
            log_error(f"Tab button error: {e}")
            ti.insert_text('    ')

    def _get_active_text_input(self):
        if self.app and hasattr(self.app, 'current_input_widget'):
            w = self.app.current_input_widget
            if w:
                return w
        return self.text_input

    def _refocus(self, ti):
        try:
            if ti and ti.parent:
                ti.focus = True
                if hasattr(ti, 'show_keyboard'):
                    ti.show_keyboard()
        except Exception as e:
            log_error(f"Refocus error: {e}")

    def cleanup(self):
        self.buttons.clear()
        self._action_map.clear()
        ThemeManager.unregister(self)
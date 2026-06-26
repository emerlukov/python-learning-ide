"""
Tab manager for multiple code editors
"""
import os
import json
import re
import uuid
import time
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.dropdown import DropDown
from kivy.graphics import Color, Rectangle
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.app import App

from widgets.editor import LineNumberTextInput
from widgets.dialogs import ThemedPopup
from utils.screen_utils import get_screen_category, get_tab_count
from utils.paths import user_data_path, ensure_user_data_dir
from utils.debug_utils import log_error
from ide_core.themes import ThemeManager

class TabManager:
    """Управляет вкладками редактора"""

    def __init__(self):
        self.tabs = []
        self.active_index = -1
        self.tab_bar = None
        self.app = None
        self.tab_offset = 0
        self.max_visible = get_tab_count()

    def check_tab_changed(self, index):
        """Проверяет, изменилось ли содержимое вкладки"""
        if 0 <= index < len(self.tabs):
            tab = self.tabs[index]
            current_text = tab['editor'].get_text() if tab['editor'] else ""
            original = tab.get('original_content', "")

            # Сравниваем текущее содержимое с исходным
            has_changes = current_text != original

            if has_changes != (not tab.get('saved', True)):
                tab['saved'] = not has_changes
                if self.app:
                    self.app._update_title_from_current_tab()
                self._update_tab_bar()
                self.save_all_tabs()

            return has_changes
        return False

    def mark_tab_saved(self, index):
        """Отмечает вкладку как сохранённую"""
        if 0 <= index < len(self.tabs):
            self.tabs[index]['saved'] = True
            # Обновляем исходное содержимое
            self.tabs[index]['original_content'] = self.tabs[index]['editor'].get_text()
            if self.app:
                self.app._update_title_from_current_tab()
            self._update_tab_bar()
            self.save_all_tabs()

    def mark_tab_unsaved(self, index):
        """Отмечает вкладку как изменённую"""
        if 0 <= index < len(self.tabs):
            self.tabs[index]['saved'] = False
            if self.app:
                self.app._update_title_from_current_tab()
            self._update_tab_bar()
            self.save_all_tabs()

    def close_tab(self, index):
        """Закрывает вкладку без проверки сохранения (для внутреннего использования)"""
        if len(self.tabs) <= 1:
            # Если это последняя вкладка, просто очищаем её вместо закрытия
            if 0 <= index < len(self.tabs):
                self.tabs[index]['editor'].set_text("")
                self.tabs[index]['file'] = None
                self.tabs[index]['title'] = self.app.tr.get('untitled_tab', 'Новый') if self.app else 'Новый'
                self.tabs[index]['original_content'] = ""
                self.tabs[index]['saved'] = True
                self._update_tab_bar()
                self.save_all_tabs()
                return True
            return False

        if 0 <= index < len(self.tabs):
            tab = self.tabs.pop(index)
            if hasattr(tab['editor'], 'cleanup'):
                tab['editor'].cleanup()
            if self.active_index >= len(self.tabs):
                self.active_index = len(self.tabs) - 1
            self._update_tab_bar()
            self.save_all_tabs()
            return True
        return False

    def switch_to_tab(self, index):
        if 0 <= index < len(self.tabs) and index != self.active_index:
            self.active_index = index
            self._update_tab_bar()
            self.save_all_tabs()
            return self.get_active_editor()
        return None

    def get_active_editor(self):
        if 0 <= self.active_index < len(self.tabs):
            return self.tabs[self.active_index]['editor']
        return None

    def get_active_text(self):
        editor = self.get_active_editor()
        return editor.get_text() if editor else ""

    def get_active_file(self):
        if 0 <= self.active_index < len(self.tabs):
            return self.tabs[self.active_index]['file']
        return None

    def set_active_file(self, file_path):
        if 0 <= self.active_index < len(self.tabs):
            tr = self.app.tr if self.app else {}
            self.tabs[self.active_index]['file'] = file_path
            self.tabs[self.active_index]['title'] = os.path.basename(file_path) if file_path else tr.get('untitled_tab',
                                                                                                         'Новый')
            self._update_tab_bar()

    def set_active_title(self, title):
        if 0 <= self.active_index < len(self.tabs):
            self.tabs[self.active_index]['title'] = title
            self._update_tab_bar()

    def mark_active_unsaved(self):
        if 0 <= self.active_index < len(self.tabs):
            self.tabs[self.active_index]['saved'] = False
            self._update_tab_bar()

    def mark_active_saved(self):
        if 0 <= self.active_index < len(self.tabs):
            self.tabs[self.active_index]['saved'] = True
            self._update_tab_bar()

    def create_tab_bar(self, theme):
        category = get_screen_category()
        if category == 'tablet':
            tab_height = dp(42)
            tab_font_size = dp(13)
            close_btn_size = dp(24)
        elif category == 'large_phone':
            tab_height = dp(36)
            tab_font_size = dp(12)
            close_btn_size = dp(22)
        else:
            tab_height = dp(30)
            tab_font_size = dp(11)
            close_btn_size = dp(20)

        self.tab_bar = BoxLayout(size_hint_y=None, height=tab_height, spacing=dp(1),
                                 padding=[dp(1), dp(1), dp(1), dp(1)])
        with self.tab_bar.canvas.before:
            Color(*theme.get('tab_bar_bg', theme['action_bar_bg']))
            self.tab_bg_rect = Rectangle(pos=self.tab_bar.pos, size=self.tab_bar.size)
        self.tab_bar.bind(pos=self._update_tab_bg, size=self._update_tab_bg)

        self.btn_left = Button(text='◀', font_name='SourceBold', size_hint_x=None, width=dp(20),
                               background_color=theme.get('tab_inactive_bg', theme['widget_bg']), background_normal='',
                               background_down='', color=theme['text_color'], font_size=tab_font_size, bold=True)
        self.btn_left.bind(on_release=lambda x: self._scroll_tabs(-1))
        self.tab_bar.add_widget(self.btn_left)

        self.tab_buttons_container = BoxLayout(spacing=dp(1), size_hint=(1, 1), padding=[dp(0.7), dp(2), dp(0.7), 0])
        self.tab_bar.add_widget(self.tab_buttons_container)

        self.btn_right = Button(text='▶', font_name='SourceBold', size_hint_x=None, width=dp(20),
                                background_color=theme.get('tab_inactive_bg', theme['widget_bg']), background_normal='',
                                background_down='', color=theme['text_color'], font_size=tab_font_size, bold=True)
        self.btn_right.bind(on_release=lambda x: self._scroll_tabs(1))
        self.tab_bar.add_widget(self.btn_right)

        btn_add = Button(text='+', font_name='SourceBold', size_hint_x=None, width=dp(25),
                         background_color=theme.get('tab_add_btn_bg', theme['widget_bg']), background_normal='',
                         background_down='', color=theme['text_color'], font_size=tab_font_size + 6, bold=True)
        btn_add.bind(on_release=lambda x: self._on_add_tab())
        self.tab_bar.add_widget(btn_add)

        self._update_tab_bar()
        return self.tab_bar

    def _update_tab_bg(self, instance, value):
        if hasattr(self, 'tab_bg_rect'):
            self.tab_bg_rect.pos = instance.pos
            self.tab_bg_rect.size = instance.size

    def _scroll_tabs(self, direction):
        max_offset = max(0, len(self.tabs) - self.max_visible)
        self.tab_offset = max(0, min(self.tab_offset + direction, max_offset))
        self._update_tab_bar()

    def _on_add_tab(self):
        # ВИБРАЦИЯ
        #if self.app and hasattr(self.app, 'vibrate_short'):
            #self.app.vibrate_short()

        editor = self.add_tab()
        if self.app:
            self.app._on_tab_changed(editor)

    def _on_tab_press(self, index):
        # ВИБРАЦИЯ
        #if self.app and hasattr(self.app, 'vibrate_short'):
            #self.app.vibrate_short()

        editor = self.switch_to_tab(index)
        if editor and self.app:
            self.app._on_tab_changed(editor)

    def _on_tab_close(self, index):
        """Обработчик закрытия вкладки (с проверкой сохранения)"""
        if 0 <= index < len(self.tabs):
            self.check_tab_changed(index)
            tab = self.tabs[index]
            if not tab.get('saved', True):
                # Запоминаем ВСЕ данные о закрываемой вкладке
                tab_id = tab.get('id')
                tab_content = tab['editor'].get_text()
                tab_file = tab.get('file')
                tab_title = tab.get('title')
                self._show_close_tab_dialog(tab_id, tab_content, tab_file, tab_title, index)
                return

        # ВИБРАЦИЯ
        #if self.app and hasattr(self.app, 'vibrate_short'):
            #self.app.vibrate_short()

        self._do_close_tab(index)

    def _show_close_tab_dialog(self, tab_id, tab_content, tab_file, tab_title, index):
        """Показывает диалог при закрытии вкладки с несохранёнными изменениями"""
        if not self.app:
            return

        tr = self.app.tr
        theme = ThemeManager.get_theme()

        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.button import Button
        from kivy.uix.label import Label
        from kivy.clock import Clock

        # ========== АДАПТИВНЫЕ РАЗМЕРЫ ==========
        category = get_screen_category()
        if category == 'tablet':
            padding = dp(20)
            spacing = dp(15)
            msg_height = dp(100)
            btn_height = dp(55)
            font_size_msg = dp(16)
            font_size_btn = dp(15)
            popup_size = (0.75, 0.45)
        elif category == 'large_phone':
            padding = dp(15)
            spacing = dp(12)
            msg_height = dp(85)
            btn_height = dp(50)
            font_size_msg = dp(14)
            font_size_btn = dp(13)
            popup_size = (0.85, 0.42)
        else:
            padding = dp(12)
            spacing = dp(10)
            msg_height = dp(75)
            btn_height = dp(45)
            font_size_msg = dp(13)
            font_size_btn = dp(12)
            popup_size = (0.9, 0.45)

        content = BoxLayout(orientation='vertical', padding=padding, spacing=spacing)

        message = f"{tr.get('unsaved_changes', 'Unsaved changes')}\n\n'{tab_title}'\n\n{tr.get('save_before_exit', 'Save before closing?')}"

        msg_label = Label(
            text=message,
            color=theme['text_color'],
            font_size=font_size_msg,
            font_name='SourceBold',
            halign='center',
            valign='middle',
            size_hint_y=None,
            height=msg_height
        )
        msg_label.bind(width=lambda inst, val: setattr(inst, 'text_size', (val, None)))
        content.add_widget(msg_label)

        btn_layout = BoxLayout(size_hint_y=None, height=btn_height, spacing=spacing)

        # Используем ThemedPopup
        popup = ThemedPopup(
            title=tr.get('confirm_title', 'Unsaved changes'),
            title_color=theme['popup_title'],
            title_bg=theme.get('popup_title_bg', theme['widget_bg']),
            popup_bg=theme.get('popup_bg', theme.get('widget_bg', (0.188, 0.204, 0.251, 1))),
            separator_color=theme.get('popup_separator', (0.25, 0.25, 0.25, 1)),
            content=content,
            size_hint=popup_size,
            auto_dismiss=False
        )

        def on_save(x):
            popup.dismiss()
            if tab_file:
                self.app._save_tab_content_by_id(tab_file, tab_content, tab_id)
            else:
                self.app._save_tab_as_by_id(tab_content, tab_id)
            Clock.schedule_once(lambda dt: self._do_close_tab_by_id(tab_id), 0.5)

        def on_discard(x):
            popup.dismiss()
            self._do_close_tab_by_id(tab_id)

        def on_cancel(x):
            popup.dismiss()

        btn_save = Button(
            text=tr.get('save', 'Save'),
            font_name='SourceBold',
            background_color=(0.2, 0.5, 0.2, 1),
            background_normal='', background_down='',
            color=(1, 1, 1, 1),
            font_size=font_size_btn,
            size_hint=(1, 1),
            on_release=on_save
        )

        btn_discard = Button(
            text=tr.get('exit_without_save', 'Discard'),
            font_name='SourceBold',
            background_color=(0.5, 0.2, 0.2, 1),
            background_normal='', background_down='',
            color=(1, 1, 1, 1),
            font_size=font_size_btn,
            size_hint=(1, 1),
            on_release=on_discard
        )

        btn_cancel = Button(
            text=tr.get('cancel', 'Cancel'),
            font_name='SourceBold',
            background_color=theme.get('widget_bg', (0.141, 0.145, 0.149, 1)),
            background_normal='', background_down='',
            color=theme['text_color'],
            font_size=font_size_btn,
            size_hint=(1, 1),
            on_release=on_cancel
        )

        btn_layout.add_widget(btn_save)
        btn_layout.add_widget(btn_discard)
        btn_layout.add_widget(btn_cancel)
        content.add_widget(btn_layout)

        # ========== ОБЁРТКА КНОПОК ДЛЯ ВИБРАЦИИ ==========
        if self.app and hasattr(self.app, 'wrap_widget_buttons'):
            self.app.wrap_widget_buttons(content)

        popup.open()

    def _do_close_tab_by_id(self, tab_id):
        """Закрывает вкладку по ID (не по индексу)"""
        # ДОБАВИТЬ: проверка, не закрыта ли уже вкладка
        if tab_id is None:
            return

        # ДОБАВИТЬ: флаг для предотвращения повторного закрытия
        if hasattr(self, '_closing_tab_id') and self._closing_tab_id == tab_id:
            return
        self._closing_tab_id = tab_id

        try:
            # Находим индекс вкладки по ID
            index = -1
            for i, tab in enumerate(self.tabs):
                if tab.get('id') == tab_id:
                    index = i
                    break

            if index == -1:
                return  # Вкладка уже закрыта

            # Запоминаем, была ли это активная вкладка и её данные
            was_active = (index == self.active_index)
            active_tab_id_before = None
            if not was_active and self.active_index >= 0 and self.active_index < len(self.tabs):
                active_tab_id_before = self.tabs[self.active_index].get('id')

            # Удаляем вкладку с ПОЛНОЙ ОЧИСТКОЙ
            tab = self.tabs.pop(index)

            # ЯВНАЯ ОЧИСТКА ВСЕХ ССЫЛОК (ВАЖНО!)
            if hasattr(tab['editor'], 'cleanup'):
                tab['editor'].cleanup()

            # Очищаем данные вкладки для сборщика мусора
            tab['original_content'] = None
            tab['editor'] = None
            tab['file'] = None
            tab['title'] = None

            # Обновляем активный индекс
            if len(self.tabs) == 0:
                self.add_tab()
            else:
                if was_active:
                    # Если закрыли активную вкладку
                    if index > 0:
                        self.active_index = index - 1
                    elif index < len(self.tabs):
                        self.active_index = index
                    else:
                        self.active_index = 0
                else:
                    # Если закрыли НЕ активную вкладку
                    if index < self.active_index:
                        self.active_index -= 1

            # Обновляем UI
            self._update_tab_bar()
            self.save_all_tabs()

            # Обновляем отображаемый редактор
            if self.app and self.app.editor_container:
                active_editor = self.get_active_editor()
                if active_editor:
                    self.app.code_input = active_editor.text_input
                    self.app.editor = active_editor
                    if hasattr(self.app, 'action_bar') and self.app.action_bar:
                        self.app.action_bar.text_input = self.app.code_input
                    if hasattr(self.app, 'symbol_bar') and self.app.symbol_bar:
                        self.app.symbol_bar.text_input = self.app.code_input
                    if hasattr(self.app, 'autocomplete') and self.app.autocomplete:
                        self.app.autocomplete.code_input = self.app.code_input

                    self.app.editor_container.clear_widgets()
                    self.app.editor_container.add_widget(active_editor)

                    # Обновляем заголовок окна из активной вкладки
                    self.app._update_title_from_current_tab()

                    Clock.schedule_once(lambda dt: setattr(self.app.code_input, 'focus', True), 0.1)
        finally:
            self._closing_tab_id = None  # Сбрасываем флаг

    def _do_close_tab(self, index):
        """Оставляет для совместимости, но используем _do_close_tab_by_id"""
        self._do_close_tab_by_id(self.tabs[index].get('id') if index < len(self.tabs) else None)

    def add_tab(self, title=None, text="", file_path=None):
        if title is None:
            tr = self.app.tr if self.app else {}
            title = tr.get('untitled_tab', 'Новый')
        editor = LineNumberTextInput(size_hint_y=1.0)

        # Перепривязываем обработчики касаний для нового редактора
        if hasattr(editor, 'rebind_touch_handlers'):
            editor.rebind_touch_handlers()

        editor.set_text(text)

        def set_cursor_to_start(dt):
            try:
                if editor and hasattr(editor, 'text_input') and editor.text_input:
                    editor.text_input.cursor = (0, 0)
                    editor.text_input.focus = True
            except:
                pass

        Clock.schedule_once(set_cursor_to_start, 0.3)
        tab = {
            'id': str(uuid.uuid4()),  # ← УНИКАЛЬНЫЙ ID
            'title': title,
            'editor': editor,
            'file': file_path,
            'original_content': text,
            'saved': True
        }
        self.tabs.append(tab)
        self.active_index = len(self.tabs) - 1
        self._update_tab_bar()
        self.save_all_tabs()
        return editor

    def _close_tab_after_save(self, index):
        """Закрывает вкладку после сохранения"""
        # Обновляем статус после сохранения
        if 0 <= index < len(self.tabs):
            self.tabs[index]['saved'] = True
            self.tabs[index]['original_content'] = self.tabs[index]['editor'].get_text()
        self._do_close_tab(index)

    def update_tab_bar_theme(self, theme):
        if not hasattr(self, 'tab_bar') or not self.tab_bar:
            return
        new_bg = theme.get('action_bar_bg', theme['widget_bg'])
        self.tab_bar.canvas.before.clear()
        with self.tab_bar.canvas.before:
            Color(*new_bg)
            self.tab_bg_rect = Rectangle(pos=self.tab_bar.pos, size=self.tab_bar.size)
        if hasattr(self, 'btn_left'):
            self.btn_left.background_color = theme['widget_bg']
            self.btn_left.color = theme['text_color']
            if hasattr(self.btn_left, 'canvas'):
                self.btn_left.canvas.ask_update()
        if hasattr(self, 'btn_right'):
            self.btn_right.background_color = theme['widget_bg']
            self.btn_right.color = theme['text_color']
            if hasattr(self.btn_right, 'canvas'):
                self.btn_right.canvas.ask_update()
        for child in self.tab_bar.children:
            if isinstance(child, Button) and child.text == '+':
                child.background_color = theme['widget_bg']
                child.color = theme['text_color']
                if hasattr(child, 'canvas'):
                    child.canvas.ask_update()
                break
        if hasattr(self.tab_bar, 'canvas'):
            self.tab_bar.canvas.ask_update()
        self._update_tab_bar()

    def _update_tab_bar(self):
        if not self.tab_bar or not hasattr(self, 'tab_buttons_container'):
            return
        self.tab_buttons_container.clear_widgets()
        theme = ThemeManager.get_theme()
        start_idx = self.tab_offset
        end_idx = min(start_idx + self.max_visible, len(self.tabs))
        if hasattr(self, 'btn_left'):
            self.btn_left.disabled = (self.tab_offset == 0)
        if hasattr(self, 'btn_right'):
            self.btn_right.disabled = (end_idx >= len(self.tabs))
        for i in range(start_idx, end_idx):
            tab = self.tabs[i]
            title = tab['title']
            if len(title) > 15:
                title = title[:14] + '~'
            if not tab['saved']:
                title = '*' + title
            if i == self.active_index:
                base_bg = theme.get('tab_bar_bg', theme['action_bar_bg'])
                if theme.get('name') == 'light':
                    bg_color = (base_bg[0] * 0.85, base_bg[1] * 0.85, base_bg[2] * 0.85, 1)
                else:
                    bg_color = (base_bg[0] * 1.15 if base_bg[0] * 1.15 <= 1 else 1,
                                base_bg[1] * 1.15 if base_bg[1] * 1.15 <= 1 else 1,
                                base_bg[2] * 1.15 if base_bg[2] * 1.15 <= 1 else 1, 1)
                text_color = theme['text_color']
            else:
                bg_color = theme.get('tab_inactive_bg', theme['widget_bg'])
                text_color = theme['text_color']
            tab_box = BoxLayout(spacing=dp(0.3), size_hint_x=None, width=dp(95))
            btn_tab = Button(text=title, font_name='SourceBold', background_color=bg_color, background_normal='',
                             background_down='', color=text_color, font_size=dp(11), halign='left', valign='middle',
                             padding=(dp(3), 0))
            btn_tab.tab_index = i
            btn_tab.touch_start_time = 0
            btn_tab.touch_start_pos = (0, 0)

            def make_touch_down():
                def handler(instance, touch):
                    if instance.collide_point(*touch.pos):
                        instance.touch_start_time = time.time()
                        instance.touch_start_pos = touch.pos
                    return False

                return handler

            def make_touch_up(idx):
                def handler(instance, touch):
                    if instance.collide_point(*touch.pos):
                        duration = time.time() - instance.touch_start_time
                        dx = abs(touch.pos[0] - instance.touch_start_pos[0])
                        dy = abs(touch.pos[1] - instance.touch_start_pos[1])
                        if dx < dp(5) and dy < dp(5):
                            if duration > 0.5:
                                self.show_tab_context_menu(idx, instance)
                            else:
                                self._on_tab_press(idx)
                    return False

                return handler

            btn_tab.bind(on_touch_down=make_touch_down())
            btn_tab.bind(on_touch_up=make_touch_up(i))
            tab_box.add_widget(btn_tab)
            if len(self.tabs) > 1:
                btn_close = Button(text='x', font_name='SourceBold', size_hint_x=None, width=dp(20),
                                   background_color=bg_color, background_normal='', background_down='',
                                   color=theme.get('tab_close_btn_text', text_color), font_size=dp(15))
                btn_close.bind(on_release=lambda x, idx=i: self._on_tab_close(idx))

                # ========== ОБЁРТКА КНОПКИ ЗАКРЫТИЯ ==========
                if self.app and hasattr(self.app, 'wrap_widget_buttons'):
                    self.app.wrap_widget_buttons(btn_close)

                tab_box.add_widget(btn_close)
            self.tab_buttons_container.add_widget(tab_box)

    def show_tab_context_menu(self, index, button):
        """Показывает контекстное меню для вкладки."""
        if not self.app:
            return

        tr = self.app.tr
        theme = ThemeManager.get_theme()

        if not button or not button.parent:
            return

        try:
            if hasattr(button, 'to_window'):
                wx, wy = button.to_window(*button.pos)
            else:
                wx, wy = button.pos
        except:
            return

        menu = DropDown()
        menu.auto_width = False
        menu.width = dp(100)

        # ========== ПЕРЕИМЕНОВАТЬ ==========
        btn_rename = Button(
            text=tr.get('rename_tab', 'Переименовать'),
            size_hint_y=None, height=dp(30),
            background_color=theme['widget_bg'],
            background_normal='', background_down='',
            color=theme['text_color'], font_size=dp(11)
        )
        btn_rename.bind(on_release=lambda x: self._rename_tab(index, menu))
        menu.add_widget(btn_rename)

        # ========== ДУБЛИРОВАТЬ ==========
        btn_duplicate = Button(
            text=tr.get('duplicate_tab', 'Дублировать'),
            size_hint_y=None, height=dp(30),
            background_color=theme['widget_bg'],
            background_normal='', background_down='',
            color=theme['text_color'], font_size=dp(11)
        )
        btn_duplicate.bind(on_release=lambda x: self._duplicate_tab(index, menu))  # ← ИСПРАВЛЕНО
        menu.add_widget(btn_duplicate)

        if len(self.tabs) > 1:
            # ========== ЗАКРЫТЬ ДРУГИЕ ==========
            btn_close_others = Button(
                text=tr.get('close_other_tabs', 'Закрыть другие'),
                size_hint_y=None, height=dp(30),
                background_color=theme['widget_bg'],
                background_normal='', background_down='',
                color=theme['text_color'], font_size=dp(11)
            )
            btn_close_others.bind(on_release=lambda x: self._close_other_tabs(index, menu))  # ← ИСПРАВЛЕНО
            menu.add_widget(btn_close_others)

            # ========== ЗАКРЫТЬ ВСЕ ==========
            btn_close_all = Button(
                text=tr.get('close_all_tabs', 'Закрыть все'),
                size_hint_y=None, height=dp(30),
                background_color=theme.get('tab_context_danger_bg', (0.3, 0.1, 0.1, 1)),
                background_normal='', background_down='',
                color=theme['text_color'], font_size=dp(11)
            )
            btn_close_all.bind(on_release=lambda x: self._close_all_tabs(menu))  # ← ИСПРАВЛЕНО
            menu.add_widget(btn_close_all)

        # ========== ДОБАВИТЬ ОБЁРТКУ КНОПОК В КОНТЕКСТНОМ МЕНЮ ==========
        if self.app and hasattr(self.app, 'wrap_widget_buttons'):
            for child in menu.container.children:
                self.app.wrap_widget_buttons(child)

        try:
            menu.open(button)
        except:
            if hasattr(self, 'tab_bar') and self.tab_bar:
                try:
                    menu.open(self.tab_bar)
                except:
                    pass

    def _rename_tab(self, index, menu):
        # ВИБРАЦИЯ
        #if self.app and hasattr(self.app, 'vibrate_short'):
            #self.app.vibrate_short()

        menu.dismiss()
        if self.app:
            self.app._show_rename_tab_dialog(index)

    def _duplicate_tab(self, index, menu):
        # ВИБРАЦИЯ
        #if self.app and hasattr(self.app, 'vibrate_short'):
            #self.app.vibrate_short()

        menu.dismiss()
        if 0 <= index < len(self.tabs):
            tab = self.tabs[index]
            text = tab['editor'].get_text()
            original_title = tab['title']
            match = re.match(r'^(.*?)(?: \((\d+)\))?$', original_title)
            base_title = match.group(1) if match else original_title
            copy_count = 1
            for t in self.tabs:
                m = re.match(r'^' + re.escape(base_title) + r' \((\d+)\)$', t['title'])
                if m:
                    num = int(m.group(1))
                    if num >= copy_count:
                        copy_count = num + 1
                elif t['title'] == base_title:
                    copy_count = max(copy_count, 2)
            new_title = f"{base_title} ({copy_count})"
            editor = self.add_tab(title=new_title, text=text)
            if self.app:
                self.app._on_tab_changed(editor)

    def _close_other_tabs(self, index, menu):
        # ВИБРАЦИЯ
        # if self.app and hasattr(self.app, 'vibrate_short'):
            # self.app.vibrate_short()

        menu.dismiss()
        if 0 <= index < len(self.tabs):
            # Находим целевую вкладку (которую оставляем)
            target_tab = self.tabs[index]

            # Собираем вкладки для закрытия (все, кроме целевой)
            tabs_to_close = []
            for i, t in enumerate(self.tabs):
                if i != index:
                    # Проверяем, есть ли несохранённые изменения
                    current_text = t['editor'].get_text() if t['editor'] else ""
                    original = t.get('original_content', "")
                    if current_text != original and current_text.strip():
                        tabs_to_close.append({
                            'id': t.get('id'),
                            'title': t.get('title', 'Untitled'),
                            'content': current_text,
                            'file': t.get('file'),
                            'tab_obj': t,
                            'tab_index': i
                        })

            if tabs_to_close:
                # Показываем диалог для закрытия других вкладок с несохранёнными
                self._show_close_other_tabs_dialog(target_tab, tabs_to_close)
            else:
                # Нет несохранённых — просто закрываем
                self._do_close_other_tabs(target_tab)

    def _do_close_other_tabs(self, target_tab):
        """Фактическое закрытие других вкладок (без проверки)"""
        for t in self.tabs:
            if t != target_tab and hasattr(t['editor'], 'cleanup'):
                t['editor'].cleanup()
        self.tabs = [target_tab]
        self.active_index = 0
        self._update_tab_bar()
        self.save_all_tabs()
        if self.app:
            self.app._on_tab_changed(target_tab['editor'])

    def _show_close_other_tabs_dialog(self, target_tab, tabs_to_close):
        """Показывает диалог для закрытия других вкладок с несохранёнными"""
        if not self.app:
            return

        tr = self.app.tr
        theme = ThemeManager.get_theme()

        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.button import Button
        from kivy.uix.label import Label
        from kivy.uix.scrollview import ScrollView
        from widgets.dialogs import ThemedPopup

        # Адаптивные размеры
        category = get_screen_category()
        if category == 'tablet':
            padding = dp(20)
            spacing = dp(15)
            msg_height = dp(140)
            btn_height = dp(55)
            font_size_msg = dp(14)
            font_size_btn = dp(14)
            popup_size = (0.8, 0.58)
        elif category == 'large_phone':
            padding = dp(15)
            spacing = dp(12)
            msg_height = dp(125)
            btn_height = dp(50)
            font_size_msg = dp(13)
            font_size_btn = dp(13)
            popup_size = (0.88, 0.6)
        else:
            padding = dp(12)
            spacing = dp(10)
            msg_height = dp(115)
            btn_height = dp(45)
            font_size_msg = dp(12)
            font_size_btn = dp(12)
            popup_size = (0.92, 0.65)

        content = BoxLayout(orientation='vertical', padding=padding, spacing=spacing)

        # Список несохранённых вкладок
        tabs_list = "\n".join([f"• {tab['title']}" for tab in tabs_to_close[:10]])
        if len(tabs_to_close) > 10:
            tabs_list += f"\n... и {len(tabs_to_close) - 10} других"

        message = f"{tr.get('unsaved_changes', 'Unsaved changes')}:\n\n{tabs_list}\n\n{tr.get('close_other_confirm', 'Close other tabs without saving?')}"

        scroll = ScrollView(size_hint=(1, 0.6))
        msg_label = Label(
            text=message,
            color=theme['text_color'],
            font_size=font_size_msg,
            font_name='SourceBold',
            halign='left',
            valign='top',
            size_hint_y=None
        )
        msg_label.bind(width=lambda inst, val: setattr(inst, 'text_size', (val, None)))
        msg_label.bind(texture_size=lambda inst, sz: setattr(inst, 'height', sz[1] + dp(10)))
        scroll.add_widget(msg_label)
        content.add_widget(scroll)

        btn_layout = BoxLayout(size_hint_y=None, height=btn_height, spacing=spacing)

        popup = ThemedPopup(
            title=tr.get('close_other_tabs', 'Close other tabs'),
            title_color=theme['popup_title'],
            title_bg=theme.get('popup_title_bg', theme['widget_bg']),
            popup_bg=theme.get('popup_bg', theme.get('widget_bg', (0.188, 0.204, 0.251, 1))),
            separator_color=theme.get('popup_separator', (0.25, 0.25, 0.25, 1)),
            content=content,
            size_hint=popup_size,
            auto_dismiss=False
        )

        def on_close_others(x):
            popup.dismiss()
            self._do_close_other_tabs(target_tab)

        def on_cancel(x):
            popup.dismiss()

        btn_close_others = Button(
            text=tr.get('close_other_tabs', 'Close others'),
            font_name='SourceBold',
            background_color=theme.get('btn_danger_bg', (0.5, 0.2, 0.2, 1)),
            background_normal='', background_down='',
            color=(1, 1, 1, 1),
            font_size=font_size_btn,
            size_hint=(1, 1),
            on_release=on_close_others
        )

        btn_cancel = Button(
            text=tr.get('cancel', 'Cancel'),
            font_name='SourceBold',
            background_color=theme.get('widget_bg', (0.141, 0.145, 0.149, 1)),
            background_normal='', background_down='',
            color=theme['text_color'],
            font_size=font_size_btn,
            size_hint=(1, 1),
            on_release=on_cancel
        )

        btn_layout.add_widget(btn_cancel)
        btn_layout.add_widget(btn_close_others)
        content.add_widget(btn_layout)

        # Обёртка для вибрации
        if self.app and hasattr(self.app, 'wrap_widget_buttons'):
            self.app.wrap_widget_buttons(content)

        popup.open()

    def _close_all_tabs(self, menu):
        # ВИБРАЦИЯ
        # if self.app and hasattr(self.app, 'vibrate_short'):
            # self.app.vibrate_short()

        menu.dismiss()

        # Проверяем, есть ли несохранённые вкладки
        unsaved_tabs = []
        for tab in self.tabs:
            current_text = tab['editor'].get_text() if tab['editor'] else ""
            original = tab.get('original_content', "")
            if current_text != original and current_text.strip():
                unsaved_tabs.append({
                    'id': tab.get('id'),
                    'title': tab.get('title', 'Untitled'),
                    'content': current_text,
                    'file': tab.get('file')
                })

        if unsaved_tabs:
            # Показываем диалог для закрытия всех вкладок с несохранёнными
            self._show_close_all_tabs_dialog(unsaved_tabs)
        else:
            # Нет несохранённых вкладок — просто закрываем
            self._do_close_all_tabs()

    def _do_close_all_tabs(self):
        """Фактическое закрытие всех вкладок (без проверки)"""
        for tab in self.tabs:
            if hasattr(tab['editor'], 'cleanup'):
                tab['editor'].cleanup()
        self.tabs.clear()
        editor = self.add_tab()
        self.active_index = 0
        self._update_tab_bar()
        self.save_all_tabs()
        if self.app:
            self.app._on_tab_changed(editor)

    def _show_close_all_tabs_dialog(self, unsaved_tabs):
        """Показывает диалог для закрытия всех вкладок с несохранёнными"""
        if not self.app:
            return

        tr = self.app.tr
        theme = ThemeManager.get_theme()

        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.button import Button
        from kivy.uix.label import Label
        from kivy.uix.scrollview import ScrollView
        from widgets.dialogs import ThemedPopup

        # Адаптивные размеры
        category = get_screen_category()
        if category == 'tablet':
            padding = dp(20)
            spacing = dp(15)
            msg_height = dp(140)
            btn_height = dp(55)
            font_size_msg = dp(14)
            font_size_btn = dp(14)
            popup_size = (0.8, 0.58)
        elif category == 'large_phone':
            padding = dp(15)
            spacing = dp(12)
            msg_height = dp(125)
            btn_height = dp(50)
            font_size_msg = dp(13)
            font_size_btn = dp(13)
            popup_size = (0.88, 0.6)
        else:
            padding = dp(12)
            spacing = dp(10)
            msg_height = dp(115)
            btn_height = dp(45)
            font_size_msg = dp(12)
            font_size_btn = dp(12)
            popup_size = (0.92, 0.65)

        content = BoxLayout(orientation='vertical', padding=padding, spacing=spacing)

        # Список несохранённых вкладок
        tabs_list = "\n".join([f"• {tab['title']}" for tab in unsaved_tabs[:10]])
        if len(unsaved_tabs) > 10:
            tabs_list += f"\n... и {len(unsaved_tabs) - 10} других"

        message = f"{tr.get('unsaved_changes', 'Unsaved changes')}:\n\n{tabs_list}\n\n{tr.get('close_all_confirm', 'Close all tabs without saving?')}"

        scroll = ScrollView(size_hint=(1, 0.6))
        msg_label = Label(
            text=message,
            color=theme['text_color'],
            font_size=font_size_msg,
            font_name='SourceBold',
            halign='left',
            valign='top',
            size_hint_y=None
        )
        msg_label.bind(width=lambda inst, val: setattr(inst, 'text_size', (val, None)))
        msg_label.bind(texture_size=lambda inst, sz: setattr(inst, 'height', sz[1] + dp(10)))
        scroll.add_widget(msg_label)
        content.add_widget(scroll)

        btn_layout = BoxLayout(size_hint_y=None, height=btn_height, spacing=spacing)

        popup = ThemedPopup(
            title=tr.get('close_all_tabs', 'Close all tabs'),
            title_color=theme['popup_title'],
            title_bg=theme.get('popup_title_bg', theme['widget_bg']),
            popup_bg=theme.get('popup_bg', theme.get('widget_bg', (0.188, 0.204, 0.251, 1))),
            separator_color=theme.get('popup_separator', (0.25, 0.25, 0.25, 1)),
            content=content,
            size_hint=popup_size,
            auto_dismiss=False
        )

        def on_close_all(x):
            popup.dismiss()
            self._do_close_all_tabs()

        def on_cancel(x):
            popup.dismiss()

        btn_close_all = Button(
            text=tr.get('close_all_tabs', 'Close all'),
            font_name='SourceBold',
            background_color=theme.get('btn_danger_bg', (0.5, 0.2, 0.2, 1)),
            background_normal='', background_down='',
            color=(1, 1, 1, 1),
            font_size=font_size_btn,
            size_hint=(1, 1),
            on_release=on_close_all
        )

        btn_cancel = Button(
            text=tr.get('cancel', 'Cancel'),
            font_name='SourceBold',
            background_color=theme.get('widget_bg', (0.141, 0.145, 0.149, 1)),
            background_normal='', background_down='',
            color=theme['text_color'],
            font_size=font_size_btn,
            size_hint=(1, 1),
            on_release=on_cancel
        )

        btn_layout.add_widget(btn_cancel)
        btn_layout.add_widget(btn_close_all)
        content.add_widget(btn_layout)

        # Обёртка для вибрации
        if self.app and hasattr(self.app, 'wrap_widget_buttons'):
            self.app.wrap_widget_buttons(content)

        popup.open()

    def save_all_tabs(self):
        try:
            tabs_data = {'active_index': self.active_index, 'tabs': []}
            for tab in self.tabs:
                tabs_data['tabs'].append({'title': tab['title'], 'file': tab['file'],
                                          'text': tab['editor'].get_text() if tab['editor'] else ''})
            save_path = user_data_path('tabs.json')
            ensure_user_data_dir()
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(tabs_data, f, indent=2)
        except:
            pass

    def load_all_tabs(self):
        try:
            save_path = user_data_path('tabs.json')
            if not os.path.exists(save_path):
                return False
            with open(save_path, 'r', encoding='utf-8') as f:
                saved_data = json.load(f)
            if isinstance(saved_data, list):
                tabs_data = saved_data
                active_index = 0
            else:
                tabs_data = saved_data.get('tabs', [])
                active_index = saved_data.get('active_index', 0)
            if not tabs_data:
                return False
            self.tabs.clear()
            tr = self.app.tr if self.app else {}
            for data in tabs_data:
                editor = LineNumberTextInput(size_hint_y=1.0)

                if hasattr(editor, 'rebind_touch_handlers'):
                    editor.rebind_touch_handlers()
                    
                text = data.get('text', '')
                if text and text.strip():
                    editor.set_text(text)
                else:
                    editor.set_text('')

                file_path = data.get('file')

                tab = {
                    'id': data.get('id', str(uuid.uuid4())),  # ← загружаем ID или создаём новый
                    'title': data.get('title', tr.get('untitled_tab', 'Новый')),
                    'editor': editor,
                    'file': file_path,
                    'original_content': text,
                    'saved': True
                }
                self.tabs.append(tab)
            if 0 <= active_index < len(self.tabs):
                self.active_index = active_index
            else:
                self.active_index = 0
            self._update_tab_bar()
            return True
        except:
            return False

    def is_tab_saved(self, index):
        """Проверяет, сохранена ли вкладка"""
        if 0 <= index < len(self.tabs):
            return self.tabs[index].get('saved', True)
        return True
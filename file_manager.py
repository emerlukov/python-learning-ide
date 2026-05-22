# file_manager.py - Файловый менеджер с поддержкой SAF для Android

import os
import threading
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.utils import platform
from kivy.uix.behaviors import ButtonBehavior
from kivy.graphics import Color, Rectangle

from kivymd.uix.label import MDIcon
from kivymd.uix.button import MDRectangleFlatButton, MDIconButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.scrollview import MDScrollView

# ====================== ИМПОРТ ТЕМ ======================
try:
    from main import DARK_THEME, LIGHT_THEME, ThemeManager
except ImportError:
    DARK_THEME = {'name': 'dark'}
    LIGHT_THEME = {'name': 'light'}
    ThemeManager = None

# Расширения текстовых файлов
TEXT_EXTENSIONS = {
    '.py', '.txt', '.md', '.json', '.xml', '.html', '.htm', '.css', '.js',
    '.csv', '.log', '.ini', '.yaml', '.yml', '.toml', '.env', '.gitignore'
}


class ClickableRow(ButtonBehavior, MDBoxLayout):
    pass


class FileNode:
    def __init__(self, path, is_dir=False, size=0, name=None):
        self.path = path
        self.name = name or os.path.basename(path)
        self.is_dir = is_dir
        self.size = size
        self.extension = os.path.splitext(self.name)[1].lower() if not is_dir else ''

    @property
    def icon_name(self):
        if self.is_dir:
            return 'folder'
        if self.extension == '.py':
            return 'language-python'
        if self.extension in ('.txt', '.md'):
            return 'file-document'
        if self.extension in ('.json', '.xml', '.yaml', '.yml'):
            return 'code-json'
        return 'file'

    def format_size(self):
        if self.is_dir:
            return ""
        size = self.size
        for unit in ['B', 'KB', 'MB']:
            if size < 1024:
                return f"{int(size)} {unit}" if unit == 'B' else f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} GB"


class FileManager:
    def __init__(self, app):
        self.app = app
        self.current_path = self._get_default_path()
        self._loading = False
        # Для SAF на Android
        self._saf_enabled = False
        self._saf_root_uri = None

    def _get_default_path(self):
        if platform == 'android':
            # На Android 11+ используем доступные пути
            paths = [
                '/storage/emulated/0/Download',
                '/storage/emulated/0/Documents',
                '/storage/emulated/0',
                '/sdcard'
            ]
            for p in paths:
                if os.path.exists(p) and os.access(p, os.R_OK):
                    return p
            return '/storage/emulated/0'
        return os.path.expanduser('~')

    def set_saf_root(self, uri):
        """Устанавливает корневой URI для SAF доступа"""
        self._saf_root_uri = uri
        self._saf_enabled = True

    def navigate_to(self, path):
        if os.path.exists(path) and os.path.isdir(path):
            self.current_path = os.path.abspath(path)
            return True
        return False

    def go_up(self):
        parent = os.path.dirname(self.current_path)
        if parent and parent != self.current_path:
            self.current_path = parent
            return True
        return False

    def list_files(self, callback):
        if self._loading:
            callback([], self.current_path, "Loading...")
            return

        def load():
            self._loading = True
            folders = []
            files = []

            try:
                for item in os.listdir(self.current_path):
                    if item.startswith('.'):
                        continue

                    full_path = os.path.join(self.current_path, item)
                    try:
                        if os.path.isdir(full_path):
                            folders.append(FileNode(full_path, is_dir=True))
                        else:
                            # Добавляем ВСЕ файлы, а не только текстовые
                            try:
                                size = os.path.getsize(full_path)
                                files.append(FileNode(full_path, is_dir=False, size=size))
                            except (PermissionError, OSError):
                                files.append(FileNode(full_path, is_dir=False, size=0))
                    except (PermissionError, OSError):
                        continue

                folders.sort(key=lambda x: x.name.lower())
                files.sort(key=lambda x: x.name.lower())
                Clock.schedule_once(lambda dt: callback(folders + files, self.current_path, None))

            except PermissionError:
                Clock.schedule_once(lambda dt: callback([], self.current_path, "Нет доступа к папке"))
            except Exception as e:
                Clock.schedule_once(lambda dt: callback([], self.current_path, str(e)))
            finally:
                self._loading = False

        threading.Thread(target=load, daemon=True).start()

    def read_file(self, file_path, callback):
        def read():
            try:
                # Пробуем разные кодировки
                for encoding in ['utf-8', 'utf-8-sig', 'cp1251', 'latin-1']:
                    try:
                        with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                            content = f.read()
                        Clock.schedule_once(lambda dt: callback(content, None))
                        return
                    except UnicodeDecodeError:
                        continue
                # Если ничего не подошло
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                Clock.schedule_once(lambda dt: callback(content, None))
            except PermissionError:
                Clock.schedule_once(lambda dt: callback(None, "Нет прав на чтение файла"))
            except Exception as e:
                Clock.schedule_once(lambda dt: callback(None, str(e)))

        threading.Thread(target=read, daemon=True).start()

    def save_file(self, file_path, content, callback):
        def save():
            try:
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                Clock.schedule_once(lambda dt: callback(True, None))
            except PermissionError:
                Clock.schedule_once(lambda dt: callback(False, "Нет прав на запись"))
            except Exception as e:
                Clock.schedule_once(lambda dt: callback(False, str(e)))

        threading.Thread(target=save, daemon=True).start()

    def delete_file(self, file_path, callback):
        def delete():
            try:
                os.remove(file_path)
                Clock.schedule_once(lambda dt: callback(True, None))
            except Exception as e:
                Clock.schedule_once(lambda dt: callback(False, str(e)))

        threading.Thread(target=delete, daemon=True).start()

    def rename_file(self, old_path, new_name, callback):
        def rename():
            try:
                new_path = os.path.join(os.path.dirname(old_path), new_name)
                os.rename(old_path, new_path)
                Clock.schedule_once(lambda dt: callback(True, new_path, None))
            except Exception as e:
                Clock.schedule_once(lambda dt: callback(False, None, str(e)))

        threading.Thread(target=rename, daemon=True).start()


class FileBrowserPopup:
    def __init__(self, app, file_manager, title=None, mode="open"):
        self.app = app
        self.fm = file_manager
        self.mode = mode
        self.popup = None
        self.callback = None
        self._current_items = []
        self._selected_item = None
        self._title = title or ("Open file" if mode == "open" else "Save file")

    def _tr(self, key, fallback=""):
        if hasattr(self.app, 'tr') and self.app.tr:
            return self.app.tr.get(key, fallback)
        return fallback

    def _get_theme(self):
        try:
            if ThemeManager is not None:
                theme = ThemeManager.get_theme()
                if theme and isinstance(theme, dict) and 'name' in theme:
                    return theme
        except Exception as e:
            pass
        return DARK_THEME

    def show(self, callback, save_filename="script.py"):
        self.callback = callback
        self.save_filename = save_filename
        self._show_browser()

    def _show_browser(self):
        theme = self._get_theme()
        text_color = theme.get('text_color', (0, 0, 0, 1))
        tr = self._tr

        content = MDBoxLayout(orientation='vertical', padding=dp(5), spacing=dp(5))

        # Устанавливаем фон
        with content.canvas.before:
            self._bg_color = Color(*theme.get('app_bg', (1, 1, 1, 1)))
            self._bg_rect = Rectangle(pos=content.pos, size=content.size)
        content.bind(pos=self._update_bg, size=self._update_bg)

        # Путь
        self.path_label = Label(
            text=self.fm.current_path,
            font_size=dp(10),
            font_name='SourceBold',
            color=theme.get('stats_text', (0.6, 0.6, 0.6, 1)),
            size_hint_y=None,
            height=dp(25),
            shorten=True,
            shorten_from='left'
        )
        content.add_widget(self.path_label)

        # Список файлов
        self.file_list = MDScrollView()
        self.file_container = MDBoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(1))
        self.file_container.bind(minimum_height=self.file_container.setter('height'))
        self.file_list.add_widget(self.file_container)
        content.add_widget(self.file_list)

        # Кнопка "Наверх"
        up_btn = MDRectangleFlatButton(
            text=tr('up_level', 'Up'),
            size_hint_y=None,
            height=dp(30),
            line_color=theme.get('separator_color', (0.5, 0.5, 0.5, 0.5)),
            text_color=text_color
        )
        up_btn.bind(on_release=lambda x: self._go_up())
        content.add_widget(up_btn)

        # Поле ввода имени (для сохранения)
        if self.mode == "save":
            self.filename_input = MDTextField(
                text=self.save_filename,
                hint_text=tr('file_name', 'File name...'),
                size_hint_y=None,
                height=dp(45),
                mode="rectangle"
            )
            self.filename_input.line_color_normal = theme.get('separator_color', (0.5, 0.5, 0.5, 0.5))
            self.filename_input.text_color = text_color
            self.filename_input.hint_text_color = theme.get('stats_text', (0.5, 0.5, 0.5, 1))
            content.add_widget(self.filename_input)

        # Кнопки
        btn_layout = MDBoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))

        cancel_btn = MDRectangleFlatButton(
            text=tr('cancel', 'Cancel'),
            line_color=theme.get('separator_color', (0.5, 0.5, 0.5, 0.5)),
            text_color=text_color
        )
        cancel_btn.bind(on_release=lambda x: self._dismiss())

        action_text = tr('save', 'Save') if self.mode == "save" else tr('open', 'Open')
        action_btn = MDRectangleFlatButton(
            text=action_text,
            text_color=(1, 1, 1, 1),
            md_bg_color=theme.get('btn_success_bg', (0.2, 0.5, 0.2, 1))
        )
        action_btn.bind(on_release=lambda x: self._on_action())

        btn_layout.add_widget(cancel_btn)
        btn_layout.add_widget(action_btn)
        content.add_widget(btn_layout)

        self.popup = Popup(
            title=self._title,
            title_color=theme.get('popup_title', (0, 0, 0, 1)),
            title_size=dp(14),
            separator_color=theme.get('separator_color', (0.5, 0.5, 0.5, 1)),
            background='',
            background_color=theme.get('popup_bg', (1, 1, 1, 1)),
            content=content,
            size_hint=(0.92, 0.85),
            auto_dismiss=False
        )

        self.popup.open()
        self._refresh_list()

    def _update_bg(self, instance, value):
        if hasattr(self, '_bg_rect'):
            self._bg_rect.pos = instance.pos
            self._bg_rect.size = instance.size

    def _go_up(self):
        if self.fm.go_up():
            self._refresh_list()

    def _refresh_list(self):
        if self.file_container:
            self.file_container.clear_widgets()
        if self.path_label:
            self.path_label.text = self.fm.current_path
        self.fm.list_files(self._update_list)

    def _update_list(self, items, current_path, error):
        if not self.file_container:
            return

        self.file_container.clear_widgets()
        self.path_label.text = current_path
        self._current_items = items

        theme = self._get_theme()
        text_color = theme.get('text_color', (0, 0, 0, 1))
        selected_bg = theme.get('btn_selected_file_bg', (0.3, 0.5, 0.3, 0.5))
        widget_bg = theme.get('widget_bg', (0.95, 0.95, 0.95, 1))
        tr = self._tr

        if error:
            self.file_container.add_widget(Label(
                text=error,
                size_hint_y=None,
                height=dp(40),
                color=(0.8, 0.2, 0.2, 1)
            ))
            return

        if not items:
            self.file_container.add_widget(Label(
                text=tr('empty_folder', 'Empty folder'),
                size_hint_y=None,
                height=dp(50),
                color=text_color
            ))
            return

        for item in items:
            row = ClickableRow(
                orientation='horizontal',
                size_hint_y=None,
                height=dp(44),
                spacing=dp(8),
                padding=[dp(8), dp(4), dp(8), dp(4)]
            )

            # Фон строки
            with row.canvas.before:
                Color(*widget_bg)
                row._bg_rect = Rectangle(pos=row.pos, size=row.size)
            row.bind(pos=self._update_row_bg, size=self._update_row_bg)

            # Подсветка выбранного файла
            if self._selected_item == item.path:
                with row.canvas.after:
                    Color(*selected_bg)
                    row._selected_rect = Rectangle(pos=row.pos, size=row.size)
                row.bind(pos=self._update_selected_rect, size=self._update_selected_rect)

            icon = MDIcon(
                icon=item.icon_name,
                font_size=dp(22),
                theme_text_color="Custom",
                text_color=text_color,
                size_hint_x=None,
                width=dp(40)
            )
            row.add_widget(icon)

            name_label = Label(
                text=item.name,
                font_size=dp(12),
                color=text_color,
                halign='left',
                size_hint_x=1
            )
            row.add_widget(name_label)

            if not item.is_dir and item.size > 0:
                size_label = Label(
                    text=item.format_size(),
                    font_size=dp(9),
                    color=theme.get('stats_text', (0.5, 0.5, 0.5, 1)),
                    size_hint_x=None,
                    width=dp(50),
                    halign='right'
                )
                row.add_widget(size_label)

            menu_btn = MDIconButton(
                icon='dots-vertical',
                icon_size=dp(20),
                size_hint_x=None,
                width=dp(40),
                theme_icon_color="Custom",
                icon_color=text_color
            )
            menu_btn.bind(on_release=lambda btn, it=item: self._show_menu(btn, it))
            row.add_widget(menu_btn)

            if item.is_dir:
                row.bind(on_release=lambda x, p=item.path: self._open_folder(p))
            else:
                row.bind(on_release=lambda x, p=item.path: self._select_file(p))

            self.file_container.add_widget(row)

    def _update_row_bg(self, instance, value):
        if hasattr(instance, '_bg_rect'):
            instance._bg_rect.pos = instance.pos
            instance._bg_rect.size = instance.size

    def _update_selected_rect(self, instance, value):
        if hasattr(instance, '_selected_rect'):
            instance._selected_rect.pos = instance.pos
            instance._selected_rect.size = instance.size

    def _open_folder(self, path):
        self.fm.navigate_to(path)
        self._refresh_list()
        self._selected_item = None

    def _select_file(self, path):
        self._selected_item = path
        self._refresh_list()

    def _show_menu(self, button, item):
        theme = self._get_theme()
        text_color = theme.get('text_color', (0, 0, 0, 1))
        tr = self._tr

        content = MDBoxLayout(orientation='vertical', padding=dp(8), spacing=dp(5), size_hint_y=None)
        content.height = dp(130)

        if not item.is_dir:
            btn_open = MDRectangleFlatButton(
                text=tr('open', 'Open'),
                size_hint_y=None,
                height=dp(40),
                line_color=theme.get('separator_color', (0.5, 0.5, 0.5, 0.5)),
                text_color=text_color
            )
            btn_open.bind(on_release=lambda x: self._open_item(item))
            content.add_widget(btn_open)

        btn_rename = MDRectangleFlatButton(
            text=tr('rename', 'Rename'),
            size_hint_y=None,
            height=dp(40),
            line_color=theme.get('separator_color', (0.5, 0.5, 0.5, 0.5)),
            text_color=text_color
        )
        btn_rename.bind(on_release=lambda x: self._rename_item(item))
        content.add_widget(btn_rename)

        btn_delete = MDRectangleFlatButton(
            text=tr('delete', 'Delete'),
            size_hint_y=None,
            height=dp(40),
            md_bg_color=theme.get('btn_danger_bg', (0.5, 0.2, 0.2, 1)),
            text_color=(1, 1, 1, 1)
        )
        btn_delete.bind(on_release=lambda x: self._delete_item(item))
        content.add_widget(btn_delete)

        menu_popup = Popup(
            title=tr('actions', 'Actions'),
            title_color=theme.get('popup_title', (0, 0, 0, 1)),
            separator_color=theme.get('separator_color', (0.5, 0.5, 0.5, 1)),
            background='',
            background_color=theme.get('popup_bg', (1, 1, 1, 1)),
            content=content,
            size_hint=(0.6, None),
            height=dp(190) if not item.is_dir else dp(150),
            auto_dismiss=True
        )
        menu_popup.open()

    def _open_item(self, item):
        if item.is_dir:
            self.fm.navigate_to(item.path)
            self._refresh_list()
            self._selected_item = None
        else:
            self._load_and_close(item.path)

    def _rename_item(self, item):
        theme = self._get_theme()
        text_color = theme.get('text_color', (0, 0, 0, 1))
        tr = self._tr

        content = MDBoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        content.add_widget(Label(
            text=f"{tr('rename', 'Rename')}: {item.name}",
            color=text_color,
            font_size=dp(12)
        ))

        name_input = MDTextField(
            text=item.name,
            size_hint_y=None,
            height=dp(45),
            mode="rectangle"
        )
        name_input.line_color_normal = theme.get('separator_color', (0.5, 0.5, 0.5, 0.5))
        name_input.text_color = text_color
        content.add_widget(name_input)

        btn_layout = MDBoxLayout(size_hint_y=None, height=dp(40), spacing=dp(10))

        popup = Popup(
            title=tr('rename', 'Rename'),
            title_color=theme.get('popup_title', (0, 0, 0, 1)),
            separator_color=theme.get('separator_color', (0.5, 0.5, 0.5, 1)),
            background='',
            background_color=theme.get('popup_bg', (1, 1, 1, 1)),
            content=content,
            size_hint=(0.8, 0.35),
            auto_dismiss=False
        )

        def do_rename(btn):
            new_name = name_input.text.strip()
            if new_name and new_name != item.name:
                def callback(success, new_path, error):
                    popup.dismiss()
                    if success:
                        self._refresh_list()
                        self.app.show_result_popup(f"{tr('renamed', 'Renamed')}: {new_name}")
                    else:
                        self.app.show_result_popup(f"{tr('error', 'Error')}: {error}")

                self.fm.rename_file(item.path, new_name, callback)
            else:
                popup.dismiss()

        btn_ok = MDRectangleFlatButton(
            text=tr('ok', 'OK'),
            text_color=(1, 1, 1, 1),
            md_bg_color=theme.get('btn_success_bg', (0.2, 0.5, 0.2, 1))
        )
        btn_ok.bind(on_release=do_rename)
        btn_cancel = MDRectangleFlatButton(
            text=tr('cancel', 'Cancel'),
            line_color=theme.get('separator_color', (0.5, 0.5, 0.5, 0.5)),
            text_color=text_color
        )
        btn_cancel.bind(on_release=lambda x: popup.dismiss())

        btn_layout.add_widget(btn_cancel)
        btn_layout.add_widget(btn_ok)
        content.add_widget(btn_layout)

        popup.open()
        Clock.schedule_once(lambda dt: setattr(name_input, 'focus', True), 0.3)

    def _delete_item(self, item):
        theme = self._get_theme()
        text_color = theme.get('text_color', (0, 0, 0, 1))
        tr = self._tr

        content = MDBoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        content.add_widget(Label(
            text=f"{tr('delete_confirm', 'Delete')} {item.name}?",
            color=text_color,
            font_size=dp(14)
        ))
        if not item.is_dir:
            content.add_widget(Label(
                text=tr('cannot_undo', 'This cannot be undone'),
                color=(0.7, 0.2, 0.2, 1),
                font_size=dp(10)
            ))

        btn_layout = MDBoxLayout(size_hint_y=None, height=dp(40), spacing=dp(10))

        popup = Popup(
            title=tr('confirm', 'Confirm'),
            title_color=theme.get('popup_title', (0, 0, 0, 1)),
            separator_color=theme.get('separator_color', (0.5, 0.5, 0.5, 1)),
            background='',
            background_color=theme.get('popup_bg', (1, 1, 1, 1)),
            content=content,
            size_hint=(0.7, 0.25),
            auto_dismiss=False
        )

        def do_delete(btn):
            popup.dismiss()

            def callback(success, error):
                if success:
                    self._refresh_list()
                    self.app.show_result_popup(f"{tr('deleted', 'Deleted')}: {item.name}")
                else:
                    self.app.show_result_popup(f"{tr('error', 'Error')}: {error}")

            self.fm.delete_file(item.path, callback)

        btn_delete = MDRectangleFlatButton(
            text=tr('delete', 'Delete'),
            text_color=(1, 1, 1, 1),
            md_bg_color=theme.get('btn_danger_bg', (0.5, 0.2, 0.2, 1))
        )
        btn_delete.bind(on_release=do_delete)
        btn_cancel = MDRectangleFlatButton(
            text=tr('cancel', 'Cancel'),
            line_color=theme.get('separator_color', (0.5, 0.5, 0.5, 0.5)),
            text_color=text_color
        )
        btn_cancel.bind(on_release=lambda x: popup.dismiss())

        btn_layout.add_widget(btn_cancel)
        btn_layout.add_widget(btn_delete)
        content.add_widget(btn_layout)

        popup.open()

    def _load_and_close(self, file_path):
        def on_loaded(content, error):
            self._dismiss()
            if error:
                self.app.show_result_popup(f"Error: {error}")
            elif self.callback:
                self.callback(file_path, content)

        self.fm.read_file(file_path, on_loaded)

    def _on_action(self):
        tr = self._tr

        if self.mode == "save":
            filename = self.filename_input.text.strip()
            if not filename:
                filename = "script.py"
            if '.' not in filename:
                filename += '.py'

            full_path = os.path.join(self.fm.current_path, filename)
            content = self.app.code_input.text if hasattr(self.app, 'code_input') else ""

            if os.path.exists(full_path):
                self._confirm_overwrite(full_path, content, filename)
                return

            def on_saved(success, error):
                self._dismiss()
                if success:
                    self.app.show_result_popup(f"{tr('saved', 'Saved')}: {filename}")
                    if self.callback:
                        self.callback(full_path, content)
                else:
                    self.app.show_result_popup(f"{tr('error', 'Error')}: {error}")

            self.fm.save_file(full_path, content, on_saved)

        else:
            if self._selected_item:
                self._load_and_close(self._selected_item)
            else:
                self.app.show_result_popup(tr('select_file', 'Select a file first'))

    def _confirm_overwrite(self, full_path, content, filename):
        theme = self._get_theme()
        text_color = theme.get('text_color', (0, 0, 0, 1))
        tr = self._tr

        content_box = MDBoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        content_box.add_widget(Label(
            text=f"{tr('file_exists', 'File')} '{filename}' {tr('already_exists', 'exists')}.\n{tr('overwrite_prompt', 'Overwrite?')}",
            color=text_color,
            halign='center'
        ))

        btn_layout = MDBoxLayout(size_hint_y=None, height=dp(40), spacing=dp(10))

        popup = Popup(
            title=tr('confirm', 'Confirm'),
            title_color=theme.get('popup_title', (0, 0, 0, 1)),
            separator_color=theme.get('separator_color', (0.5, 0.5, 0.5, 1)),
            background='',
            background_color=theme.get('popup_bg', (1, 1, 1, 1)),
            content=content_box,
            size_hint=(0.7, 0.25),
            auto_dismiss=False
        )

        def on_yes(btn):
            popup.dismiss()

            def on_saved(success, error):
                self._dismiss()
                if success:
                    self.app.show_result_popup(f"{tr('saved', 'Saved')}: {filename}")
                    if self.callback:
                        self.callback(full_path, content)
                else:
                    self.app.show_result_popup(f"{tr('error', 'Error')}: {error}")

            self.fm.save_file(full_path, content, on_saved)

        btn_yes = MDRectangleFlatButton(
            text=tr('yes', 'Yes'),
            text_color=(1, 1, 1, 1),
            md_bg_color=theme.get('btn_success_bg', (0.2, 0.5, 0.2, 1))
        )
        btn_yes.bind(on_release=on_yes)
        btn_no = MDRectangleFlatButton(
            text=tr('no', 'No'),
            line_color=theme.get('separator_color', (0.5, 0.5, 0.5, 0.5)),
            text_color=text_color
        )
        btn_no.bind(on_release=lambda x: popup.dismiss())

        btn_layout.add_widget(btn_no)
        btn_layout.add_widget(btn_yes)
        content_box.add_widget(btn_layout)

        popup.open()

    def _dismiss(self):
        if self.popup:
            self.popup.dismiss()
            self.popup = None

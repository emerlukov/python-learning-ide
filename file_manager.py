# file_manager.py - Файловый менеджер с сортировкой и локализацией

import os
import threading
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.utils import platform
from kivy.uix.behaviors import ButtonBehavior
from kivy.graphics import Color, Rectangle
import time

from kivymd.uix.label import MDIcon
from kivymd.uix.button import MDRectangleFlatButton, MDIconButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.scrollview import MDScrollView

# ====================== ИМПОРТ ТЕМ ======================
try:
    from main import DARK_THEME, LIGHT_THEME, ThemeManager
except ImportError:
    DARK_THEME = {'name': 'dark', 'app_bg': (0.188, 0.204, 0.251, 1), 'text_color': (0.85, 0.88, 0.90, 1)}
    LIGHT_THEME = {'name': 'light', 'app_bg': (1, 1, 1, 1), 'text_color': (0, 0, 0, 1)}
    ThemeManager = None

# ====================== ГЛОБАЛЬНЫЕ КОНСТАНТЫ ======================
# Расширения текстовых файлов
TEXT_EXTENSIONS = {
    '.py', '.txt', '.md', '.json', '.xml', '.html', '.htm', '.css', '.js',
    '.csv', '.log', '.ini', '.yaml', '.yml', '.toml', '.env', '.gitignore',
    '.rst', '.tex', '.c', '.cpp', '.h', '.java', '.kt', '.kts', '.swift',
    '.go', '.rs', '.rb', '.php', '.sql', '.sh', '.bat', '.ps1', '.cfg',
    '.conf', '.properties', '.gradle', '.svg', '.vue', '.jsx', '.tsx',
    '.ts', '.scss', '.sass', '.less', '.coffee'
}

# Цвета
PURPLE = (0.596, 0.486, 1.0, 1)
PURPLE_LIGHT = (0.7, 0.6, 1.0, 0.3)
SORT_ACTIVE = (0.8, 0.7, 1.0, 1)


class ClickableRow(ButtonBehavior, MDBoxLayout):
    pass


class FileNode:
    __slots__ = ('path', 'name', 'is_dir', 'size', 'extension', 'mtime')

    def __init__(self, path, is_dir=False, size=0, mtime=0, name=None):
        self.path = path
        self.name = name or os.path.basename(path)
        self.is_dir = is_dir
        self.size = size
        self.mtime = mtime
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

    def format_date(self, tr):
        """Возвращает отформатированную дату изменения с локализацией"""
        if self.mtime == 0:
            return ""
        from datetime import datetime
        dt = datetime.fromtimestamp(self.mtime)
        return dt.strftime(f"%d.%m.%Y %H:%M")


class SortManager:
    """Управляет сортировкой файлов"""
    SORT_NAME = 'name'
    SORT_DATE = 'date'
    SORT_SIZE = 'size'

    def __init__(self):
        self.current_sort = self.SORT_NAME
        self.reverse = False

    def sort_items(self, folders, files):
        """Сортирует папки и файлы по текущему критерию"""
        if self.current_sort == self.SORT_NAME:
            folders.sort(key=lambda x: x.name.lower(), reverse=self.reverse)
            files.sort(key=lambda x: x.name.lower(), reverse=self.reverse)
        elif self.current_sort == self.SORT_DATE:
            folders.sort(key=lambda x: x.mtime, reverse=not self.reverse)
            files.sort(key=lambda x: x.mtime, reverse=not self.reverse)
        elif self.current_sort == self.SORT_SIZE:
            files.sort(key=lambda x: x.size, reverse=not self.reverse)
            folders.sort(key=lambda x: 0, reverse=False)

        return folders + files

    def get_sort_icon(self):
        if self.current_sort == self.SORT_NAME:
            return 'sort-alphabetical' + ('-descending' if self.reverse else '-ascending')
        elif self.current_sort == self.SORT_DATE:
            return 'calendar' + ('-descending' if self.reverse else '-ascending')
        else:
            return 'sort' + ('-descending' if self.reverse else '-ascending')

    def next_sort(self):
        if self.current_sort == self.SORT_NAME:
            self.current_sort = self.SORT_DATE
        elif self.current_sort == self.SORT_DATE:
            self.current_sort = self.SORT_SIZE
        else:
            self.current_sort = self.SORT_NAME
        self.reverse = False
        return self.current_sort

    def toggle_reverse(self):
        self.reverse = not self.reverse
        return self.reverse


class FileManager:
    def __init__(self, app):
        self.app = app
        self.current_path = self._get_default_path()
        self._loading = False
        self._cache = {}
        self._cache_time = {}
        self._cache_ttl = 3
        self.sort_manager = SortManager()

    def _get_default_path(self):
        if platform == 'android':
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

    def navigate_to(self, path):
        if os.path.exists(path) and os.path.isdir(path):
            self.current_path = os.path.abspath(path)
            self._cache.pop(self.current_path, None)
            return True
        return False

    def go_up(self):
        parent = os.path.dirname(self.current_path)
        if parent and parent != self.current_path:
            self.current_path = parent
            self._cache.pop(self.current_path, None)
            return True
        return False

    def list_files(self, callback, force_refresh=False):
        if self._loading:
            callback([], self.current_path, "Загрузка...")
            return

        current_time = time.time()
        if not force_refresh and self.current_path in self._cache:
            cache_time = self._cache_time.get(self.current_path, 0)
            if current_time - cache_time < self._cache_ttl:
                items = self._cache[self.current_path]
                Clock.schedule_once(lambda dt: callback(items, self.current_path, None))
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
                            try:
                                stat = os.stat(full_path)
                                mtime = stat.st_mtime
                            except:
                                mtime = 0
                            folders.append(FileNode(full_path, is_dir=True, mtime=mtime))
                        else:
                            ext = os.path.splitext(item)[1].lower()
                            if ext in TEXT_EXTENSIONS:
                                try:
                                    stat = os.stat(full_path)
                                    size = stat.st_size
                                    mtime = stat.st_mtime
                                    files.append(FileNode(full_path, is_dir=False, size=size, mtime=mtime))
                                except:
                                    pass
                    except:
                        continue

                all_items = self.sort_manager.sort_items(folders, files)

                self._cache[self.current_path] = all_items
                self._cache_time[self.current_path] = time.time()

                Clock.schedule_once(lambda dt: callback(all_items, self.current_path, None))

            except PermissionError:
                Clock.schedule_once(lambda dt: callback([], self.current_path, "Нет доступа"))
            except Exception as e:
                Clock.schedule_once(lambda dt: callback([], self.current_path, str(e)))
            finally:
                self._loading = False

        threading.Thread(target=load, daemon=True).start()

    def set_sort(self, sort_type, reverse=False):
        self.sort_manager.current_sort = sort_type
        self.sort_manager.reverse = reverse
        self._cache.pop(self.current_path, None)
        return True

    def toggle_sort_direction(self):
        reverse = self.sort_manager.toggle_reverse()
        self._cache.pop(self.current_path, None)
        return reverse

    def read_file(self, file_path, callback):
        def read():
            try:
                for encoding in ['utf-8', 'utf-8-sig', 'cp1251', 'latin-1']:
                    try:
                        with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                            content = f.read()
                        Clock.schedule_once(lambda dt: callback(content, None))
                        return
                    except UnicodeDecodeError:
                        continue
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                Clock.schedule_once(lambda dt: callback(content, None))
            except Exception as e:
                Clock.schedule_once(lambda dt: callback(None, str(e)))

        threading.Thread(target=read, daemon=True).start()

    def save_file(self, file_path, content, callback):
        def save():
            try:
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                self._cache.pop(os.path.dirname(file_path), None)
                Clock.schedule_once(lambda dt: callback(True, None))
            except Exception as e:
                Clock.schedule_once(lambda dt: callback(False, str(e)))

        threading.Thread(target=save, daemon=True).start()

    def delete_file(self, file_path, callback):
        def delete():
            try:
                os.remove(file_path)
                self._cache.pop(os.path.dirname(file_path), None)
                Clock.schedule_once(lambda dt: callback(True, None))
            except Exception as e:
                Clock.schedule_once(lambda dt: callback(False, str(e)))

        threading.Thread(target=delete, daemon=True).start()

    def rename_file(self, old_path, new_name, callback):
        def rename():
            try:
                new_path = os.path.join(os.path.dirname(old_path), new_name)
                os.rename(old_path, new_path)
                self._cache.pop(os.path.dirname(old_path), None)
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
        self._selected_item = None
        self._title = title or ("Open file" if mode == "open" else "Save file")
        self._sort_type = 'name'
        self._sort_reverse = False

    def _tr(self, key, fallback=""):
        if hasattr(self.app, 'tr') and self.app.tr:
            return self.app.tr.get(key, fallback)
        return fallback

    def _get_bg_color(self):
        try:
            if ThemeManager is not None:
                theme = ThemeManager.get_theme()
                if theme and theme.get('name') == 'dark':
                    return (0.188, 0.204, 0.251, 1)
                else:
                    return (1, 1, 1, 1)
        except:
            pass
        return (0.188, 0.204, 0.251, 1)

    def show(self, callback, save_filename="script.py"):
        self.callback = callback
        self.save_filename = save_filename
        self._show_browser()

    def _show_browser(self):
        bg_color = self._get_bg_color()
        tr = self._tr

        content = MDBoxLayout(orientation='vertical', padding=dp(5), spacing=dp(5))

        with content.canvas.before:
            self._bg_color = Color(*bg_color)
            self._bg_rect = Rectangle(pos=content.pos, size=content.size)
        content.bind(pos=self._update_bg, size=self._update_bg)

        # Путь
        self.path_label = Label(
            text=self.fm.current_path,
            font_size=dp(10),
            font_name='SourceBold',
            color=(0.6, 0.6, 0.6, 1),
            size_hint_y=None,
            height=dp(25),
            shorten=True,
            shorten_from='left'
        )
        content.add_widget(self.path_label)

        # Панель сортировки
        sort_bar = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=dp(35), spacing=dp(5),
                               padding=[dp(5), dp(2)])

        # Кнопка сортировки по имени
        self.sort_name_btn = MDRectangleFlatButton(
            text=tr('sort_by_name', 'By name'),
            size_hint_x=0.33,
            font_size=dp(10),
            line_color=PURPLE,
            text_color=PURPLE
        )
        self.sort_name_btn.bind(on_release=lambda x: self._apply_sort('name'))

        # Кнопка сортировки по дате
        self.sort_date_btn = MDRectangleFlatButton(
            text=tr('sort_by_date', 'By date'),
            size_hint_x=0.33,
            font_size=dp(10),
            line_color=PURPLE,
            text_color=PURPLE
        )
        self.sort_date_btn.bind(on_release=lambda x: self._apply_sort('date'))

        # Кнопка сортировки по размеру
        self.sort_size_btn = MDRectangleFlatButton(
            text=tr('sort_by_size', 'By size'),
            size_hint_x=0.33,
            font_size=dp(10),
            line_color=PURPLE,
            text_color=PURPLE
        )
        self.sort_size_btn.bind(on_release=lambda x: self._apply_sort('size'))

        # Кнопка реверса
        self.sort_reverse_btn = MDIconButton(
            icon='arrow-up',
            icon_size=dp(20),
            size_hint_x=None,
            width=dp(40),
            theme_icon_color="Custom",
            icon_color=PURPLE
        )
        self.sort_reverse_btn.bind(on_release=lambda x: self._toggle_reverse())

        sort_bar.add_widget(self.sort_name_btn)
        sort_bar.add_widget(self.sort_date_btn)
        sort_bar.add_widget(self.sort_size_btn)
        sort_bar.add_widget(self.sort_reverse_btn)
        content.add_widget(sort_bar)

        # Список файлов
        self.file_list = MDScrollView()
        self.file_container = MDBoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(1))
        self.file_container.bind(minimum_height=self.file_container.setter('height'))
        self.file_list.add_widget(self.file_container)
        content.add_widget(self.file_list)

        # Индикатор загрузки
        self._loading_indicator = Label(
            text=tr('loading_in_progress', "Loading..."),
            font_size=dp(12),
            color=(0.6, 0.6, 0.6, 1),
            size_hint_y=None,
            height=dp(40)
        )

        # Кнопка "Наверх"
        up_btn = MDRectangleFlatButton(
            text=tr('up_level', 'Up'),
            size_hint_y=None,
            height=dp(30),
            line_color=PURPLE,
            text_color=PURPLE
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
            self.filename_input.line_color_normal = PURPLE
            self.filename_input.text_color = PURPLE
            self.filename_input.hint_text_color = (0.6, 0.6, 0.6, 1)
            content.add_widget(self.filename_input)

        # Кнопки
        btn_layout = MDBoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))

        cancel_btn = MDRectangleFlatButton(
            text=tr('cancel', 'Cancel'),
            line_color=PURPLE,
            text_color=PURPLE
        )
        cancel_btn.bind(on_release=lambda x: self._dismiss())

        action_text = tr('save', 'Save') if self.mode == "save" else tr('open', 'Open')
        self.action_btn = MDRectangleFlatButton(
            text=action_text,
            text_color=(1, 1, 1, 1),
            md_bg_color=PURPLE
        )
        self.action_btn.bind(on_release=lambda x: self._on_action())

        btn_layout.add_widget(cancel_btn)
        btn_layout.add_widget(self.action_btn)
        content.add_widget(btn_layout)

        self.popup = Popup(
            title=self._title,
            title_color=PURPLE,
            title_size=dp(14),
            separator_color=PURPLE,
            background='',
            background_color=bg_color,
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

    def _apply_sort(self, sort_type):
        """Применяет сортировку и обновляет список"""
        tr = self._tr

        # Обновляем стиль кнопок
        self.sort_name_btn.line_color = SORT_ACTIVE if sort_type == 'name' else PURPLE
        self.sort_name_btn.text_color = SORT_ACTIVE if sort_type == 'name' else PURPLE
        self.sort_date_btn.line_color = SORT_ACTIVE if sort_type == 'date' else PURPLE
        self.sort_date_btn.text_color = SORT_ACTIVE if sort_type == 'date' else PURPLE
        self.sort_size_btn.line_color = SORT_ACTIVE if sort_type == 'size' else PURPLE
        self.sort_size_btn.text_color = SORT_ACTIVE if sort_type == 'size' else PURPLE

        self.fm.set_sort(sort_type, self._sort_reverse)
        self._refresh_list()

    def _toggle_reverse(self):
        """Инвертирует направление сортировки"""
        self._sort_reverse = not self._sort_reverse
        self.sort_reverse_btn.icon = 'arrow-down' if self._sort_reverse else 'arrow-up'
        self.fm.toggle_sort_direction()
        self._refresh_list()

    def _go_up(self):
        if self.fm.go_up():
            self._refresh_list()
            self._selected_item = None

    def _refresh_list(self):
        if self.file_container:
            self.file_container.clear_widgets()
            self.file_container.add_widget(self._loading_indicator)
        if self.path_label:
            self.path_label.text = self.fm.current_path
        self.fm.list_files(self._update_list)

    def _update_list(self, items, current_path, error):
        if not self.file_container:
            return

        self.file_container.clear_widgets()
        self.path_label.text = current_path

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
                text=self._tr('empty_folder', 'Empty folder'),
                size_hint_y=None,
                height=dp(50),
                color=PURPLE
            ))
            return

        def add_widgets(start_idx, batch_size=25):
            end_idx = min(start_idx + batch_size, len(items))
            for i in range(start_idx, end_idx):
                item = items[i]
                row = self._create_row(item)
                self.file_container.add_widget(row)
            if end_idx < len(items):
                Clock.schedule_once(lambda dt: add_widgets(end_idx, batch_size), 0.01)

        add_widgets(0, 25)

    def _create_row(self, item):
        tr = self._tr

        row = ClickableRow(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(48),
            spacing=dp(8),
            padding=[dp(8), dp(4), dp(8), dp(4)]
        )

        # Подсветка выбранного
        if self._selected_item == item.path:
            with row.canvas.before:
                Color(*PURPLE_LIGHT)
                row._selected_rect = Rectangle(pos=row.pos, size=row.size)
            row.bind(pos=self._update_selected_rect, size=self._update_selected_rect)

        # Иконка
        icon = MDIcon(
            icon=item.icon_name,
            font_size=dp(22),
            theme_text_color="Custom",
            text_color=PURPLE,
            size_hint_x=None,
            width=dp(40)
        )
        row.add_widget(icon)

        # Информация
        info_layout = MDBoxLayout(orientation='vertical', size_hint_x=1, spacing=dp(2))

        name_label = Label(
            text=item.name,
            font_size=dp(12),
            color=PURPLE,
            halign='left',
            size_hint_y=0.6
        )
        info_layout.add_widget(name_label)

        # Дополнительная информация
        if item.is_dir:
            sub_text = f"{tr('modified', 'Modified')}: {item.format_date(tr)}"
        else:
            sub_text = f"{tr('file_size', 'Size')}: {item.format_size()}  |  {tr('modified', 'Modified')}: {item.format_date(tr)}"

        sub_label = Label(
            text=sub_text,
            font_size=dp(9),
            color=(0.6, 0.6, 0.6, 1),
            halign='left',
            size_hint_y=0.4
        )
        info_layout.add_widget(sub_label)

        row.add_widget(info_layout)

        # Кнопка меню
        menu_btn = MDIconButton(
            icon='dots-vertical',
            icon_size=dp(20),
            size_hint_x=None,
            width=dp(40),
            theme_icon_color="Custom",
            icon_color=PURPLE
        )
        menu_btn.bind(on_release=lambda btn, it=item: self._show_menu(btn, it))
        row.add_widget(menu_btn)

        if item.is_dir:
            row.bind(on_release=lambda x, p=item.path: self._open_folder(p))
        else:
            row.bind(on_release=lambda x, p=item.path: self._select_file(p))

        return row

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

        # Обновляем подсветку
        if self.file_container:
            for child in self.file_container.children:
                if isinstance(child, ClickableRow):
                    if hasattr(child, '_selected_rect'):
                        child.canvas.before.remove(child._selected_rect)
                        child._selected_rect = None

                    if hasattr(child, 'children'):
                        for widget in child.children:
                            if isinstance(widget, MDBoxLayout):
                                for sub_widget in widget.children:
                                    if isinstance(sub_widget, Label) and sub_widget.text == os.path.basename(path):
                                        with child.canvas.before:
                                            Color(*PURPLE_LIGHT)
                                            child._selected_rect = Rectangle(pos=child.pos, size=child.size)
                                        child.bind(pos=self._update_selected_rect, size=self._update_selected_rect)
                                        break

    def _show_menu(self, button, item):
        tr = self._tr

        content = MDBoxLayout(orientation='vertical', padding=dp(8), spacing=dp(5), size_hint_y=None)
        content.height = dp(130)

        if not item.is_dir:
            btn_open = MDRectangleFlatButton(
                text=tr('open', 'Open'),
                size_hint_y=None,
                height=dp(40),
                line_color=PURPLE,
                text_color=PURPLE
            )
            btn_open.bind(on_release=lambda x: self._open_item(item))
            content.add_widget(btn_open)

        btn_rename = MDRectangleFlatButton(
            text=tr('rename', 'Rename'),
            size_hint_y=None,
            height=dp(40),
            line_color=PURPLE,
            text_color=PURPLE
        )
        btn_rename.bind(on_release=lambda x: self._rename_item(item))
        content.add_widget(btn_rename)

        btn_delete = MDRectangleFlatButton(
            text=tr('delete', 'Delete'),
            size_hint_y=None,
            height=dp(40),
            md_bg_color=(0.5, 0.2, 0.2, 1),
            text_color=(1, 1, 1, 1)
        )
        btn_delete.bind(on_release=lambda x: self._delete_item(item))
        content.add_widget(btn_delete)

        menu_popup = Popup(
            title=tr('actions', 'Actions'),
            title_color=PURPLE,
            separator_color=PURPLE,
            background='',
            background_color=self._get_bg_color(),
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
        bg_color = self._get_bg_color()
        tr = self._tr

        content = MDBoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        content.add_widget(Label(
            text=f"{tr('rename', 'Rename')}: {item.name}",
            color=PURPLE,
            font_size=dp(12)
        ))

        name_input = MDTextField(
            text=item.name,
            size_hint_y=None,
            height=dp(45),
            mode="rectangle"
        )
        name_input.line_color_normal = PURPLE
        name_input.text_color = PURPLE
        content.add_widget(name_input)

        btn_layout = MDBoxLayout(size_hint_y=None, height=dp(40), spacing=dp(10))

        popup = Popup(
            title=tr('rename', 'Rename'),
            title_color=PURPLE,
            separator_color=PURPLE,
            background='',
            background_color=bg_color,
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
            md_bg_color=PURPLE
        )
        btn_ok.bind(on_release=do_rename)
        btn_cancel = MDRectangleFlatButton(
            text=tr('cancel', 'Cancel'),
            line_color=PURPLE,
            text_color=PURPLE
        )
        btn_cancel.bind(on_release=lambda x: popup.dismiss())

        btn_layout.add_widget(btn_cancel)
        btn_layout.add_widget(btn_ok)
        content.add_widget(btn_layout)

        popup.open()
        Clock.schedule_once(lambda dt: setattr(name_input, 'focus', True), 0.3)

    def _delete_item(self, item):
        bg_color = self._get_bg_color()
        tr = self._tr

        content = MDBoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        content.add_widget(Label(
            text=f"{tr('delete_confirm', 'Delete')} {item.name}?",
            color=PURPLE,
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
            title_color=PURPLE,
            separator_color=PURPLE,
            background='',
            background_color=bg_color,
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
            md_bg_color=(0.5, 0.2, 0.2, 1)
        )
        btn_delete.bind(on_release=do_delete)
        btn_cancel = MDRectangleFlatButton(
            text=tr('cancel', 'Cancel'),
            line_color=PURPLE,
            text_color=PURPLE
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
        bg_color = self._get_bg_color()
        tr = self._tr

        content_box = MDBoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        content_box.add_widget(Label(
            text=f"{tr('file_exists', 'File')} '{filename}' {tr('already_exists', 'exists')}.\n{tr('overwrite_prompt', 'Overwrite?')}",
            color=PURPLE,
            halign='center'
        ))

        btn_layout = MDBoxLayout(size_hint_y=None, height=dp(40), spacing=dp(10))

        popup = Popup(
            title=tr('confirm', 'Confirm'),
            title_color=PURPLE,
            separator_color=PURPLE,
            background='',
            background_color=bg_color,
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
            md_bg_color=PURPLE
        )
        btn_yes.bind(on_release=on_yes)
        btn_no = MDRectangleFlatButton(
            text=tr('no', 'No'),
            line_color=PURPLE,
            text_color=PURPLE
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

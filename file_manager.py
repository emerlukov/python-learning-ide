# file_manager.py - ИСПРАВЛЕННАЯ ВЕРСИЯ

import os
from kivy.app import App
import threading
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.utils import platform
from kivy.core.window import Window
from kivy.uix.behaviors import ButtonBehavior
from kivy.graphics import Color, Rectangle
import time

from kivymd.uix.label import MDIcon
from kivymd.uix.button import MDRectangleFlatButton, MDIconButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.scrollview import MDScrollView
from ide_core.settings import SettingsManager

# ====================== ИМПОРТ ТЕМ ======================
try:
    from ide_core.themes import ThemeManager
except ImportError:
    ThemeManager = None

# ====================== ГЛОБАЛЬНЫЕ КОНСТАНТЫ ======================
TEXT_EXTENSIONS = {
    '.py', '.txt', '.md', '.json', '.xml', '.html', '.htm', '.css', '.js',
    '.csv', '.log', '.ini', '.yaml', '.yml', '.toml', '.env', '.gitignore',
    '.rst', '.tex', '.c', '.cpp', '.h', '.java', '.kt', '.kts', '.swift',
    '.go', '.rs', '.rb', '.php', '.sql', '.sh', '.bat', '.ps1', '.cfg',
    '.conf', '.properties', '.gradle', '.svg', '.vue', '.jsx', '.tsx',
    '.ts', '.scss', '.sass', '.less', '.coffee'
}

PURPLE = (0.596, 0.486, 1.0, 1)
PURPLE_LIGHT = (0.7, 0.6, 1.0, 0.3)
SORT_ACTIVE = (0.8, 0.7, 1.0, 1)

# Задержка для определения клика (секунды)
CLICK_DELAY = 0.3
# Минимальное движение для определения свайпа (пиксели)
MIN_SWIPE_DISTANCE = dp(10)


class ClickableRow(ButtonBehavior, MDBoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.touch_start_time = 0
        self.touch_start_pos = (0, 0)
        self.touch_moved = False


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
        if self.mtime == 0:
            return ""
        from datetime import datetime
        dt = datetime.fromtimestamp(self.mtime)
        return dt.strftime("%d.%m.%Y %H:%M")


class SortManager:
    SORT_NAME = 'name'
    SORT_DATE = 'date'
    SORT_SIZE = 'size'

    def __init__(self):
        self.current_sort = self.SORT_NAME
        self.reverse = False

    def sort_items(self, folders, files):
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
        self._max_cache_size = 50  # Максимальное количество кэшированных путей
        self.sort_manager = SortManager()

        self._read_lock = False
        self._write_lock = False
        self._delete_lock = False
        self._rename_lock = False

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

                # Очищаем старые записи кэша при превышении лимита
                if len(self._cache) > self._max_cache_size:
                    # Сортируем по времени и удаляем самые старые
                    sorted_paths = sorted(self._cache_time.keys(), key=lambda x: self._cache_time[x])
                    for old_path in sorted_paths[:len(self._cache) - self._max_cache_size]:
                        self._cache.pop(old_path, None)
                        self._cache_time.pop(old_path, None)

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
        """Читает файл с блокировкой от повторных вызовов"""
        if self._read_lock:
            app = App.get_running_app()
            msg = app.tr.get('operation_in_progress',
                             'Operation already in progress') if app else 'Operation already in progress'
            Clock.schedule_once(lambda dt: callback(None, msg), 0)
            return

        self._read_lock = True

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
            finally:
                self._read_lock = False  # ВАЖНО: снимаем блокировку

        threading.Thread(target=read, daemon=True).start()

    def save_file(self, file_path, content, callback):
        """Сохраняет файл с блокировкой от повторных вызовов"""
        if self._write_lock:
            Clock.schedule_once(lambda dt: callback(False, "Операция уже выполняется"), 0)
            return

        self._write_lock = True

        def save():
            try:
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                self._cache.pop(os.path.dirname(file_path), None)
                Clock.schedule_once(lambda dt: callback(True, None))
            except Exception as e:
                Clock.schedule_once(lambda dt: callback(False, str(e)))
            finally:
                self._write_lock = False

        threading.Thread(target=save, daemon=True).start()

    def delete_file(self, file_path, callback):
        """Удаляет файл с блокировкой от повторных вызовов"""
        if self._delete_lock:
            Clock.schedule_once(lambda dt: callback(False, "Операция уже выполняется"), 0)
            return

        self._delete_lock = True

        def delete():
            try:
                os.remove(file_path)
                self._cache.pop(os.path.dirname(file_path), None)
                Clock.schedule_once(lambda dt: callback(True, None))
            except Exception as e:
                Clock.schedule_once(lambda dt: callback(False, str(e)))
            finally:
                self._delete_lock = False

        threading.Thread(target=delete, daemon=True).start()

    def rename_file(self, old_path, new_name, callback):
        """Переименовывает файл с блокировкой от повторных вызовов"""
        if self._rename_lock:
            Clock.schedule_once(lambda dt: callback(False, None, "Операция уже выполняется"), 0)
            return

        self._rename_lock = True

        def rename():
            try:
                new_path = os.path.join(os.path.dirname(old_path), new_name)
                os.rename(old_path, new_path)
                self._cache.pop(os.path.dirname(old_path), None)
                Clock.schedule_once(lambda dt: callback(True, new_path, None))
            except Exception as e:
                Clock.schedule_once(lambda dt: callback(False, None, str(e)))
            finally:
                self._rename_lock = False

        threading.Thread(target=rename, daemon=True).start()

    def refresh_file_list(self):
        """Обновляет список файлов в текущей папке"""
        self._cache.pop(self.current_path, None)
        if hasattr(self.app, '_current_file_popup') and self.app._current_file_popup:
            self.app._current_file_popup._refresh_list()

    def set_saf_root(self, uri):
        """Устанавливает URI для SAF (Storage Access Framework)"""
        self._saf_root = uri
        # Можно сохранить в настройках
        SettingsManager.save_working_folder(uri)


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
        self._last_touch_time = 0
        self._last_touch_path = None
        self._current_menu_popup = None  # Добавляем ссылку на текущее меню

    def _tr(self, key, fallback=""):
        return getattr(self.app, 'tr', {}).get(key, fallback)

    def _get_bg_color(self):
        try:
            if ThemeManager:
                theme = ThemeManager.get_theme()
                if theme and theme.get('name') == 'light':
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

        if self.mode == "save":
            self.filename_input = MDTextField(
                text=self.save_filename,
                hint_text="    " + tr('file_name', 'File name'),
                size_hint_y=None,
                height=dp(45),
                mode="rectangle"
            )
            self.filename_input.line_color_normal = PURPLE
            self.filename_input.text_color = PURPLE
            self.filename_input.hint_text_color = (0.6, 0.6, 0.6, 1)
            content.add_widget(self.filename_input)

        # Панель сортировки
        sort_bar = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=dp(35), spacing=dp(5),
                               padding=[dp(5), dp(2)])

        self.sort_name_btn = MDRectangleFlatButton(
            text=tr('sort_by_name', 'By name'),
            size_hint_x=0.33,
            font_size=dp(10),
            line_color=PURPLE,
            text_color=PURPLE
        )
        self.sort_name_btn.bind(on_release=lambda x: self._apply_sort('name'))

        self.sort_date_btn = MDRectangleFlatButton(
            text=tr('sort_by_date', 'By date'),
            size_hint_x=0.33,
            font_size=dp(10),
            line_color=PURPLE,
            text_color=PURPLE
        )
        self.sort_date_btn.bind(on_release=lambda x: self._apply_sort('date'))

        self.sort_size_btn = MDRectangleFlatButton(
            text=tr('sort_by_size', 'By size'),
            size_hint_x=0.33,
            font_size=dp(10),
            line_color=PURPLE,
            text_color=PURPLE
        )
        self.sort_size_btn.bind(on_release=lambda x: self._apply_sort('size'))

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

        self.file_list = MDScrollView()
        self.file_container = MDBoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(1))
        self.file_container.bind(minimum_height=self.file_container.setter('height'))
        self.file_list.add_widget(self.file_container)
        content.add_widget(self.file_list)

        self._loading_indicator = Label(
            text=tr('loading_in_progress', "Loading..."),
            font_size=dp(12),
            color=(0.6, 0.6, 0.6, 1),
            size_hint_y=None,
            height=dp(40)
        )

        up_btn = MDRectangleFlatButton(
            text=tr('up_level', 'Up'),
            size_hint_y=None,
            height=dp(30),
            line_color=PURPLE,
            text_color=PURPLE
        )
        up_btn.bind(on_release=lambda x: self._go_up())
        content.add_widget(up_btn)

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

        # Обёртываем все кнопки в попапе для вибрации
        if hasattr(self.app, 'wrap_widget_buttons'):
            self.app.wrap_widget_buttons(content)


        self._refresh_list()

    def _on_keyboard_height(self, window, keyboard_height):
        """Сдвигаем попап вверх когда поднимается клавиатура"""
        if not self.popup:
            return
        if keyboard_height > 0:
            # Клавиатура открылась — сдвигаем попап вверх на высоту клавиатуры
            # но не выше верхней границы экрана
            shift = keyboard_height
            new_y = shift / 2  # центрируем в оставшемся пространстве
            max_y = Window.height - self.popup.height
            self.popup.y = min(new_y, max_y)
        else:
            # Клавиатура закрылась — возвращаем попап по центру
            self.popup.pos_hint = {'center_x': 0.5, 'center_y': 0.5}
            self.popup.center = Window.center

    def _update_bg(self, instance, value):
        if hasattr(self, '_bg_rect'):
            self._bg_rect.pos = instance.pos
            self._bg_rect.size = instance.size

    def _apply_sort(self, sort_type):
        self.sort_name_btn.line_color = SORT_ACTIVE if sort_type == 'name' else PURPLE
        self.sort_name_btn.text_color = SORT_ACTIVE if sort_type == 'name' else PURPLE
        self.sort_date_btn.line_color = SORT_ACTIVE if sort_type == 'date' else PURPLE
        self.sort_date_btn.text_color = SORT_ACTIVE if sort_type == 'date' else PURPLE
        self.sort_size_btn.line_color = SORT_ACTIVE if sort_type == 'size' else PURPLE
        self.sort_size_btn.text_color = SORT_ACTIVE if sort_type == 'size' else PURPLE

        self.fm.set_sort(sort_type, self._sort_reverse)
        self._refresh_list()

    def _toggle_reverse(self):
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

        # Сохраняем данные в атрибутах строки
        row.item_path = item.path
        row.is_dir = item.is_dir
        row.item = item

        # Подсветка выбранного
        if self._selected_item == item.path:
            with row.canvas.before:
                Color(*PURPLE_LIGHT)
                row._selected_rect = Rectangle(pos=row.pos, size=row.size)
            row.bind(pos=self._update_selected_rect, size=self._update_selected_rect)

        icon = MDIcon(
            icon=item.icon_name,
            font_size=dp(22),
            theme_text_color="Custom",
            text_color=PURPLE,
            size_hint_x=None,
            width=dp(40)
        )
        row.add_widget(icon)

        info_layout = MDBoxLayout(orientation='vertical', size_hint_x=1, spacing=dp(2))

        name_label = Label(
            text=item.name,
            font_size=dp(12),
            color=PURPLE,
            halign='left',
            size_hint_y=0.6
        )
        info_layout.add_widget(name_label)

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

        menu_btn = MDIconButton(
            icon='dots-vertical',
            icon_size=dp(20),
            size_hint_x=None,
            width=dp(40),
            theme_icon_color="Custom",
            icon_color=PURPLE
        )
        # ИЗМЕНЕНО: прямое касание для кнопки меню
        menu_btn.bind(on_release=lambda btn, it=item: self._show_menu_for_item(it, btn))
        row.add_widget(menu_btn)

        # Привязываем обработчики касаний для строки (удержание)
        row.bind(on_touch_down=self._on_row_touch_down)
        row.bind(on_touch_up=self._on_row_touch_up)

        return row

    def _on_row_touch_down(self, instance, touch):
        """Запоминаем начало касания, но только если касание не на кнопке меню"""
        # Проверяем, не нажата ли кнопка меню внутри строки
        for child in instance.children:
            if isinstance(child, MDIconButton) and child.collide_point(*touch.pos):
                return False  # Игнорируем, это обработает кнопка меню

        if not instance.collide_point(*touch.pos):
            return False
        instance.touch_start_time = time.time()
        instance.touch_start_pos = touch.pos
        instance.touch_moved = False
        return True

    def _on_row_touch_up(self, instance, touch):
        """Обрабатываем отпускание касания только если это удержание (не на кнопке меню)"""
        # Проверяем, не нажата ли кнопка меню внутри строки
        for child in instance.children:
            if isinstance(child, MDIconButton) and child.collide_point(*touch.pos):
                return False  # Игнорируем, это обработает кнопка меню

        # Проверяем, было ли движение
        if hasattr(instance, 'touch_moved') and instance.touch_moved:
            return False

        # Проверяем, не двигался ли палец
        if hasattr(instance, 'touch_start_pos'):
            dx = abs(touch.pos[0] - instance.touch_start_pos[0])
            dy = abs(touch.pos[1] - instance.touch_start_pos[1])
            if dx > MIN_SWIPE_DISTANCE or dy > MIN_SWIPE_DISTANCE:
                return False

        # Проверяем время касания
        duration = time.time() - instance.touch_start_time

        # Получаем данные из атрибутов строки
        path = getattr(instance, 'item_path', None)
        is_dir = getattr(instance, 'is_dir', False)

        if not path:
            return False

        # ТОЛЬКО длинное касание (удержание) для контекстного меню
        if duration >= CLICK_DELAY:
            item = getattr(instance, 'item', None)
            if item:
                self._show_menu_for_item(item, instance)
        else:
            # Короткое касание - открываем папку или выделяем файл
            if is_dir:
                self._open_folder(path)
            else:
                self._select_file(path)

        return True

    def _update_selected_rect(self, instance, value):
        """Обновляет позицию и размер подсветки выбранного элемента"""
        if hasattr(instance, '_selected_rect') and instance._selected_rect:
            instance._selected_rect.pos = instance.pos
            instance._selected_rect.size = instance.size

    def _open_folder(self, path):
        self.fm.navigate_to(path)
        self._refresh_list()
        self._selected_item = None

    def _select_file(self, path):
        """Выбирает файл с правильной очисткой предыдущей подсветки"""
        # Сохраняем старый выбранный путь
        old_selected = self._selected_item
        self._selected_item = path

        # Очищаем подсветку со всех строк
        if self.file_container:
            for child in self.file_container.children[:]:  # копия списка для безопасной итерации
                if isinstance(child, ClickableRow):
                    # Удаляем старый прямоугольник если есть
                    if hasattr(child, '_selected_rect'):
                        if child._selected_rect:
                            child.canvas.before.remove(child._selected_rect)
                            child._selected_rect = None

                    # Удаляем старые привязки, если они есть
                    if hasattr(child, '_bound_pos') and child._bound_pos:
                        child.unbind(pos=child._bound_pos, size=child._bound_size)
                        child._bound_pos = None
                        child._bound_size = None

        # Добавляем подсветку только для нового выбранного файла
        if self.file_container:
            for child in self.file_container.children:
                if isinstance(child, ClickableRow):
                    # Проверяем, соответствует ли эта строка выбранному файлу
                    child_path = getattr(child, 'item_path', None)
                    if child_path == path:
                        # Создаем новый прямоугольник
                        with child.canvas.before:
                            Color(*PURPLE_LIGHT)
                            child._selected_rect = Rectangle(pos=child.pos, size=child.size)

                        # Сохраняем привязки для обновления
                        child._bound_pos = child.bind(pos=self._update_selected_rect)
                        child._bound_size = child.bind(size=self._update_selected_rect)
                        break

    def _show_menu_for_item(self, item, button):
        """Показывает контекстное меню для элемента - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
        # Закрываем предыдущее меню, если оно открыто
        if self._current_menu_popup:
            self._current_menu_popup.dismiss()
            self._current_menu_popup = None

        tr = self._tr
        bg_color = self._get_bg_color()

        # Создаём содержимое меню
        content = MDBoxLayout(orientation='vertical', padding=dp(8), spacing=dp(5), size_hint_y=None)

        # Устанавливаем высоту в зависимости от типа элемента
        if not item.is_dir:
            content.height = dp(200)
        else:
            content.height = dp(160)

        if not item.is_dir:
            btn_open = MDRectangleFlatButton(
                text=tr('open', 'Open'),
                size_hint_y=None,
                height=dp(40),
                line_color=PURPLE,
                text_color=PURPLE
            )
            btn_open.bind(on_release=lambda x: self._open_item_with_menu_close(item))
            content.add_widget(btn_open)

        btn_rename = MDRectangleFlatButton(
            text=tr('rename', 'Rename'),
            size_hint_y=None,
            height=dp(40),
            line_color=PURPLE,
            text_color=PURPLE
        )
        btn_rename.bind(on_release=lambda x: self._rename_item_with_menu_close(item))
        content.add_widget(btn_rename)

        btn_delete = MDRectangleFlatButton(
            text=tr('delete', 'Delete'),
            size_hint_y=None,
            height=dp(40),
            md_bg_color=(0.5, 0.2, 0.2, 1),
            text_color=(1, 1, 1, 1)
        )
        btn_delete.bind(on_release=lambda x: self._delete_item_with_menu_close(item))
        content.add_widget(btn_delete)

        # Создаём попап меню
        try:
            menu_popup = Popup(
                title=tr('actions', 'Actions'),
                title_color=PURPLE,
                separator_color=PURPLE,
                background='',
                background_color=bg_color,
                content=content,
                size_hint=(0.55, None),
                height=content.height,
                auto_dismiss=True
            )

            # Обёртываем кнопки в контекстном меню
            if hasattr(self.app, 'wrap_widget_buttons'):
                self.app.wrap_widget_buttons(content)

            # При закрытии очищаем ссылку
            menu_popup.bind(on_dismiss=self._on_menu_closed)

            self._current_menu_popup = menu_popup
            menu_popup.open()
        except Exception as e:
            print(f"[ERROR] Menu popup error: {e}")

    def _on_menu_closed(self, instance):
        """Очищает ссылку на меню при его закрытии"""
        self._current_menu_popup = None

    def _open_item_with_menu_close(self, item):
        """Открывает элемент и закрывает меню"""
        if self._current_menu_popup:
            self._current_menu_popup.dismiss()
            self._current_menu_popup = None
        self._open_item(item)

    def _rename_item_with_menu_close(self, item):
        """Переименовывает элемент и закрывает меню"""
        if self._current_menu_popup:
            self._current_menu_popup.dismiss()
            self._current_menu_popup = None
        self._rename_item(item)

    def _delete_item_with_menu_close(self, item):
        """Удаляет элемент и закрывает меню"""
        if self._current_menu_popup:
            self._current_menu_popup.dismiss()
            self._current_menu_popup = None
        self._delete_item(item)

    def _open_item(self, item):
        """Открывает папку или файл"""
        if item.is_dir:
            self.fm.navigate_to(item.path)
            self._refresh_list()
            self._selected_item = None
        else:
            self._load_and_close(item.path)

    def _rename_item(self, item):
        """Показывает диалог переименования"""
        bg_color = self._get_bg_color()
        tr = self._tr

        content = MDBoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        content.add_widget(Label(
            text=f"{tr('rename', 'Rename')}: {item.name}",
            color=PURPLE,
            font_size=dp(12),
            size_hint_y=None,
            height=dp(30)
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

        rename_popup = Popup(
            title=tr('rename', 'Rename'),
            title_color=PURPLE,
            separator_color=PURPLE,
            background='',
            background_color=bg_color,
            content=content,
            size_hint=(0.8, 0.38),
            auto_dismiss=False
        )

        def do_rename(btn):
            new_name = name_input.text.strip()
            if new_name and new_name != item.name:
                def callback(success, new_path, error):
                    rename_popup.dismiss()
                    if success:
                        self._refresh_list()
                        self.app.show_result_popup(f"{tr('renamed', 'Renamed')}: {new_name}")
                    else:
                        self.app.show_result_popup(f"{tr('error', 'Error')}: {error}")

                self.fm.rename_file(item.path, new_name, callback)
            else:
                rename_popup.dismiss()

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
        btn_cancel.bind(on_release=lambda x: rename_popup.dismiss())

        btn_layout.add_widget(btn_cancel)
        btn_layout.add_widget(btn_ok)
        content.add_widget(btn_layout)

        if hasattr(self.app, 'wrap_widget_buttons'):
            self.app.wrap_widget_buttons(content)

        rename_popup.open()
        Clock.schedule_once(lambda dt: setattr(name_input, 'focus', True), 0.3)

    def _delete_item(self, item):
        """Показывает диалог подтверждения удаления"""
        bg_color = self._get_bg_color()
        tr = self._tr

        content = MDBoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        content.add_widget(Label(
            text=f"{tr('delete_confirm', 'Delete')} {item.name}?",
            color=PURPLE,
            font_size=dp(14),
            size_hint_y=None,
            height=dp(30)
        ))
        if not item.is_dir:
            content.add_widget(Label(
                text=tr('cannot_undo', 'This cannot be undone'),
                color=(0.7, 0.2, 0.2, 1),
                font_size=dp(10),
                size_hint_y=None,
                height=dp(20)
            ))

        btn_layout = MDBoxLayout(size_hint_y=None, height=dp(40), spacing=dp(10))

        delete_popup = Popup(
            title=tr('confirm', 'Confirm'),
            title_color=PURPLE,
            separator_color=PURPLE,
            background='',
            background_color=bg_color,
            content=content,
            size_hint=(0.7, 0.35),
            auto_dismiss=False
        )

        def do_delete(btn):
            delete_popup.dismiss()

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
        btn_cancel.bind(on_release=lambda x: delete_popup.dismiss())

        btn_layout.add_widget(btn_cancel)
        btn_layout.add_widget(btn_delete)
        content.add_widget(btn_layout)

        if hasattr(self.app, 'wrap_widget_buttons'):
            self.app.wrap_widget_buttons(content)

        delete_popup.open()

    def _load_and_close(self, file_path):
        """Загружает файл и закрывает браузер"""

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
            halign='center',
            size_hint_y=None,
            height=dp(50)
        ))

        btn_layout = MDBoxLayout(size_hint_y=None, height=dp(40), spacing=dp(10))

        popup = Popup(
            title=tr('confirm', 'Confirm'),
            title_color=PURPLE,
            separator_color=PURPLE,
            background='',
            background_color=bg_color,
            content=content_box,
            size_hint=(0.7, 0.28),
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

        if hasattr(self.app, 'wrap_widget_buttons'):
            self.app.wrap_widget_buttons(content_box)

        popup.open()

    def _dismiss(self):
        """Закрывает попап с очисткой всех ресурсов"""
        # Отписываемся от события клавиатуры
        Window.unbind(keyboard_height=self._on_keyboard_height)
        # Очищаем подсветку
        if hasattr(self, 'file_container') and self.file_container:
            for child in self.file_container.children[:]:
                if isinstance(child, ClickableRow):
                    if hasattr(child, '_selected_rect') and child._selected_rect:
                        child.canvas.before.remove(child._selected_rect)
                        child._selected_rect = None
                    if hasattr(child, '_bound_pos') and child._bound_pos:
                        child.unbind(pos=child._bound_pos, size=child._bound_size)
                        child._bound_pos = None
                        child._bound_size = None

        # Закрываем меню если открыто
        if hasattr(self, '_current_menu_popup') and self._current_menu_popup:
            self._current_menu_popup.dismiss()
            self._current_menu_popup = None

        # Закрываем попап
        if self.popup:
            self.popup.dismiss()
            self.popup = None
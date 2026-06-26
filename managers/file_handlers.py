# managers/file_handlers.py
"""
File operation handlers for the application
"""
import os
import threading
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.utils import platform

from ide_core.themes import ThemeManager
from utils.debug_utils import log_error


class FileOperationHandlers:
    """Обработчики файловых операций"""

    def __init__(self, app):
        self.app = app

    def on_file_loaded(self, file_path, content):
        """Обработчик загруженного файла"""
        if not content:
            return

        filename = os.path.basename(file_path)

        if hasattr(self.app, 'tab_manager') and self.app.tab_manager:
            editor = self.app.tab_manager.add_tab(title=filename, text=content)
            if 0 <= self.app.tab_manager.active_index < len(self.app.tab_manager.tabs):
                self.app.tab_manager.tabs[self.app.tab_manager.active_index]['file'] = file_path
                self.app.tab_manager.tabs[self.app.tab_manager.active_index]['original_content'] = content
                self.app.tab_manager.mark_tab_saved(self.app.tab_manager.active_index)
            self.app._on_tab_changed(editor)
        else:
            self.app.code_input.text = content
            if hasattr(self.app, 'editor'):
                self.app.editor.original_lines = content.split('\n')
                self.app.editor._update_line_panel()

        self.app._current_file = file_path
        self.app._update_title_from_current_tab()
        self.app.show_result_popup(f"Loaded: {filename}")

    def on_file_saved(self, file_path, content):
        """Обработчик сохранённого файла"""
        filename = os.path.basename(file_path)

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(self.app.code_input.text)

            self.app._current_file = file_path

            if hasattr(self.app, 'tab_manager') and self.app.tab_manager:
                if 0 <= self.app.tab_manager.active_index < len(self.app.tab_manager.tabs):
                    self.app.tab_manager.tabs[self.app.tab_manager.active_index]['file'] = file_path
                    self.app.tab_manager.tabs[self.app.tab_manager.active_index][
                        'original_content'] = self.app.code_input.text
                    self.app.tab_manager.mark_tab_saved(self.app.tab_manager.active_index)
                    self.app.tab_manager.set_active_title(filename)

            self.app._update_title_from_current_tab()
            self.app.show_result_popup(f"Saved: {filename}")
        except Exception as e:
            self.app.show_result_popup(f"X Error saving: {e}")

    def on_activity_result(self, request_code, result_code, intent):
        """Обработка результатов системных диалогов Android (SAF)"""
        if result_code != -1 or intent is None:
            return

        try:
            uri = intent.getData()
            if not uri:
                return

            # Выбор папки для рабочей директории (SAF)
            if request_code == 1004:
                if uri:
                    if hasattr(self.app, 'file_manager'):
                        self.app.file_manager.set_saf_root(str(uri))
                    self.app.show_result_popup("Папка выбрана! Теперь можно открывать файлы.")
                return

            # Открытие файла через SAF
            if request_code == 1001:
                self._read_file_from_uri(uri)
                return

            # Сохранение файла через SAF
            if request_code == 1002:
                self._save_file_to_uri(uri)
                return

            # Запрос разрешения MANAGE_EXTERNAL_STORAGE (Android 11+)
            if request_code == 1005:
                try:
                    from jnius import autoclass
                    Environment = autoclass('android.os.Environment')
                    tr = self.app.tr
                    if Environment.isExternalStorageManager():
                        self.app.show_result_popup(tr.get('storage_permission_success',
                                                          "✓ Full file access granted!\nPlease restart the app."))
                    else:
                        self.app.show_result_popup(tr.get('storage_permission_failed',
                                                          "✗ Full file access not granted.\nSome files may not be visible."))
                    # Обновляем состояние file_manager
                    if hasattr(self.app, 'file_manager'):
                        self.app.file_manager.refresh_file_list()
                except Exception as e:
                    log_error(f"Storage permission check error: {e}")
                return

        except Exception as e:
            log_error(f"on_activity_result error: {e}")

    def _read_file_from_uri(self, uri):
        """Читает файл из URI (SAF)"""
        try:
            from jnius import autoclass, cast
            from android import activity

            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            ContentResolver = autoclass('android.content.ContentResolver')

            current_activity = cast('android.app.Activity', PythonActivity.mActivity)
            resolver = current_activity.getContentResolver()

            input_stream = resolver.openInputStream(uri)
            reader = autoclass('java.io.InputStreamReader')(input_stream, 'UTF-8')
            buffered = autoclass('java.io.BufferedReader')(reader)

            try:
                content = []
                line = buffered.readLine()
                while line is not None:
                    content.append(line)
                    line = buffered.readLine()
            finally:
                try:
                    buffered.close()
                except:
                    pass
                try:
                    reader.close()
                except:
                    pass
                try:
                    input_stream.close()
                except:
                    pass

            file_content = '\n'.join(content)

            Clock.schedule_once(lambda dt: self.on_file_loaded(uri.toString(), file_content))
        except Exception as e:
            log_error(f"Read from URI error: {e}")
            Clock.schedule_once(lambda dt: self.app.show_result_popup(f"Error reading file: {e}"))

    def _save_file_to_uri(self, uri):
        """Сохраняет файл в URI (SAF)"""
        try:
            from jnius import autoclass, cast
            from android import activity

            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            current_activity = cast('android.app.Activity', PythonActivity.mActivity)
            resolver = current_activity.getContentResolver()

            output_stream = resolver.openOutputStream(uri)
            try:
                content = self.app.code_input.text
                output_stream.write(content.encode('utf-8'))
            finally:
                try:
                    output_stream.close()
                except:
                    pass

            Clock.schedule_once(lambda dt: self.app.show_result_popup("File saved successfully!"))
        except Exception as e:
            log_error(f"Save to URI error: {e}")
            Clock.schedule_once(lambda dt: self.app.show_result_popup(f"Error saving file: {e}"))
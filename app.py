"""
Main application class for Python Learning IDE
"""
import os
import json
import threading
import time
from datetime import datetime

from kivy.app import App
from kivymd.app import MDApp
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.graphics import Color, Rectangle, Line
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.utils import platform
from kivy.core.clipboard import Clipboard

from utils import (
    log_error, get_screen_category, reset_screen_cache,
    adaptive_dp, adaptive_sp, get_tab_count,
    patched_excepthook, android_copy
)
from ide_core import SettingsManager, ThemeManager, SyntaxStyleManager, TRANSLATIONS, LessonManager
from widgets import MyActionBar, MySymbolScrollBar
from managers import AutoCompleteWidget, CodeExecutor, TabManager
from file_manager import FileManager
from managers import examples_manager

# Импортируем новые модули
from ui.top_bar import TopBarBuilder
from ui.menus import SettingsMenu
from managers.file_handlers import FileOperationHandlers
from managers.input_handler import InputHandler
from managers.emergency_recovery import EmergencyRecovery
from utils.hotkeys import HotkeyManager

from utils.vibration_manager import VibrationManager, wrap_all_buttons, auto_wrap_on_build
from utils.paths import user_data_path, ensure_user_data_dir, migrate_legacy_data


class PythonLearningApp(MDApp):
    """Главный класс приложения Python Learning IDE"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        migrate_legacy_data()

        # Инициализируем VibrationManager
        self.vibration_manager = VibrationManager()

        # Базовые настройки
        self.current_language = self._load_language()
        self.tr = TRANSLATIONS[self.current_language]
        self.current_theme_name = 'dark'
        self.splash_finished = False
        self._ui_ready = False
        self._code_running = False
        self._original_title = "Python Learning IDE"
        self.title = self._original_title

        # Данные
        self.history = []
        self._max_history = 20
        self.error_explainer_enabled = True

        # Менеджеры
        self.code_executor = CodeExecutor()
        self.tab_manager = TabManager()
        self.tab_manager.app = self
        self.file_manager = FileManager(self)

        # Менеджеры операций (новые)
        self.file_handlers = FileOperationHandlers(self)
        self.input_handler = InputHandler(self)
        self.emergency_recovery = EmergencyRecovery(self)
        self.hotkey_manager = HotkeyManager(self)

        # UI компоненты
        self.top_bar_builder = TopBarBuilder(self)
        self._settings_menu = None

        # Состояния
        self._current_file = None
        self._last_autosave_time = 0
        self._autosave_file = self._get_autosave_path()
        self._pending_operations = []
        self._current_file_popup = None
        self.search_widget = None
        self._popup = None

        # Применяем тему
        ThemeManager.apply_saved_theme()
        ThemeManager.register(self)

        # Загружаем примеры асинхронно
        self.examples_loaded = False
        examples_manager.load_examples_async(callback=self._on_examples_loaded)

    # ====================== ИНИЦИАЛИЗАЦИЯ ======================

    def build(self):
        """Создаёт интерфейс приложения"""
        main_widget = self._create_main_widget()

        from kivy.uix.screenmanager import ScreenManager, Screen
        from animated_splash import AnimatedSplashScreen

        sm = ScreenManager()
        splash = AnimatedSplashScreen(self, name='splash')
        sm.add_widget(splash)

        main_screen = Screen(name='main')
        main_screen.add_widget(main_widget)
        sm.add_widget(main_screen)

        sm.current = 'splash'

        Window.bind(on_resize=self.on_resize)

        # Привязываем обработчик для Android
        if platform == 'android':
            try:
                from android import activity
                activity.bind(on_activity_result=self.file_handlers.on_activity_result)
            except Exception as e:
                log_error(f"Failed to bind Android activity: {e}")

        # Прогрев Pygments
        self._warmup_pygments()

        # Проверка emergency бэкапа после загрузки
        Clock.schedule_once(lambda dt: self.emergency_recovery.check_and_restore(), 1.0)
        # Проверка разрешений через 1 секунду после запуска
        Clock.schedule_once(lambda dt: self.check_and_request_manage_storage(), 1)
        # Применяем язык после загрузки UI
        Clock.schedule_once(lambda dt: self._apply_language_to_ui(), 0.5)

        # ДОБАВЛЯЕМ: автоматическая обёртка кнопок (безопасно)
        try:
            from utils.vibration_manager import wrap_all_buttons, VibrationManager
            Clock.schedule_once(lambda dt: self._safe_wrap_buttons(), 0.8)
        except ImportError:
            pass

        return sm

    def _safe_wrap_buttons(self):
        """Безопасная обёртка всех кнопок"""
        try:
            from utils.vibration_manager import wrap_all_buttons
            if hasattr(self, 'root_layout'):
                wrap_all_buttons(self.root_layout)
                count = VibrationManager.get_wrapped_count()
                log_error(f"Successfully wrapped {count} buttons with vibration")
        except Exception as e:
            log_error(f"Vibration wrap failed: {e}")

    def wrap_widget_buttons(self, widget):
        """
        Обёртывает все кнопки в динамически созданном виджете.
        Вызывать после создания каждого диалога/попапа.
        """
        from utils.vibration_manager import wrap_all_buttons
        Clock.schedule_once(lambda dt: wrap_all_buttons(widget), 0.1)

    def _wrap_all_buttons(self):
        """Оборачивает все кнопки для автоматической вибрации"""
        if hasattr(self, 'root_layout'):
            wrap_all_buttons(self.root_layout)
            print(f"[Vibration] Wrapped {VibrationManager.get_wrapped_count()} buttons")

    def vibrate_short(self):
        """Единый метод вибрации - закомментирован, т.к. вибрация теперь через VibrationManager"""
        # Временно отключаем, чтобы не было двойной вибрации
        # try:
        #     from plyer import vibrator
        #     vibrator.vibrate(0.02)
        # except:
        #     pass
        pass  # Вибрация теперь через автоматическую обёртку

    def get_vibration_settings(self):
        """Возвращает настройки вибрации для UI"""
        return {
            'enabled': VibrationManager.is_enabled(),
            'duration': VibrationManager._duration
        }

    def set_vibration_enabled(self, enabled):
        """Включает/выключает вибрацию глобально"""
        VibrationManager.set_enabled(enabled)


    def set_vibration_duration(self, duration):
        """Устанавливает длительность вибрации"""
        VibrationManager.set_duration(duration)


    def _create_main_widget(self):
        """Создаёт главный виджет приложения"""
        self._request_android_permissions()  # ← ДОБАВЛЕНО
        self._request_storage_permission()
        self._load_fonts()

        Window.keyboard_anim_args = {'d': 0.2, 't': 'in_out_quad'}
        Window.bind(on_key_down=self.hotkey_manager.handle_keyboard)

        theme = ThemeManager.get_theme()
        main_layout = BoxLayout(orientation='vertical', padding=dp(3), spacing=dp(3))

        with main_layout.canvas.before:
            self.bg_color = Color(*theme['app_bg'])
            self.bg_rect = Rectangle(size=main_layout.size, pos=main_layout.pos)
        main_layout.bind(size=self._update_bg, pos=self._update_bg)

        # Верхняя панель (спиннер + меню)
        self.top_section = self.top_bar_builder.create_top_bar(theme)
        self.lesson_manager = LessonManager(self)
        main_layout.add_widget(self.top_section)

        # Панели действий
        self.action_bar = MyActionBar(None)
        self.action_bar.app = self
        main_layout.add_widget(self.action_bar)

        self.symbol_bar = MySymbolScrollBar(None)
        self.symbol_bar.app = self
        main_layout.add_widget(self.symbol_bar)

        # Вкладки
        tab_bar = self.tab_manager.create_tab_bar(theme)
        main_layout.add_widget(tab_bar)

        # Автодополнение
        self.autocomplete = AutoCompleteWidget()
        self.autocomplete.code_input = None
        main_layout.add_widget(self.autocomplete)

        # Редактор
        self._init_editor()

        self.editor_container = BoxLayout()
        self.editor_container.add_widget(self.editor)
        main_layout.add_widget(self.editor_container)

        # Плавающая кнопка Run
        root_layout = self._create_run_button(main_layout, theme)

        # Настройка автосохранения
        self._setup_autosave()
        self._ui_ready = True
        self._process_pending_operations()

        Clock.schedule_once(self._apply_saved_syntax_style, 0.5)

        self.root_layout = root_layout

        return root_layout

    def _init_editor(self):
        """Инициализирует редактор и загружает вкладки"""
        tabs_loaded = self.tab_manager.load_all_tabs()

        if not tabs_loaded:
            self.editor = self.tab_manager.add_tab(
                title=self.tr.get('untitled_tab', 'New'), text=""
            )
            self._set_initial_empty_lines()
        else:
            self.editor = self.tab_manager.get_active_editor()

        self.code_input = self.editor.text_input

        # Обновляем ссылки в панелях
        if hasattr(self, 'symbol_bar') and self.symbol_bar:
            self.symbol_bar.text_input = self.code_input
            print(f"[DEBUG] Updated symbol_bar.text_input")

        self.action_bar.text_input = self.code_input
        self.symbol_bar.text_input = self.code_input
        self.autocomplete.code_input = self.code_input
        self._current_file = self.tab_manager.get_active_file()

        # Применяем сохранённый шрифт
        self._apply_saved_font()

        # Устанавливаем курсор на первую строку
        def set_cursor(dt):
            if self.code_input:
                self.code_input.cursor = (0, 0)
                self.code_input.focus = True

        Clock.schedule_once(set_cursor, 0.5)
        Clock.schedule_once(set_cursor, 0.7)

    def _on_tab_changed(self, new_editor):
        """Переключение вкладки"""
        if not new_editor:
            return

        if not hasattr(self, 'editor_container') or not self.editor_container:
            return

        # Очищаем контейнер и добавляем новый редактор
        self.editor_container.clear_widgets()
        self.editor = new_editor

        if not hasattr(new_editor, 'text_input') or not new_editor.text_input:
            return

        self.code_input = new_editor.text_input
        self.editor_container.add_widget(new_editor)

        if hasattr(new_editor, 'rebind_touch_handlers'):
            new_editor.rebind_touch_handlers()

        # Обновляем ссылки в панелях
        if hasattr(self, 'action_bar') and self.action_bar:
            self.action_bar.text_input = self.code_input
        if hasattr(self, 'symbol_bar') and self.symbol_bar:
            self.symbol_bar.text_input = self.code_input
        if hasattr(self, 'autocomplete') and self.autocomplete:
            self.autocomplete.code_input = self.code_input

        # Применяем сохранённый шрифт
        self._apply_saved_font()

        # Обновляем заголовок окна
        self._update_title_from_current_tab()

        # Устанавливаем курсор
        def set_cursor(dt):
            if self.code_input:
                self.code_input.cursor = (0, 0)
                self.code_input.focus = True

        Clock.schedule_once(set_cursor, 0.5)

        # Восстанавливаем кнопку Run
        self._restore_run_button()

    def _create_run_button(self, main_layout, theme):
        """Создаёт плавающую кнопку запуска"""
        from kivy.uix.behaviors import ButtonBehavior
        from kivymd.uix.label import MDIcon
        from kivy.graphics import Ellipse

        category = get_screen_category()

        if category == 'tablet':
            run_btn_size = dp(90)
            margin_bottom = dp(90)
            icon_size = dp(32)
        elif category == 'large_phone':
            run_btn_size = dp(78)
            margin_bottom = dp(78)
            icon_size = dp(28)
        else:
            run_btn_size = dp(67)
            margin_bottom = dp(67)
            icon_size = dp(23)

        class RunButton(ButtonBehavior, FloatLayout):
            pass

        root_layout = FloatLayout()
        root_layout.add_widget(main_layout)

        self.run_btn = RunButton(size_hint=(None, None), size=(run_btn_size, run_btn_size))

        # Цвета кнопки
        if theme.get('name') == 'dark':
            bg_color = theme.get('run_btn_bg', (0.85, 0.88, 0.90, 1))
            icon_color = theme.get('run_btn_text', (0.18, 0.18, 0.19, 1))
        else:
            bg_color = theme.get('run_btn_bg', (0.596, 0.486, 1.0, 1))
            icon_color = theme.get('run_btn_text', (0, 0, 0, 1))

        def draw_round_btn(btn, *args):
            btn.canvas.before.clear()
            with btn.canvas.before:
                Color(*bg_color)
                Ellipse(pos=btn.pos, size=btn.size)

        self.run_btn.bind(pos=draw_round_btn, size=draw_round_btn)

        self.play_icon = MDIcon(
            icon='play', font_size=f"{dp(icon_size)}sp",
            theme_text_color="Custom", text_color=icon_color,
            pos_hint={"center_x": 0.5, "center_y": 0.5}
        )
        self.run_btn.add_widget(self.play_icon)

        def set_btn_pos(instance, value):
            x = root_layout.width - run_btn_size - dp(12)
            y = margin_bottom
            self.run_btn.pos = (x, y)

        root_layout.bind(size=set_btn_pos, pos=set_btn_pos)
        Clock.schedule_once(lambda dt: set_btn_pos(None, None), 0.3)
        self.run_btn.bind(on_press=self.run_code)
        root_layout.add_widget(self.run_btn)

        self.root_layout = root_layout
        return root_layout

    def _restore_run_button(self):
        """Восстанавливает иконку на кнопке запуска"""
        if not hasattr(self, 'run_btn') or self.run_btn is None:
            return

        from kivymd.uix.label import MDIcon
        from kivy.graphics import Ellipse

        category = get_screen_category()
        if category == 'tablet':
            icon_size = dp(32)
        elif category == 'large_phone':
            icon_size = dp(28)
        else:
            icon_size = dp(23)

        theme = ThemeManager.get_theme()
        if theme.get('name') == 'dark':
            icon_color = theme.get('run_btn_text', (0.18, 0.18, 0.19, 1))
        else:
            icon_color = theme.get('run_btn_text', (0, 0, 0, 1))

        # Очищаем и добавляем иконку заново
        self.run_btn.clear_widgets()
        self.play_icon = MDIcon(
            icon='play', font_size=f"{dp(icon_size)}sp",
            theme_text_color="Custom", text_color=icon_color,
            pos_hint={"center_x": 0.5, "center_y": 0.5}
        )
        self.run_btn.add_widget(self.play_icon)
        self.run_btn.canvas.ask_update()

    # ====================== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ======================

    def _load_language(self):
        """Загружает сохранённый язык"""
        # Сначала пробуем из настроек
        try:
            lang = SettingsManager.get_language()
            if lang in ['ru', 'en']:
                log_error(f"Loaded language from settings: {lang}")
                return lang
        except Exception as e:
            log_error(f"Error reading language from settings: {e}")

        # Затем из файла
        try:
            lang_file = user_data_path('language.txt')
            if os.path.exists(lang_file):
                with open(lang_file, 'r') as f:
                    lang = f.read().strip()
                    if lang in ['ru', 'en']:
                        log_error(f"Loaded language from file: {lang}")
                        # Сохраняем в настройки для синхронизации
                        SettingsManager.save_language(lang)
                        return lang
        except Exception as e:
            log_error(f"Error reading language file: {e}")

        log_error("Using default language: en")
        return 'en'

    def _save_language(self):
        """Сохраняет текущий язык"""
        try:
            # Сохраняем в настройки
            SettingsManager.save_language(self.current_language)
            # Сохраняем в файл
            lang_file = user_data_path('language.txt')
            ensure_user_data_dir()
            with open(lang_file, 'w') as f:
                f.write(self.current_language)
            log_error(f"Language saved: {self.current_language}")
        except Exception as e:
            log_error(f"Error saving language: {e}")

    def _apply_language_to_ui(self):
        """Применяет сохранённый язык ко всем UI элементам"""
        log_error(f"Applying language: {self.current_language}")

        # Обновляем спиннер примеров
        if hasattr(self, 'spinner'):
            self.spinner.text = self.tr.get('examples', 'Examples')
            self.spinner.values = self._get_example_titles()

        # Обновляем заголовки вкладок
        if hasattr(self, 'tab_manager'):
            for tab in self.tab_manager.tabs:
                current_title = tab['title']
                has_asterisk = current_title.startswith('*')
                clean_title = current_title.lstrip('*')

                if clean_title in ['Untitled', 'New', 'Новый']:
                    new_title = self.tr.get('untitled_tab', 'New')
                    if has_asterisk:
                        new_title = '*' + new_title
                    tab['title'] = new_title
            self.tab_manager._update_tab_bar()

        # Обновляем меню
        if hasattr(self, '_menu_dropdown'):
            self._create_menu_items(ThemeManager.get_theme())

        # Обновляем заголовок окна
        self._update_title_from_current_tab()

    def _get_autosave_path(self):
        """Возвращает путь к файлу автосохранения"""
        ensure_user_data_dir()
        return user_data_path('autosave.py')

    def _load_fonts(self):
        """Регистрирует шрифты"""
        from kivy.core.text import LabelBase

        fonts_dir = os.path.join(os.path.dirname(__file__), 'fonts')

        if not os.path.exists(fonts_dir):
            return

        # Базовые шрифты
        noto_path = os.path.join(fonts_dir, 'NotoSans-Regular.ttf')
        if os.path.exists(noto_path):
            LabelBase.register(name='Roboto', fn_regular=noto_path)

        # Моноширинные шрифты
        font_files = {
            'JetBrainsMono': 'JetBrainsMono.ttf',
            'FiraCode': 'FiraCode-Regular.ttf',
            'CascadiaCode': 'CascadiaCode.ttf',
            'IBMPlexMono': 'IBMPlexMono-Regular.ttf',
            'NotoSansMono': 'NotoSansMono.ttf',
            'SourceCodePro': 'SourceCodePro-Regular.otf',
        }

        for font_name, font_file in font_files.items():
            font_path = os.path.join(fonts_dir, font_file)
            if os.path.exists(font_path):
                LabelBase.register(name=font_name, fn_regular=font_path)

        # DejaVuSans для спецсимволов
        dejavu_path = os.path.join(fonts_dir, 'DejaVuSans.ttf')
        if os.path.exists(dejavu_path):
            LabelBase.register(name='DejaVuSans', fn_regular=dejavu_path)

        # Жирный шрифт для интерфейса
        bold_path = os.path.join(fonts_dir, 'SourceSansPro-Bold.ttf')
        if os.path.exists(bold_path):
            LabelBase.register(name='SourceBold', fn_regular=bold_path)

    def _apply_saved_font(self):
        """Применяет сохранённый шрифт к редактору"""
        saved_font = SettingsManager.get_font()
        font_files = {
            'DroidMono': 'DroidMono',
            'JetBrainsMono': 'JetBrainsMono',
            'FiraCode': 'FiraCode',
            'CascadiaCode': 'CascadiaCode',
            'IBMPlexMono': 'IBMPlexMono',
            'NotoSansMono': 'NotoSansMono',
            'SourceCodePro': 'SourceCodePro',
        }
        if saved_font in font_files and self.code_input:
            self.code_input.font_name = font_files[saved_font]

    def _set_initial_empty_lines(self):
        """Устанавливает начальные пустые строки"""

        def set_lines(dt):
            if self.code_input:
                self.code_input.text = ''
                if hasattr(self, 'editor') and self.editor:
                    self.editor.original_lines = ['']
                    self.editor._update_line_panel()
                self.code_input.cursor = (0, 0)

        Clock.schedule_once(set_lines, 0.3)

    def _setup_autosave(self):
        """Настраивает автосохранение"""
        self._last_autosave_time = 0
        self.code_input.bind(text=self._on_code_change_for_autosave)

    def _on_code_change_for_autosave(self, instance, value):
        """Обработчик изменения кода для автосохранения"""
        if hasattr(self, 'tab_manager') and self.tab_manager:
            if 0 <= self.tab_manager.active_index < len(self.tab_manager.tabs):
                current_tab = self.tab_manager.tabs[self.tab_manager.active_index]
                original = current_tab.get('original_content', "")
                has_changes = value != original

                if has_changes and current_tab.get('saved', True):
                    self.tab_manager.mark_tab_unsaved(self.tab_manager.active_index)
                elif not has_changes and not current_tab.get('saved', True):
                    self.tab_manager.mark_tab_saved(self.tab_manager.active_index)

        self._update_title_from_current_tab()

        current_time = time.time()
        if current_time - self._last_autosave_time > 2:
            self._last_autosave_time = current_time
            Clock.unschedule(self._do_autosave)
            Clock.schedule_once(self._do_autosave, 3)

    def _do_autosave(self, dt):
        """Выполняет автосохранение"""
        self._last_autosave_time = time.time()
        self.tab_manager.save_all_tabs()

    def _warmup_pygments(self):
        """Прогревает Pygments для устранения первого фриза"""

        def warmup(dt):
            try:
                from pygments.lexers import PythonLexer
                from pygments.styles import get_style_by_name
                default_style = ThemeManager.get_syntax_style()
                get_style_by_name(default_style)
                lexer = PythonLexer()
                list(lexer.get_tokens("def foo(): pass"))
                log_error("Pygments warmed up successfully")
            except Exception as e:
                log_error(f"Pygments warmup failed: {e}")

        Clock.schedule_once(warmup, 0.5)

    def _apply_saved_syntax_style(self, dt):
        """Применяет сохранённый стиль подсветки"""
        try:
            saved_style = SyntaxStyleManager.get_current_style()
            if hasattr(self, 'tab_manager'):
                SyntaxStyleManager.apply_style_to_all_tabs(self.tab_manager, saved_style)
        except:
            pass

    def _request_android_permissions(self):
        """Запрашивает разрешения для Android при первом запуске"""
        if platform != 'android':
            return

        try:
            from android.permissions import request_permissions, Permission
            permissions = [
                Permission.READ_EXTERNAL_STORAGE,
                Permission.WRITE_EXTERNAL_STORAGE
            ]
            if hasattr(Permission, 'MANAGE_EXTERNAL_STORAGE'):
                permissions.append(Permission.MANAGE_EXTERNAL_STORAGE)
            request_permissions(permissions)
            log_error("Android permissions requested")
        except Exception as e:
            log_error(f"Failed to request permissions: {e}")

    def _request_storage_permission(self):
        try:
            from jnius import autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            activity = PythonActivity.mActivity
            permissions = ["android.permission.READ_EXTERNAL_STORAGE", "android.permission.WRITE_EXTERNAL_STORAGE"]
            VERSION = autoclass('android.os.Build$VERSION')
            if VERSION.SDK_INT >= 23:
                activity.requestPermissions(permissions, 1)
        except Exception as e:
            log_error(f"Storage permission request error: {e}")

    def check_and_request_manage_storage(self):
        """Проверяет и запрашивает MANAGE_EXTERNAL_STORAGE (Android 11+)"""
        if platform != 'android':
            return

        try:
            # Проверяем версию Android
            from jnius import autoclass
            Build = autoclass('android.os.Build$VERSION')

            if Build.SDK_INT >= 30:  # Android 11+
                Environment = autoclass('android.os.Environment')
                if not Environment.isExternalStorageManager():
                    # Показываем диалог с инструкцией
                    self.show_manage_storage_dialog()
        except Exception as e:
            print(f"Permission check error: {e}")

    def show_manage_storage_dialog(self):
        """Показывает диалог с инструкцией по включению доступа к файлам"""
        theme = ThemeManager.get_theme()
        tr = self.tr  # ← используем текущий язык

        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.label import Label
        from kivy.uix.button import Button
        from kivy.metrics import dp
        from widgets.dialogs import ThemedPopup

        content = BoxLayout(orientation='vertical', padding=dp(15), spacing=dp(15))

        message = tr.get('storage_permission_message',
                         "To work with files on Android 11+, you need to allow file management.\n\n"
                         "1. Click 'Open Settings'\n"
                         "2. Enable 'Allow managing all files'\n"
                         "3. Return to the app"
                         )

        msg_label = Label(
            text=message,
            markup=True,
            color=theme['text_color'],
            font_size=dp(13),
            halign='center',
            valign='top',
            size_hint_y=None,
            height=dp(150)
        )
        msg_label.bind(width=lambda inst, val: setattr(inst, 'text_size', (val, None)))
        content.add_widget(msg_label)

        btn_layout = BoxLayout(size_hint_y=None, height=dp(45), spacing=dp(10))

        popup = ThemedPopup(
            title=tr.get('storage_permission_title', 'Storage Permission'),
            title_color=theme['popup_title'],
            title_bg=theme.get('popup_title_bg', theme['widget_bg']),
            popup_bg=theme.get('popup_bg', theme['widget_bg']),
            separator_color=theme.get('popup_separator', (0.25, 0.25, 0.25, 1)),
            content=content,
            size_hint=(0.9, 0.5),
            auto_dismiss=False
        )

        def open_settings(btn):
            popup.dismiss()
            try:
                from jnius import autoclass
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                Intent = autoclass('android.content.Intent')
                Settings = autoclass('android.provider.Settings')

                intent = Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION)
                intent.setData(autoclass('android.net.Uri').parse(
                    "package:" + PythonActivity.mActivity.getPackageName()
                ))
                PythonActivity.mActivity.startActivityForResult(intent, 1005)
            except Exception as e:
                print(f"Failed to open settings: {e}")
                self.show_result_popup(tr.get('storage_permission_failed',
                                              "Failed to open settings.\nEnable permission manually."))

        btn_settings = Button(
            text=tr.get('storage_permission_open_settings', 'Open Settings'),
            font_name='SourceBold',
            background_color=theme.get('btn_success_bg', (0.2, 0.5, 0.2, 1)),
            background_normal='', background_down='',
            color=(1, 1, 1, 1),
            font_size=dp(13),
            on_release=open_settings
        )

        btn_later = Button(
            text=tr.get('storage_permission_later', 'Later'),
            font_name='SourceBold',
            background_color=theme['widget_bg'],
            background_normal='', background_down='',
            color=theme['text_color'],
            font_size=dp(13),
            on_release=lambda x: popup.dismiss()
        )

        btn_layout.add_widget(btn_later)
        btn_layout.add_widget(btn_settings)
        content.add_widget(btn_layout)

        popup.open()

    def _save_autosave(self):
        """Сохраняет автосохранение"""
        try:
            tabs_data = {'active_index': self.tab_manager.active_index, 'tabs': []}
            for tab in self.tab_manager.tabs:
                tabs_data['tabs'].append({
                    'title': tab['title'],
                    'file': tab['file'],
                    'text': tab['editor'].get_text() if tab['editor'] else ''
                })
            dir_path = os.path.dirname(self._autosave_file)
            os.makedirs(dir_path, exist_ok=True)
            with open(self._autosave_file, 'w', encoding='utf-8') as f:
                json.dump(tabs_data, f, indent=2)
        except Exception as e:
            log_error(f"Autosave error: {e}")

    # ====================== ОБНОВЛЕНИЕ UI ======================

    def _update_bg(self, instance, value):
        """Обновляет фон"""
        if hasattr(self, 'bg_rect'):
            self.bg_rect.size = instance.size
            self.bg_rect.pos = instance.pos

    def apply_theme(self, theme):
        """Применяет тему ко всем компонентам"""
        self.current_theme_name = theme['name']
        Window.clearcolor = theme['window_bg']

        if hasattr(self, 'bg_color'):
            self.bg_color.rgba = theme['app_bg']

        # Обновляем верхние панели
        if hasattr(self, 'top_bar_builder'):
            self.top_bar_builder.update_theme(theme)

        # Обновляем панели действий
        if hasattr(self, 'action_bar'):
            self.action_bar.apply_theme(theme)
        if hasattr(self, 'symbol_bar'):
            self.symbol_bar.apply_theme(theme)

        # Обновляем кнопку Run
        if hasattr(self, 'run_btn'):
            self._update_run_button_theme(theme)

        # Обновляем панель вкладок
        if hasattr(self, 'tab_manager'):
            self.tab_manager.update_tab_bar_theme(theme)

    def _update_run_button_theme(self, theme):
        """Обновляет тему кнопки Run"""
        from kivy.graphics import Ellipse

        if theme.get('name') == 'dark':
            bg_color = theme.get('run_btn_bg', (0.85, 0.88, 0.90, 1))
            icon_color = theme.get('run_btn_text', (0.18, 0.18, 0.19, 1))
        else:
            bg_color = theme.get('run_btn_bg', (0.596, 0.486, 1.0, 1))
            icon_color = theme.get('run_btn_text', (0, 0, 0, 1))

        def update_bg(btn, *args):
            btn.canvas.before.clear()
            with btn.canvas.before:
                Color(*bg_color)
                Ellipse(pos=btn.pos, size=btn.size)

        update_bg(self.run_btn)

        if hasattr(self, 'play_icon'):
            self.play_icon.text_color = icon_color

    def on_resize(self, window, width, height):
        """Обработчик изменения размера окна"""
        Clock.schedule_once(lambda dt: self._refresh_ui_after_resize(), 0.1)

    def _refresh_ui_after_resize(self):
        """Обновляет UI после поворота экрана"""
        reset_screen_cache()

        # Обновляем верхние панели
        if hasattr(self, 'top_bar_builder'):
            self.top_bar_builder.update_theme(ThemeManager.get_theme())

        # Обновляем максимальное количество вкладок
        if hasattr(self, 'tab_manager'):
            self.tab_manager.max_visible = get_tab_count()
            self.tab_manager._update_tab_bar()

        # Обновляем высоту панелей
        category = get_screen_category()

        if hasattr(self, 'action_bar'):
            if category == 'tablet':
                self.action_bar.height = dp(52)
            elif category == 'large_phone':
                self.action_bar.height = dp(45)
            else:
                self.action_bar.height = dp(38)

        if hasattr(self, 'symbol_bar'):
            if category == 'tablet':
                self.symbol_bar.height = dp(42)
            elif category == 'large_phone':
                self.symbol_bar.height = dp(36)
            else:
                self.symbol_bar.height = dp(30)

        # Обновляем панель номеров строк
        if hasattr(self, 'editor') and self.editor:
            Clock.schedule_once(self.editor._force_line_panel_refresh, 0.2)
            Clock.schedule_once(lambda dt: self.editor._update_line_panel(), 0.3)

    def _update_title_from_current_tab(self):
        """Обновляет заголовок окна на основе активной вкладки"""
        if not hasattr(self, 'tab_manager') or not self.tab_manager:
            return

        active_tab = None
        if 0 <= self.tab_manager.active_index < len(self.tab_manager.tabs):
            active_tab = self.tab_manager.tabs[self.tab_manager.active_index]

        if active_tab:
            is_saved = active_tab.get('saved', True)
            title = active_tab.get('title', 'Untitled')
            file_path = active_tab.get('file')

            if file_path and os.path.exists(file_path):
                correct_title = os.path.basename(file_path)
                if active_tab['title'] != correct_title:
                    active_tab['title'] = correct_title
                    self.tab_manager._update_tab_bar()
                title = correct_title

            if not is_saved:
                self.title = f"*{title} - {self._original_title}"
            else:
                self.title = f"{title} - {self._original_title}"

            self._current_file = file_path
        else:
            self.title = self._original_title
            self._current_file = None

    def _process_pending_operations(self):
        """Выполняет отложенные операции"""
        if not self._ui_ready:
            return
        for op in self._pending_operations:
            try:
                op()
            except Exception as e:
                log_error(f"Pending operation error: {e}")
        self._pending_operations.clear()

    # ====================== ЗАПУСК КОДА ======================

    def run_code(self, instance):
        """Запускает выполнение кода"""
        if hasattr(self, '_code_running') and self._code_running:
            self.show_result_popup("Код уже выполняется...")
            return

        if not hasattr(self, 'editor') or not self.editor:
            self.show_result_popup("Ошибка: редактор не инициализирован")
            return

        # === ИСПРАВЛЕНИЕ ===
        code = self.editor.get_text()

        if not code.strip():
            self.show_result_popup(self.tr.get('enter_code', 'X Enter code'))
            return

        self._code_running = True
        instance.disabled = True

        def result_callback(result):
            self._code_running = False
            instance.disabled = False
            self._show_result(result)

        if not self.code_executor.run(code, self.input_handler.handle_input, result_callback):
            self._code_running = False
            instance.disabled = False

    def _show_result(self, result):
        """Показывает результат выполнения"""
        MAX_RESULT_LENGTH = 50000
        if len(result) > MAX_RESULT_LENGTH:
            result = result[:MAX_RESULT_LENGTH] + "\n\n... (вывод обрезан)"

        self.history.append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "out": result
        })

        if len(self.history) > self._max_history:
            self.history = self.history[-self._max_history:]

        self.show_result_popup(result)

    # ====================== ДИАЛОГИ ======================

    def show_result_popup(self, result, success=None):
        """
        Показывает результат в всплывающем окне

        Args:
            result: текст результата
            success: True - успех, False - ошибка, None - нейтрально (пока не используется)
        """
        if len(result) > 50000:
            result = result[:50000] + "\n\n... " + self.tr.get('output_truncated', '(truncated)')

        theme = ThemeManager.get_theme()

        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.button import Button
        from kivy.uix.scrollview import ScrollView
        from kivy.uix.textinput import TextInput
        from widgets.dialogs import ThemedPopup

        content = BoxLayout(orientation='vertical', padding=dp(5), spacing=dp(3))

        scroll = ScrollView(size_hint=(1, 0.85), do_scroll_x=False, do_scroll_y=True)

        # ИЗМЕНЕНИЕ: Заменили 'SourceBold' на 'DejaVuSans' (или 'NotoSans'), чтобы читались спецсимволы звезд и наград
        output_view = TextInput(
            text=str(result), readonly=True, font_size=dp(16),
            font_name='DejaVuSans', background_color=theme['result_bg'],
            foreground_color=theme['result_text'], do_wrap=True, multiline=True,
            size_hint_y=None, height=dp(33), padding=(dp(5), dp(5), dp(5), dp(5))
        )
        output_view.bind(minimum_height=output_view.setter('height'))
        scroll.add_widget(output_view)
        content.add_widget(scroll)

        btn_layout = BoxLayout(size_hint_y=None, height=dp(18), spacing=dp(3))

        btn_copy = Button(
            text=self.tr.get('copy_btn', 'Copy'), font_name='SourceBold',
            background_color=theme['widget_bg'], background_normal='', background_down='',
            color=theme['text_color'], font_size=dp(15), size_hint_y=None, height=dp(33),
            on_release=lambda x: self._copy_result(result)
        )

        btn_close = Button(
            text=self.tr.get('close', 'Close'), font_name='SourceBold',
            background_color=theme['widget_bg'], background_normal='', background_down='',
            color=theme['text_color'], font_size=dp(15), size_hint_y=None, height=dp(33)
        )

        btn_layout.add_widget(btn_copy)
        btn_layout.add_widget(btn_close)
        content.add_widget(btn_layout)

        category = get_screen_category()
        if category == 'tablet':
            size_hint = (0.75, 0.70)
        elif category == 'large_phone':
            size_hint = (0.85, 0.76)
        else:
            size_hint = (0.90, 0.82)

        if hasattr(self, 'wrap_widget_buttons'):
            self.wrap_widget_buttons(content)

        popup = ThemedPopup(
            title=self.tr.get('result_title', 'Result'),
            popup_bg=theme.get('popup_bg', (0.188, 0.204, 0.251, 1)),
            title_bg=theme.get('popup_title_bg', (0.188, 0.204, 0.251, 1)),
            title_color=theme['popup_title'], content=content, size_hint=size_hint,
            auto_dismiss=False, separator_color=theme.get('popup_separator', (0.25, 0.25, 0.25, 1))
        )
        btn_close.bind(on_release=popup.dismiss)
        popup.open()
        self._popup = popup

    def _copy_result(self, text):
        """Копирует результат в буфер обмена"""
        Clipboard.copy(text)
        if platform == 'android':
            android_copy(text)
        self.show_result_popup(self.tr.get('result_copied', '[OK] Copied'))

    # ====================== ФАЙЛОВЫЕ ОПЕРАЦИИ ======================

    def show_load_dialog(self, instance=None):
        """Открывает диалог выбора файла"""
        from file_manager import FileBrowserPopup

        browser = FileBrowserPopup(
            self, self.file_manager,
            title=self.tr.get('open', 'Open file'), mode="open"
        )
        browser.show(self.file_handlers.on_file_loaded)
        self._current_file_popup = browser

    def show_save_dialog(self, instance=None):
        """Открывает диалог сохранения файла"""
        from file_manager import FileBrowserPopup

        suggested_name = "script.py"
        if self._current_file:
            suggested_name = os.path.basename(self._current_file)

        browser = FileBrowserPopup(
            self, self.file_manager,
            title=self.tr.get('save', 'Save file'), mode="save"
        )
        browser.show(self.file_handlers.on_file_saved, save_filename=suggested_name)
        self._current_file_popup = browser

    def _save_tab_content_by_id(self, file_path, content, tab_id):
        """Сохраняет содержимое вкладки по известному пути файла"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            filename = os.path.basename(file_path)

            # Находим вкладку по ID и отмечаем как сохранённую
            if hasattr(self, 'tab_manager') and self.tab_manager:
                for i, tab in enumerate(self.tab_manager.tabs):
                    if tab.get('id') == tab_id:
                        tab['file'] = file_path
                        tab['original_content'] = content
                        self.tab_manager.mark_tab_saved(i)
                        break

            self._current_file = file_path
            self._update_title_from_current_tab()
        except Exception as e:
            self.show_result_popup(f"Error saving: {e}")

    def _save_tab_as_by_id(self, content, tab_id):
        """Открывает диалог 'Сохранить как' для вкладки без привязанного файла"""
        from file_manager import FileBrowserPopup

        def on_saved(file_path, saved_content):
            """Callback после выбора пути сохранения"""
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                filename = os.path.basename(file_path)

                if hasattr(self, 'tab_manager') and self.tab_manager:
                    for i, tab in enumerate(self.tab_manager.tabs):
                        if tab.get('id') == tab_id:
                            tab['file'] = file_path
                            tab['title'] = filename
                            tab['original_content'] = content
                            self.tab_manager.mark_tab_saved(i)
                            break

                self._current_file = file_path
                self._update_title_from_current_tab()
            except Exception as e:
                self.show_result_popup(f"Error saving: {e}")

        browser = FileBrowserPopup(
            self, self.file_manager,
            title=self.tr.get('save', 'Save file'), mode="save"
        )
        browser.show(on_saved, save_filename="script.py")
        self._current_file_popup = browser

    # ====================== ПОИСК И ЗАМЕНА ======================

    def show_search_only_dialog(self, instance=None):
        """Показывает диалог поиска"""
        print("[DEBUG] show_search_only_dialog called!")
        from widgets.dialogs import SearchOnlyPopup
        from kivy.metrics import dp

        self.dismiss_search()
        print("[DEBUG] Creating SearchOnlyPopup")

        content = SearchOnlyPopup(self.code_input)
        content.size_hint_y = None
        content.height = dp(120)
        content.pos_hint = {'top': 1}

        self.search_widget = content
        print("[DEBUG] Looking for root_layout")

        if hasattr(self, 'root_layout'):
            print("[DEBUG] Adding to root_layout")
            self.root_layout.add_widget(content)
        else:
            # Ищем корневой виджет
            print("[DEBUG] root_layout not found, searching...")
            for child in self.root.children:
                print(f"[DEBUG] child: {child}")
                if hasattr(child, 'children'):
                    for sub in child.children:
                        print(f"[DEBUG] sub: {sub}")
                        if isinstance(sub, FloatLayout):
                            print("[DEBUG] Found FloatLayout, adding widget")
                            sub.add_widget(content)
                            break
                    break

        print("[DEBUG] Scheduling focus")
        Clock.schedule_once(lambda dt: content._focus_search(), 0.3)

    def show_search_replace_dialog(self, instance=None):
        """Показывает диалог поиска и замены"""
        self.dismiss_search()

        from widgets.dialogs import SearchReplacePopup

        content = SearchReplacePopup(self.code_input)
        content.size_hint_y = None
        content.height = dp(155)
        content.pos_hint = {'top': 1}

        self.search_widget = content

        if hasattr(self, 'root_layout'):
            self.root_layout.add_widget(content)
        else:
            for child in self.root.children:
                if hasattr(child, 'children'):
                    for sub in child.children:
                        if isinstance(sub, FloatLayout):
                            sub.add_widget(content)
                            break
                    break

        Clock.schedule_once(lambda dt: content._focus_search(), 0.3)

    def show_goto_line_dialog(self, instance=None):
        """Показывает диалог перехода к строке"""
        self.dismiss_search()

        from widgets.dialogs import GotoLinePopup

        content = GotoLinePopup(self.code_input)
        content.size_hint_y = None
        content.height = dp(95)
        content.pos_hint = {'top': 1}

        self.search_widget = content

        if hasattr(self, 'root_layout'):
            self.root_layout.add_widget(content)
        else:
            for child in self.root.children:
                if hasattr(child, 'children'):
                    for sub in child.children:
                        if isinstance(sub, FloatLayout):
                            sub.add_widget(content)
                            break
                    break

        Clock.schedule_once(lambda dt: content._focus_input(), 0.3)

    def dismiss_search(self):
        """Закрывает окно поиска"""
        if hasattr(self, 'search_widget') and self.search_widget:
            try:
                self.search_widget.parent.remove_widget(self.search_widget)
            except Exception as e:
                log_error(f"Error removing search widget: {e}")
            self.search_widget = None

        if hasattr(self, 'code_input') and self.code_input:
            Clock.schedule_once(lambda dt: setattr(self.code_input, 'focus', True), 0.1)

    # ====================== ПРИМЕРЫ КОДА ======================

    def _on_examples_loaded(self, examples):
        """Вызывается когда примеры загружены"""
        self.examples_loaded = True
        # Обновляем спиннер, если он уже создан
        if hasattr(self, 'spinner') and self.spinner:
            self.spinner.values = self._get_example_titles()
        print("[DEBUG] Examples loaded successfully")

    def _get_example_titles(self):
        """Возвращает локализованные названия примеров для спиннера"""
        from managers import examples_manager
        return examples_manager.get_localized_titles(self.current_language)

    def load_example(self, spinner, text):
        """Загружает выбранный пример"""
        #self.vibrate_short()

        if not text or text == self.tr.get('examples', 'Examples'):
            return

        # Получаем код примера из менеджера с текущим языком
        from managers import examples_manager
        code = examples_manager.get_example(text, self.current_language)

        print(f"[DEBUG] Loading example: {text}")
        print(f"[DEBUG] Current language: {self.current_language}")
        print(f"[DEBUG] Code length: {len(code)}")

        if code.startswith('# Загрузка') or code.startswith('# Loading'):
            # Если примеры ещё не загружены, показываем сообщение
            self.show_result_popup("Загрузка примеров...\nПодождите секунду")
            # Пробуем загрузить
            examples_manager.load_examples_async()
            # Повторяем попытку через 0.5 секунды
            Clock.schedule_once(lambda dt: self.load_example(spinner, text), 0.5)
            return

        self.code_input.text = code
        if hasattr(self, 'editor') and self.editor:
            self.editor.original_lines = code.split('\n')
            self.editor._update_line_panel()
            Clock.schedule_once(self.editor._update_text_width, 0.1)

        self._current_file = None
        self._update_title_from_current_tab()

    # ====================== ИСТОРИЯ И ФОРМАТИРОВАНИЕ ======================

    def show_history(self, instance):
        """Показывает историю выполнения"""
        if not self.history:
            self.show_result_popup(self.tr.get('history_empty', 'History is empty'))
            return

        lines = []
        for h in self.history[-10:]:
            out = h['out']
            if len(out) > 300:
                out = out[:300] + "..."
            lines.append(f"[{h['time']}] {out}\n{'-' * 40}")

        self.show_result_popup("\n".join(lines))

    def format_code(self, instance):
        """Форматирует код через autopep8"""
        import threading

        code = self.code_input.text
        if not code.strip():
            self.show_result_popup(self.tr.get('no_code', 'No code to format'))
            return

        self.run_btn.disabled = True

        def do_format():
            try:
                import autopep8
                formatted = autopep8.fix_code(
                    code,
                    options={'aggressive': 1, 'indent_size': 4, 'max_line_length': 88}
                )
                Clock.schedule_once(lambda dt: self._apply_formatting(formatted))
            except ImportError:
                formatted = self._basic_format(code)
                Clock.schedule_once(lambda dt: self._apply_formatting(formatted))
            except Exception as e:
                Clock.schedule_once(lambda dt: self._formatting_error(str(e)))

        threading.Thread(target=do_format, daemon=True).start()

    def _basic_format(self, code: str) -> str:
        """Базовое форматирование (fallback)"""
        lines = code.split('\n')
        formatted = []
        indent_level = 0

        for raw_line in lines:
            stripped = raw_line.strip()

            if not stripped:
                formatted.append(raw_line)
                continue

            if stripped.startswith(('else:', 'elif ', 'except ', 'finally:')):
                indent_level = max(0, indent_level - 1)

            indent = '    ' * indent_level
            formatted.append(indent + stripped)

            if (stripped.endswith(':') and not stripped.startswith(('import', 'from', 'elif', 'else', 'except'))):
                indent_level += 1

        return '\n'.join(formatted)

    def _apply_formatting(self, formatted):
        """Применяет отформатированный код"""
        self.run_btn.disabled = False

        if formatted.strip() == self.code_input.text.strip():
            self.show_result_popup(self.tr.get('formatted_fail', '! No changes needed'))
            return

        try:
            cursor_pos = self.code_input.cursor_index()
        except:
            cursor_pos = 0

        self.code_input.text = formatted

        if hasattr(self, 'editor') and self.editor:
            self.editor.original_lines = formatted.split('\n')
            self.editor._update_line_panel()
            Clock.schedule_once(self.editor._update_text_width, 0.1)

        try:
            if cursor_pos <= len(formatted):
                self.code_input.cursor = self.code_input.get_cursor_from_index(cursor_pos)
        except:
            pass

        self.show_result_popup(self.tr.get('formatted_ok', '[OK] Code formatted'))

    def _formatting_error(self, error_msg):
        """Обрабатывает ошибку форматирования"""
        self.run_btn.disabled = False
        self.show_result_popup(f"{self.tr.get('error', 'Error')}:\n{error_msg[:250]}")

    # ====================== МЕНЮ НАСТРОЕК ======================

    def _open_settings_menu(self, button):
        """Открывает меню настроек"""
        if self._settings_menu is None:
            self._settings_menu = SettingsMenu(self)
        self._settings_menu.show(self.menu_button)

    def show_context_menu(self, instance):
        """Показывает контекстное меню (кнопка ☰)"""
        #self.vibrate_short()

        theme = ThemeManager.get_theme()
        from kivy.uix.dropdown import DropDown

        if not hasattr(self, '_menu_dropdown') or not self._menu_dropdown:
            self._menu_dropdown = DropDown()
            self._menu_dropdown.auto_width = False
            self._menu_dropdown.width = dp(167)
            self._create_menu_items(theme)

        def open_dropdown(*args):
            self._menu_dropdown.open(instance)
            win_width, win_height = Window.size
            if self._menu_dropdown.x + self._menu_dropdown.width > win_width:
                self._menu_dropdown.x = win_width - self._menu_dropdown.width - dp(3)
            elif self._menu_dropdown.x < 0:
                self._menu_dropdown.x = dp(3)
            if self._menu_dropdown.y < 0:
                self._menu_dropdown.y = instance.y + instance.height
            elif self._menu_dropdown.y + self._menu_dropdown.height > win_height:
                self._menu_dropdown.y = instance.y - self._menu_dropdown.height

        Clock.schedule_once(open_dropdown, 0.05)

    def _create_menu_items(self, theme):
        """Создаёт пункты главного меню"""
        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.label import Label
        from kivy.graphics import Color, Rectangle, Line
        from kivy.uix.behaviors import ButtonBehavior
        from kivymd.uix.label import MDIcon

        self._menu_dropdown.clear_widgets()
        tr = self.tr

        # Стилизация фона
        if hasattr(self._menu_dropdown, 'container'):
            container = self._menu_dropdown.container
            container.canvas.before.clear()
            with container.canvas.before:
                Color(*theme.get('action_bar_bg', theme['widget_bg']))
                Rectangle(pos=container.pos, size=container.size)
            container.bind(
                pos=lambda inst, val: self._update_menu_container_bg(inst, theme),
                size=lambda inst, val: self._update_menu_container_bg(inst, theme)
            )

        menu_items = [
            ('folder-open', tr['load'], self.show_load_dialog),
            ('content-save', tr['save'], self.show_save_dialog),
            ('magnify', tr['find'], self.show_search_only_dialog),
            ('find-replace', tr['find_replace'], self.show_search_replace_dialog),
            ('history', tr['history'], self.show_history),
            ('code-tags', tr['format'], self.format_code),
            ('cog', tr['settings'], self._open_settings_menu),
        ]

        class MenuItem(ButtonBehavior, BoxLayout):
            pass

        btn_bg = theme.get('action_bar_bg', theme['widget_bg'])

        for icon_name, text, func in menu_items:
            box = MenuItem(
                orientation='horizontal', size_hint_y=None, height=dp(35),
                padding=(dp(8), 0), spacing=dp(5)
            )

            icon = MDIcon(
                icon=icon_name, font_size=f"{dp(10)}sp", theme_text_color="Custom",
                text_color=theme['text_color'], size_hint_x=None, width=dp(17)
            )

            lbl = Label(
                text=text, color=theme['text_color'], font_size=dp(15),
                font_name='SourceBold', halign='left', valign='middle'
            )

            box.add_widget(icon)
            box.add_widget(lbl)

            box.canvas.before.clear()
            with box.canvas.before:
                Color(*btn_bg)
                Rectangle(pos=box.pos, size=box.size)
                Color(btn_bg[0] + 0.08, btn_bg[1] + 0.08, btn_bg[2] + 0.08, 1)
                Line(rectangle=(box.pos[0], box.pos[1], box.size[0], box.size[1]), width=dp(0.5))

            box.bind(
                pos=lambda inst, val, bg=btn_bg: self._update_menu_btn_bg(inst, bg),
                size=lambda inst, val, bg=btn_bg: self._update_menu_btn_bg(inst, bg)
            )
            box.bind(on_release=lambda bt, f=func: self.menu_action(bt, f))
            self._menu_dropdown.add_widget(box)

        # ========== ДОБАВИТЬ ОБЁРТКУ КНОПОК В ГЛАВНОМ МЕНЮ ==========
        if hasattr(self, 'wrap_widget_buttons'):
            for child in self._menu_dropdown.container.children:
                self.wrap_widget_buttons(child)

        self._menu_dropdown.width = dp(167)

    def menu_action(self, button, func):
        """Обработчик нажатия на пункт меню"""
        #self.vibrate_short()
        if hasattr(self, '_menu_dropdown'):
            self._menu_dropdown.dismiss()
        func(None)

    def _update_menu_container_bg(self, instance, theme):
        """Обновляет фон контейнера меню"""
        if not hasattr(instance, 'canvas'):
            return
        instance.canvas.before.clear()
        with instance.canvas.before:
            Color(*theme.get('action_bar_bg', theme['widget_bg']))
            Rectangle(pos=instance.pos, size=instance.size)

    def _update_menu_btn_bg(self, instance, bg_color):
        """Обновляет фон кнопки меню"""
        if not hasattr(instance, 'canvas'):
            return
        instance.canvas.before.clear()
        with instance.canvas.before:
            Color(*bg_color)
            Rectangle(pos=instance.pos, size=instance.size)
            Color(bg_color[0] + 0.08, bg_color[1] + 0.08, bg_color[2] + 0.08, 1)
            Line(rectangle=(instance.pos[0], instance.pos[1], instance.size[0], instance.size[1]), width=dp(0.5))

    def _update_ui_language(self):
        """Обновляет язык интерфейса при смене языка"""
        tr = self.tr

        # Переименовываем вкладки
        if hasattr(self, 'tab_manager'):
            for tab in self.tab_manager.tabs:
                current_title = tab['title']
                has_asterisk = current_title.startswith('*')
                clean_title = current_title.lstrip('*')

                if clean_title in ['Untitled', 'New', 'Новый']:
                    new_title = tr.get('untitled_tab', 'New')
                    if has_asterisk:
                        new_title = '*' + new_title
                    tab['title'] = new_title
            self.tab_manager._update_tab_bar()

        # Обновляем верхние панели
        if hasattr(self, 'top_bar_builder'):
            self.top_bar_builder.update_language()

        # Обновляем кнопку курса
        if hasattr(self, 'course_btn') and self.course_btn:
            self.course_btn.text = tr.get('course', 'Course')

        # Обновляем меню
        if hasattr(self, '_menu_dropdown'):
            self._create_menu_items(ThemeManager.get_theme())

        # Обновляем заголовок
        self._update_title_from_current_tab()

        # Перезагружаем примеры при смене языка
        from managers import examples_manager
        examples_manager.reload()

        # Обновляем спиннер
        if hasattr(self, 'spinner') and self.spinner:
            current_text = self.spinner.text
            self.spinner.values = self._get_example_titles()
            self.spinner.text = current_text

        # Сохраняем язык
        self._save_language()

        print(f"[DEBUG] Language changed to: {self.current_language}")

    # ====================== ВИБРАЦИЯ ======================

    def vibrate_short(self):
        """Короткая вибрация - ОТКЛЮЧЕНА, используется VibrationManager"""
        # ВСЕ РУЧНЫЕ ВЫЗОВЫ ОТКЛЮЧЕНЫ
        # try:
        #     from plyer import vibrator
        #     vibrator.vibrate(0.02)
        # except:
        #     pass
        pass

    # ====================== ЖИЗНЕННЫЙ ЦИКЛ ======================

    def on_start(self):
        """Запуск приложения"""
        from kivy.clock import Clock

        # Применяем язык при старте
        Clock.schedule_once(lambda dt: self._apply_language_to_ui(), 0.2)

        if platform == 'android':
            from android.permissions import request_permissions, Permission
            from kivy.clock import Clock

            def perm_callback(permissions, results):
                if all(results):
                    Clock.schedule_once(lambda dt: self.refresh_file_list(), 1.0)

            request_permissions([Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE], perm_callback)

    def refresh_file_list(self):
        """Обновляет список файлов (для совместимости)"""
        if hasattr(self, '_current_file_popup') and self._current_file_popup:
            # Если есть открытый диалог, обновляем его
            if hasattr(self._current_file_popup, '_refresh_list'):
                self._current_file_popup._refresh_list()

    def on_pause(self):
        """Пауза приложения"""
        self.tab_manager.save_all_tabs()
        return True

    def on_resume(self):
        """Возврат в приложение"""
        reset_screen_cache()
        Clock.schedule_once(lambda dt: self._refresh_ui_after_resize(), 0.1)
        return True

    def on_stop(self):
        """Остановка приложения"""
        self.tab_manager.save_all_tabs()
        self._cleanup_resources()
        return True

    def _cleanup_resources(self):
        """Очистка ресурсов"""
        if hasattr(self, 'action_bar') and hasattr(self.action_bar, 'cleanup'):
            self.action_bar.cleanup()
        if hasattr(self, 'symbol_bar') and hasattr(self.symbol_bar, 'cleanup'):
            self.symbol_bar.cleanup()
        ThemeManager.unregister(self)

if __name__ == "__main__":
    PythonLearningApp().run()
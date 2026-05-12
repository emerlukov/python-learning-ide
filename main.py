"""
Python Learning App
Версия: 3.4.0
- Добавлена светная тема!!!
- Проблема с поднятием интерфейса при первом запуске решена!!!
- Undo и Redo работают!!!
- Установлен английский язык в качестве стандартного.
- Добавлен запрос подтверждения перед выполнением действия "Очистить" (Clean)!!!
- Частично перебрал переводы!!!
- Удаление 4 пробелов!!!
- Добавлена видимая табуляция!!!
- Мелкие правки с вкладками, автосохранением и тд. !!!
- Смена подсветки синтаксиса!!!
- Мелкие доработки!!!
- С иконками !!!
- Смена шрифтов!!!
- Проведено очистку кода от мусора!!!
- Добавлены шрифты в меню fonts!!!
- Мелкие правки!!!
- UI масштабируется через kivy.metrics dp/sp!!!
- Исправлен хрупкий хак с unbind/bind в _ensure_trailing_empty_lines!!!
- Смена цветов светлой темы!!!
"""

# ====================== ИМПОРТ СТАНДАРТНЫХ БИБЛИОТЕК ======================
import sys
import json
import os
import io
import gc
import threading
import traceback
import urllib.request
import urllib.error
import ssl
import time
import re
import builtins
from datetime import datetime

# ====================== ИМПОРТ СТОРОННИХ БИБЛИОТЕК ======================
try:
    import autopep8
    HAS_AUTOPEP8 = True
except ImportError:
    autopep8 = None
    HAS_AUTOPEP8 = False

# ====================== ИМПОРТ БИБЛИОТЕК ANVPY (ANDROID) ======================
try:
    import anv
    from android import request_permissions, Permission
    try:
        import androidstorage
    except ImportError:
        androidstorage = None
    ANV_AVAILABLE = True
except ImportError:
    ANV_AVAILABLE = False
    androidstorage = None
    print("Внимание: Запуск не в среде AnvPy. Некоторые функции могут не работать.")

# ====================== ИМПОРТ БИБЛИОТЕК PLYER ======================
try:
    from plyer import storagepath
    PLYER_AVAILABLE = True
except:
    PLYER_AVAILABLE = False

# ====================== ИМПОРТ КОМПОНЕНТОВ KIVY ======================
from kivy.app import App
from kivymd.app import MDApp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.textinput import TextInput
from kivy.uix.codeinput import CodeInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.spinner import Spinner
from kivy.uix.scrollview import ScrollView
from kivy.uix.dropdown import DropDown
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle, Ellipse, Line
from kivy.core.clipboard import Clipboard
from kivy.core.window import Window
from kivy.core.text import LabelBase
from kivy.config import Config
from kivy.clock import Clock
from kivy.properties import ColorProperty, ListProperty, StringProperty
from kivy.lang import Builder
from kivy.utils import platform
from kivy.metrics import dp, sp

# ====================== ГЛОБАЛЬНЫЙ ФЛАГ ОТЛАДКИ ======================
DEBUG = True

# ====================== ПРОВЕРКА НАЛИЧИЯ PYGMENTS (ПОДСВЕТКА СИНТАКСИСА) ======================
try:
    from pygments.lexers import PythonLexer
    from pygments.styles import get_style_by_name
    HAS_PYGMENTS = True
except ImportError:
    PythonLexer = None
    HAS_PYGMENTS = False

# Регистрируем шрифт до настроек Kivy
from kivy.core.text import LabelBase
if os.path.exists('/system/fonts/SourceSansPro-Bold.ttf'):
    LabelBase.register(name='SourceBold',
                       fn_regular='/system/fonts/SourceSansPro-Bold.ttf')

# ====================== НАСТРОЙКИ KIVY ======================
Config.set('graphics', 'maxfps', '30')
Config.set('kivy', 'window_icon', '')
Config.set('kivy', 'window_title', 'Python Learning IDE')
Config.set('kivy', 'exit_on_escape', '0')
Config.set('kivy', 'keyboard_mode', 'systemanddock')
Config.set('kivy', 'default_font', 'SourceBold')

Window.allow_screensaver = True
Window.softinput_mode = ''

# ====================== ОТКЛЮЧЕНИЕ СТАНДАРТНЫХ СТИЛЕЙ ======================
Builder.load_string('''
<-MyActionBar>:
    canvas.before:
        Clear
    canvas.after:
        Clear
    background_color: [0, 0, 0, 0]
    border: [0, 0, 0, 0]
    background_image: ''

<-MySymbolScrollBar>:
    canvas.before:
        Clear
    canvas.after:
        Clear
    background_color: [0, 0, 0, 0]
    border: [0, 0, 0, 0]
    background_image: ''
''')

# ====================== ИСПРАВЛЕНИЕ ОШИБКИ FOCUS ======================
def patched_excepthook(exctype, value, traceback_obj):
    """
    Игнорирует ошибку 'MainApp' object has no attribute 'focus',
    которая возникает при сворачивании/разворачивании приложения.
    """
    if exctype == AttributeError and "'MainApp' object has no attribute 'focus'" in str(value):
        return
    sys.__excepthook__(exctype, value, traceback_obj)

sys.excepthook = patched_excepthook

# ====================== ОТЛАДОЧНЫЕ ФУНКЦИИ ======================
def log_error(msg):
    """
    Записывает отладочную информацию в файл на устройстве.
    Используется для отладки на Android, где нет консоли.
    Включить: DEBUG = True
    """
    if not DEBUG:
        return
    try:
        log_paths = [
            '/storage/emulated/0/Download/app_debug.log',
            '/storage/emulated/0/app_debug.log',
            '/sdcard/app_debug.log'
        ]
        for log_path in log_paths:
            try:
                log_dir = os.path.dirname(log_path)
                if log_dir and not os.path.exists(log_dir):
                    os.makedirs(log_dir, exist_ok=True)
                with open(log_path, 'a', encoding='utf-8') as f:
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    f.write(f"{timestamp}: {msg}\n")
                break
            except:
                continue
    except:
        pass

def android_copy(text):
    """
    Копирует текст в буфер обмена через Android API.
    Работает надёжнее, чем стандартный Clipboard Kivy.
    """
    try:
        from jnius import autoclass
        Context = autoclass('android.content.Context')
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        activity = PythonActivity.mActivity
        clipboard = activity.getSystemService(Context.CLIPBOARD_SERVICE)
        ClipData = autoclass('android.content.ClipData')
        clip = ClipData.newPlainText("python_ide", text)
        clipboard.setPrimaryClip(clip)
        return True
    except:
        return False

# ====================== ЭКСПОРТ ГЛОБАЛЬНЫХ ПЕРЕМЕННЫХ ======================
__all__ = ['HAS_PYGMENTS', 'PythonLexer', 'ThemeManager', 'SettingsManager']

# ====================== ПЕРЕВОДЫ (RU/EN) ======================
TRANSLATIONS = {
    'ru': {
        'ai_assistant': 'AI',
        'api_settings': 'API ключ',
        'examples': 'Примеры',
        'find_replace': 'Заменить',
        'format': 'Формат',
        'history': 'История',
        'language': 'Язык',
        'load': 'Загрузить',
        'new': 'Новый',
        'save': 'Сохранить',
        'syntax_highlight': 'Подсветка',
        'syntax_header': 'Выберите стиль подсветки:',
        'syntax_preview': 'Предпросмотр стиля',
        'apply': 'Применить',
        'syntax_menu_title': 'Стиль подсветки',
        'back': '← Назад',
        'auto': 'Авто',
        'clean': 'Удалить',
        'copy': 'Копия',
        'cut': 'Вырезать',
        'find': 'Поиск',
        'key': 'Ключ',
        'paste': 'Вставить',
        'redo': 'Вперед',
        'sel_all': 'Выделить',
        'tab': 'Tab',
        'undo': 'Назад',
        'run': '▶',
        'cancel': 'Отмена',
        'close': 'Закрыть',
        'delete': 'Удалить',
        'no': 'Нет',
        'ok': 'OK',
        'open': 'Открыть',
        'save_file': 'Сохранить',
        'yes': 'Да',
        'code_running': '✓ Код выполняется...',
        'code_success': '✓ Выполнено',
        'enter_code': '! Введите код',
        'error': '! Ошибка',
        'file_loaded': '✓ Загружено',
        'file_saved': '✓ Сохранено',
        'formatted_fail': '! Ошибка форматирования',
        'formatted_ok': '✓ Форматирование завершено!',
        'history_empty': '! История пуста',
        'new_file_created': '✓ Новый файл',
        'no_api_key': "! API ключ не задан",
        'result_copied': '✓ Скопировано',
        'find_all': 'Найти все',
        'find_text': 'Найти...',
        'found': 'Найдено',
        'found_matches': 'Найдено совпадений',
        'not_found': 'Нет',
        'replace': 'Заменить',
        'replace_all': 'Заменить все',
        'replace_text': 'Заменить...',
        'results': 'Результаты',
        'search': 'Поиск',
        'app_folder': '[App]',
        'download_folder': '[Download]',
        'empty': '[Пусто]',
        'error_load': '! Ошибка',
        'error_save': '! Ошибка',
        'file_name': 'Имя файла...',
        'no_access': '[Нет доступа]',
        'sdcard_folder': '[/sdcard]',
        'select_file': 'Выбор файла',
        'up_level': '▲ Вверх',
        'api_deleted': '! Ключ удалён',
        'api_info': 'aistudio.google.com/app/apikey',
        'api_key_hint': 'Ключ Gemini',
        'api_not_set': '! Ключ не задан',
        'api_ok': '✓ Ключ задан',
        'api_saved': '✓ Сохранено!',
        'api_title': 'API ключ',
        'ai_btn': 'Спросить',
        'ai_hint': 'Вопрос о Python...',
        'ai_placeholder': 'Ответ здесь...',
        'ai_thinking': 'Думаю...',
        'ai_title': 'AI Помощник',
        'already_exists': 'уже существует.',
        'confirm_title': 'Точно?',
        'exit_title': 'Выход',
        'exit_without_save': 'Выйти',
        'file_exists': 'Файл',
        'new_file_confirm': 'Создать без сохранения?',
        'overwrite_confirm': 'Перезаписать?',
        'save_and_exit': 'Сохранить',
        'save_before_exit': 'Сохранить перед выходом?',
        'unsaved_changes': 'Есть несохранённые изменения.',
        'clean_confirm': 'Вы уверены что хотите очистить весь код?',
        'syntax_style_saved': 'Стиль',
        'saved': 'сохранён',
        'input_hint': 'Текст...',
        'input_prompt': 'Значение:',
        'input_title': 'Ввод',
        'copy_btn': 'Копия',
        'result_title': 'Результат',
        'close_all_tabs': 'Закрыть все',
        'close_other_tabs': 'Закрыть другие',
        'duplicate_tab': 'Дублировать',
        'rename_tab': 'Переименовать',
        'untitled_tab': 'Новый',
        'autocomplete_title': 'Автодополнение',
        'encoding_error': '! Не удалось определить кодировку',
        'file_too_big': '! Файл слишком большой (>1MB)',
        'keywords_title': 'Ключевые слова Python',
        'line': 'Строка',
        'network_error': '! Ошибка сети',
        'no_permission': 'Нет прав на запись',
        'no_read_permission': 'Нет прав на чтение',
        'of': 'из',
        'output_truncated': '(вывод обрезан)',
        'rate_limit': 'Лимит запросов. Ждем',
        'rate_limit_exceeded': 'Превышен лимит запросов.',
        'replaced': 'Заменено',
        'search_hint': 'Поиск...',
        'sec': 'сек',
        'example_1': '1. Hello World',
        'example_2': '2. Переменные',
        'example_3': '3. Ввод',
        'example_4': '4. Условия',
        'example_5': '5. Цикл For',
        'example_6': '6. Цикл While',
        'example_7': '7. Списки',
        'example_8': '8. Генераторы списков',
        'example_9': '9. Словари',
        'example_10': '10. Функции',
        'example_11': '11. Lambda',
        'example_12': '12. Классы',
        'example_13': '13. Наследование',
        'example_14': '14. Ошибки',
        'example_15': '15. Файлы',
        'example_16': '16. Рекурсия',
        'example_17': '17. Генераторы',
        'example_18': '18. Декораторы',
        'settings': 'Настройки',
        'select_language': 'Язык',
        'theme_settings': 'Тема',
        'editor_settings': 'Редактор',
        'in_development': 'В разработке...',
        'theme_dark': 'Тёмная',
        'theme_light': 'Светлая',
        'restart_for_syntax': 'Перезапустить приложение для полной смены подсветки синтаксиса?',
        'restart_info': 'Все вкладки будут сохранены и восстановлены.',
        'restart_btn': 'Перезапустить',
        'later_btn': 'Позже',
        'editor_font': 'Шрифт',
    },
    'en': {
        'ai_assistant': 'AI Assistant',
        'api_settings': 'API Key',
        'examples': 'Examples',
        'find_replace': 'Replace',
        'format': 'Format',
        'history': 'History',
        'language': 'Language',
        'load': 'Load',
        'new': 'New',
        'save': 'Save',
        'syntax_highlight': 'Highlight',
        'syntax_header': 'Select highlight style:',
        'syntax_preview': 'Style Preview',
        'apply': 'Apply',
        'syntax_menu_title': 'Syntax Style',
        'back': '← Back',
        'auto': 'Auto',
        'clean': 'Clean',
        'copy': 'Copy',
        'cut': 'Cut',
        'find': 'Find',
        'key': 'Key',
        'paste': 'Paste',
        'redo': 'Redo',
        'sel_all': 'Select All',
        'tab': 'Tab',
        'undo': 'Undo',
        'run': '▶',
        'cancel': 'Cancel',
        'close': 'Close',
        'delete': 'Delete',
        'no': 'No',
        'ok': 'OK',
        'open': 'Open',
        'save_file': 'Save',
        'yes': 'Yes',
        'code_running': '! Code is already running...',
        'code_success': '! Code executed successfully',
        'enter_code': '! Enter code before running',
        'error': '! Error',
        'file_loaded': '✓ File loaded',
        'file_saved': '✓ File saved',
        'formatted_fail': '! Failed to format code',
        'formatted_ok': '! Code formatted successfully',
        'history_empty': '! History is empty',
        'new_file_created': '✓ New file created',
        'no_api_key': "! API key not set.\nPress 'API Key' in menu",
        'result_copied': '✓ Copied to clipboard',
        'find_all': 'Find All',
        'find_text': 'Find...',
        'found': 'Found',
        'found_matches': 'Found matches',
        'not_found': 'Not found',
        'replace': 'Replace',
        'replace_all': 'Replace All',
        'replace_text': 'Replace with...',
        'results': 'Search Results',
        'search': 'Search',
        'app_folder': '[App]',
        'download_folder': '[Download]',
        'empty': '[Empty]',
        'error_load': '! Load error',
        'error_save': '! Save error',
        'file_name': 'File name...',
        'no_access': '[No access]',
        'sdcard_folder': '[/sdcard]',
        'select_file': 'Select file',
        'up_level': '▲ Up one level',
        'api_deleted': '! API key deleted',
        'api_info': 'Get key: aistudio.google.com/app/apikey',
        'api_key_hint': 'Paste your Gemini API key',
        'api_not_set': '! Key not set',
        'api_ok': '✓ Key is set',
        'api_saved': '✓ API key saved!',
        'api_title': 'API Key',
        'ai_btn': 'Ask AI',
        'ai_hint': 'Ask me anything about Python...',
        'ai_placeholder': 'AI response will appear here...',
        'ai_thinking': 'Thinking...',
        'ai_title': 'AI Assistant',
        'already_exists': 'already exists.',
        'confirm_title': 'Confirmation',
        'exit_title': 'Exit confirmation',
        'exit_without_save': 'Exit',
        'file_exists': 'File',
        'new_file_confirm': 'You have unsaved changes.\nCreate new file without saving?',
        'overwrite_confirm': 'Overwrite?',
        'save_and_exit': 'Save',
        'save_before_exit': 'Save file before exit?',
        'unsaved_changes': 'You have unsaved changes.',
        'clean_confirm': 'Are you sure you want to clear all code?',
        'syntax_style_saved': 'Style',
        'saved': 'saved',
        'input_hint': 'Enter text...',
        'input_prompt': 'Enter value:',
        'input_title': 'Input data',
        'copy_btn': 'Copy',
        'result_title': 'Result',
        'close_all_tabs': 'Close all',
        'close_other_tabs': 'Close others',
        'duplicate_tab': 'Duplicate',
        'rename_tab': 'Rename',
        'untitled_tab': 'New',
        'autocomplete_title': 'Autocomplete',
        'encoding_error': '! Cannot determine encoding',
        'file_too_big': '! File too large (>1MB)',
        'keywords_title': 'Python Keywords',
        'line': 'Line',
        'network_error': '! Network error',
        'no_permission': 'No write permission',
        'no_read_permission': 'No read permission',
        'of': 'of',
        'output_truncated': '(output truncated)',
        'rate_limit': 'Rate limit. Wait',
        'rate_limit_exceeded': 'Rate limit exceeded.',
        'replaced': 'Replaced',
        'search_hint': 'Search...',
        'sec': 'sec',
        'example_1': '1. Hello World',
        'example_2': '2. Variables',
        'example_3': '3. Input',
        'example_4': '4. Conditions',
        'example_5': '5. For Loop',
        'example_6': '6. While Loop',
        'example_7': '7. Lists',
        'example_8': '8. List Comprehensions',
        'example_9': '9. Dictionaries',
        'example_10': '10. Functions',
        'example_11': '11. Lambda',
        'example_12': '12. Classes',
        'example_13': '13. Inheritance',
        'example_14': '14. Errors',
        'example_15': '15. Files',
        'example_16': '16. Recursion',
        'example_17': '17. Generators',
        'example_18': '18. Decorators',
        'settings': 'Settings',
        'select_language': 'Language',
        'theme_settings': 'Theme',
        'editor_settings': 'Editor',
        'in_development': 'In development...',
        'theme_dark': 'Dark',
        'theme_light': 'Light',
        'restart_for_syntax': 'Restart app to fully apply syntax highlighting?',
        'restart_info': 'All tabs will be saved and restored.',
        'restart_btn': 'Restart',
        'later_btn': 'Later',
        'editor_font': 'Font',
    },
}

# [ВСЕ ЦВЕТОВЫЕ СХЕМЫ]
# ==================== ТЁМНАЯ ТЕМА ====================
DARK_THEME = {
    'name': 'dark',

    # ==================== ОСНОВНЫЕ ФОНЫ ====================
    'app_bg': (0.188, 0.204, 0.251, 1),        # фон всего приложения
    'window_bg': (0.06, 0.06, 0.06, 1),          # фон за границами приложения (Window.clearcolor)
    'widget_bg': (0.141, 0.145, 0.149, 1),       # фон кнопок, вкладок, попапов
    'text_color': (0.85, 0.88, 0.90, 1),          # цвет текста везде

    # ==================== ПАНЕЛИ ИНСТРУМЕНТОВ ====================
    'action_bar_bg': (0.18, 0.18, 0.19, 1),      # фон панели кнопок действий
    'top_bar_bg': (0.18, 0.18, 0.19, 1),          # фон верхней панели (Spinner + кнопка ☰)
    'symbol_btn_bg': (0.141, 0.145, 0.149, 1),   # фон кнопок на панелях
    'symbol_btn_text': (0.85, 0.88, 0.90, 1),     # цвет текста/иконок на кнопках панелей

    # ==================== РЕДАКТОР КОДА ====================
    'editor_bg': (0.188, 0.204, 0.251, 1),        # фон редактора кода
    'editor_text': (0.95, 0.95, 0.95, 1),          # цвет текста в редакторе
    'editor_cursor': (1.0, 1.0, 1.0, 1),           # цвет курсора
    'editor_selection': (1, 1, 1, 0.15),           # цвет выделения текста
    'panel_bg': (0.188, 0.204, 0.251, 1),          # фон панели с номерами строк
    'panel_text': (0.45, 0.48, 0.50, 1),           # цвет номеров строк
    'separator_color': (0.5, 0.5, 0.5, 0.3),       # разделитель панели строк и кода
    'current_line_highlight': (1, 1, 1, 0.04),     # подсветка текущей строки
    'indent_guide_color': (0.35, 0.38, 0.40, 0.30),# направляющие отступов

    # ==================== ПОЛЯ ВВОДА ====================
    'input_bg': (0.188, 0.204, 0.251, 1),          # фон полей ввода
    'input_text': (1.0, 1.0, 1.0, 1),              # цвет текста в полях ввода
    'input_cursor': (1.0, 1.0, 1.0, 1),            # цвет курсора в полях ввода
    'hint_text': (0.45, 0.48, 0.50, 1),            # цвет подсказок в пустых полях

    # ==================== ВКЛАДКИ ====================
    'tab_bar_bg': (0.18, 0.18, 0.19, 1),           # фон панели вкладок
    'tab_inactive_bg': (0.141, 0.145, 0.149, 1),   # фон неактивных вкладок
    'tab_active_bg': None,                          # фон активной вкладки (авто)
    'tab_add_btn_bg': (0.141, 0.145, 0.149, 1),    # фон кнопки добавления вкладки
    'tab_close_btn_text': (0.85, 0.88, 0.90, 1),   # цвет кнопки закрытия вкладки
    'tab_context_danger_bg': (0.5, 0.2, 0.2, 1),   # фон кнопки "Закрыть все"

    # ==================== ВЕРХНЯЯ ПАНЕЛЬ (Spinner + ☰) ====================
    'spinner_bg': (0.141, 0.145, 0.149, 1),        # фон выпадающего списка Примеров
    'spinner_text': (0.85, 0.88, 0.90, 1),          # текст в списке Примеров
    'spinner_dropdown_bg': (0.188, 0.204, 0.251, 1),# фон выпавшего меню Примеров
    'spinner_dropdown_text': (0.85, 0.88, 0.90, 1), # цвет пунктов в выпавшем меню
    'spinner_dropdown_selected_bg': (0.141, 0.145, 0.149, 1),# фон выбранного пункта
    'spinner_dropdown_btn_bg': (0.141, 0.14, 0.149, 1),# фон кнопок-примеров
    'menu_btn_bg': (0.141, 0.145, 0.149, 1),        # фон кнопки ☰
    'menu_btn_text': (0.85, 0.88, 0.90, 1),          # цвет значка ☰

    # ==================== ВСПЛЫВАЮЩИЕ ОКНА ====================
    'popup_bg': (0.188, 0.204, 0.251, 1),           # фон всплывающих окон
    'popup_title': (0.85, 0.88, 0.90, 1),            # цвет заголовка попапа
    'popup_title_bg': (0.188, 0.204, 0.251, 1),      # фон заголовка попапа
    'popup_separator': (0.25, 0.25, 0.25, 1),        # разделитель под заголовком попапа

    # ==================== КНОПКИ РАЗНЫХ ТИПОВ ====================
    'btn_success_bg': (0.2, 0.5, 0.2, 1),           # зелёные кнопки (Apply, Save)
    'btn_danger_bg': (0.5, 0.2, 0.2, 1),             # красные кнопки (Close, Delete)
    'btn_selected_file_bg': (0.3, 0.5, 0.3, 1),      # выделенный файл в диалоге
    'fold_btn_bg': (0.141, 0.145, 0.149, 1),         # фон кнопок сворачивания
    'fold_btn_text': (0.75, 0.78, 0.80, 1),           # текст кнопок сворачивания

    # ==================== КНОПКА ЗАПУСКА ====================
    'run_btn_bg': (0.85, 0.88, 0.90, 1),             # фон кнопки Run
    'run_btn_text': (0.18, 0.18, 0.19, 1),            # цвет значка ▶
    'run_btn_shadow': (0, 0, 0, 0.35),                # тень кнопки Run

    # ==================== ПРОЧЕЕ ====================
    'syntax_style': 'dracula',                        # стиль подсветки по умолчанию
    'result_bg': (0.188, 0.204, 0.251, 1),            # фон окна результата
    'result_text': (0.85, 0.88, 0.90, 1),             # текст в окне результата
    'stats_text': (0.60, 0.63, 0.65, 1),              # цвет пути к файлу
    'ai_response_bg': (0.06, 0.06, 0.06, 1),          # фон ответа AI
    'scroll_bar_color': (0.4, 0.4, 0.4, 0.9),         # полоса прокрутки активная
    'scroll_bar_inactive': (0.25, 0.25, 0.25, 0.6),   # полоса прокрутки неактивная
}

# ==================== СВЕТЛАЯ ТЕМА ====================
LIGHT_THEME = {
    'name': 'light',

    # ==================== ОСНОВНЫЕ ФОНЫ ====================
    'app_bg': (1.0, 1.0, 1.0, 1),                 # фон всего приложения — белый
    'window_bg': (1.0, 1.0, 1.0, 1),               # фон за границами — белый
    'widget_bg': (0.843, 0.816, 1.0, 1),            # фон кнопок — светло-фиолетовый #D7D0FF
    'text_color': (0, 0, 0, 1),                     # цвет текста — чёрный

    # ==================== ПАНЕЛИ ИНСТРУМЕНТОВ ====================
    'action_bar_bg': (0.843, 0.816, 1.0, 1),        # фон панели кнопок — #D7D0FF
    'top_bar_bg': (0.843, 0.816, 1.0, 1),            # фон верхней панели — #D7D0FF
    'symbol_btn_bg': (0.596, 0.486, 1.0, 1),         # фон кнопок на панелях — #987CFF
    'symbol_btn_text': (0, 0, 0, 1),                 # текст на кнопках панелей — чёрный

    # ==================== РЕДАКТОР КОДА ====================
    'editor_bg': (1.0, 1.0, 1.0, 1),                # фон редактора — белый
    'editor_text': (0, 0, 0, 1),                     # текст в редакторе — чёрный
    'editor_cursor': (0, 0, 0, 1),                   # курсор — чёрный
    'editor_selection': (0, 0, 0, 0.12),             # выделение текста
    'panel_bg': (0.843, 0.816, 1.0, 1),              # панель номеров строк — #D7D0FF
    'panel_text': (0.40, 0.40, 0.40, 1),             # номера строк — тёмно-серый
    'separator_color': (0.5, 0.5, 0.5, 0.3),         # разделитель панели строк
    'current_line_highlight': (0.7, 0.7, 0.7, 0.08), # подсветка строки курсора
    'indent_guide_color': (0.7, 0.7, 0.7, 0.30),     # направляющие отступов

    # ==================== ПОЛЯ ВВОДА ====================
    'input_bg': (1.0, 1.0, 1.0, 1),                 # фон полей ввода — белый
    'input_text': (0, 0, 0, 1),                      # текст в полях — чёрный
    'input_cursor': (0, 0, 0, 1),                    # курсор — чёрный
    'hint_text': (0.50, 0.50, 0.50, 1),              # подсказки — серый

    # ==================== ВКЛАДКИ ====================
    'tab_bar_bg': (0.596, 0.486, 1.0, 1),            # фон панели вкладок — #987CFF
    'tab_inactive_bg': (0.843, 0.816, 1.0, 1),       # неактивные вкладки — #D7D0FF
    'tab_active_bg': None,                            # активная вкладка (авто)
    'tab_add_btn_bg': (0.843, 0.816, 1.0, 1),        # кнопка добавления — #D7D0FF
    'tab_close_btn_text': (0, 0, 0, 1),              # кнопка закрытия — чёрный
    'tab_context_danger_bg': (0.7, 0.2, 0.2, 1),     # кнопка "Закрыть все" — красный

    # ==================== ВЕРХНЯЯ ПАНЕЛЬ (Spinner + ☰) ====================
    'spinner_bg': (0.596, 0.486, 1.0, 1),             # фон Примеров — #987CFF
    'spinner_text': (0, 0, 0, 1),                     # текст Примеров — чёрный
    'spinner_dropdown_bg': (1.0, 1.0, 1.0, 1),        # фон меню Примеров — белый
    'spinner_dropdown_text': (0, 0, 0, 1),            # пункты меню — чёрный
    'spinner_dropdown_selected_bg': (0.843, 0.816, 1.0, 1),# выбранный пункт — #D7D0FF
    'spinner_dropdown_btn_bg': (1.0, 1.0, 1.0, 1),    # кнопки-примеры — белый
    'menu_btn_bg': (0.596, 0.486, 1.0, 1),            # кнопка ☰ — #987CFF
    'menu_btn_text': (0, 0, 0, 1),                    # значок ☰ — чёрный

    # ==================== ВСПЛЫВАЮЩИЕ ОКНА ====================
    'popup_bg': (1.0, 1.0, 1.0, 1),                  # фон попапов — белый
    'popup_title': (0, 0, 0, 1),                      # заголовок попапа — чёрный
    'popup_title_bg': (0.843, 0.816, 1.0, 1),         # фон заголовка — #D7D0FF
    'popup_separator': (0.70, 0.69, 0.66, 1),         # разделитель попапа — светлый

    # ==================== КНОПКИ РАЗНЫХ ТИПОВ ====================
    'btn_success_bg': (0.2, 0.5, 0.2, 1),            # зелёные кнопки
    'btn_danger_bg': (0.7, 0.2, 0.2, 1),              # красные кнопки
    'btn_selected_file_bg': (0.3, 0.5, 0.3, 1),       # выделенный файл
    'fold_btn_bg': (0.843, 0.816, 1.0, 1),            # кнопки сворачивания — #D7D0FF
    'fold_btn_text': (0.35, 0.35, 0.35, 1),           # текст сворачивания — тёмный

    # ==================== КНОПКА ЗАПУСКА ====================
    'run_btn_bg': (0.596, 0.486, 1.0, 1),             # кнопка Run — #987CFF
    'run_btn_text': (0, 0, 0, 1),                     # значок ▶ — чёрный
    'run_btn_shadow': (0, 0, 0, 0.25),                # тень кнопки

    # ==================== ПРОЧЕЕ ====================
    'syntax_style': 'default',                         # стиль подсветки по умолчанию
    'result_bg': (1.0, 1.0, 1.0, 1),                  # фон результата — белый
    'result_text': (0, 0, 0, 1),                       # текст результата — чёрный
    'stats_text': (0.40, 0.40, 0.40, 1),              # путь к файлу — тёмно-серый
    'ai_response_bg': (1.0, 1.0, 1.0, 1),             # фон ответа AI — белый
    'scroll_bar_color': (0.6, 0.6, 0.6, 0.9),         # полоса прокрутки активная
    'scroll_bar_inactive': (0.8, 0.8, 0.8, 0.6),      # полоса прокрутки неактивная
}

# [Классы: ThemedPopup, ThemedSpinner, SettingsManager, LanguageSelectMenu,
#  ThemeSelectMenu, EditorSettingsMenu, FontSelectMenu, SyntaxStyleManager,
#  SyntaxHighlightMenu, SettingsMenu, ThemeManager]

class ThemedPopup(Popup):
    """Кастомный Popup с поддержкой тем"""
    def __init__(self, **kwargs):
        self._title_bg = kwargs.pop('title_bg', (0.188, 0.204, 0.251, 1))
        self._title_color = kwargs.pop('title_color', (0.85, 0.88, 0.90, 1))
        self._separator_color = kwargs.pop('separator_color', (0.25, 0.25, 0.25, 1))
        self._popup_bg = kwargs.pop('popup_bg', (0.188, 0.204, 0.251, 1))
        kwargs['background'] = ''
        kwargs['background_color'] = self._popup_bg
        super().__init__(**kwargs)
        self.separator_color = self._separator_color
        self._title_box = None
        self._popup_bg_color = None
        self._popup_bg_rect = None
        Clock.schedule_once(self._apply_full_theme, 0.1)

    def _apply_full_theme(self, dt):
        try:
            self._apply_popup_background()
            self._apply_title_theme()
            Clock.schedule_once(self._force_title_color, 0.15)
        except Exception as e:
            log_error(f"ThemedPopup error: {e}")

    def _apply_popup_background(self):
        self.canvas.before.clear()
        with self.canvas.before:
            self._popup_bg_color = Color(*self._popup_bg)
            self._popup_bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_popup_bg, size=self._update_popup_bg)

    def _apply_title_theme(self):
        self._title_box = self._find_title_box(self)
        if not self._title_box:
            return
        self._title_box.background = ''
        self._title_box.background_normal = ''
        self._title_box.background_down = ''
        self._title_box.canvas.before.clear()
        with self._title_box.canvas.before:
            Color(*self._title_bg)
            Rectangle(pos=self._title_box.pos, size=self._title_box.size)
        self._title_box.bind(pos=self._update_title_bg, size=self._update_title_bg)
        for child in self._title_box.children:
            if isinstance(child, Label):
                child.color = self._title_color
                child.font_name = 'SourceBold'

    def _force_title_color(self, dt):
        try:
            self._color_all_labels(self, self._title_color)
        except Exception as e:
            log_error(f"_force_title_color error: {e}")

    def _color_all_labels(self, widget, color):
        if isinstance(widget, Label):
            widget.color = color
            widget.font_name = 'SourceBold'
        if hasattr(widget, 'children'):
            for child in widget.children:
                self._color_all_labels(child, color)

    def _find_title_box(self, widget):
        if isinstance(widget, BoxLayout):
            for child in widget.children:
                if isinstance(child, Label) and child.text == self.title:
                    return widget
        if hasattr(widget, 'children'):
            for child in widget.children:
                result = self._find_title_box(child)
                if result:
                    return result
        return None

    def _update_popup_bg(self, instance, value):
        if self._popup_bg_rect:
            self._popup_bg_rect.pos = instance.pos
            self._popup_bg_rect.size = instance.size

    def _update_title_bg(self, instance, value):
        if not hasattr(instance, 'canvas'):
            return
        instance.canvas.before.clear()
        with instance.canvas.before:
            Color(*self._title_bg)
            Rectangle(pos=instance.pos, size=instance.size)


class ThemedSpinner(Spinner):
    """Кастомный Spinner с поддержкой тем"""
    dropdown_bg = ColorProperty([0.188, 0.204, 0.251, 1])
    dropdown_text_color = ColorProperty([0.85, 0.88, 0.90, 1])
    dropdown_selected_bg = ColorProperty([0.141, 0.145, 0.149, 1])

    def __init__(self, **kwargs):
        self._dropdown_bg = kwargs.pop('dropdown_bg', self.dropdown_bg)
        self._dropdown_text_color = kwargs.pop('dropdown_text_color', self.dropdown_text_color)
        self._dropdown_selected_bg = kwargs.pop('dropdown_selected_bg', self.dropdown_selected_bg)
        kwargs.setdefault('background_normal', '')
        kwargs.setdefault('background_down', '')
        super().__init__(**kwargs)
        self.dropdown_bg = self._dropdown_bg
        self.dropdown_text_color = self._dropdown_text_color
        self.dropdown_selected_bg = self._dropdown_selected_bg
        self.bind(on_press=self._on_spinner_press)

    def _on_spinner_press(self, instance):
        Clock.schedule_once(lambda dt: self._apply_dropdown_theme(), 0.05)
        Clock.schedule_once(lambda dt: self._apply_dropdown_theme(), 0.1)

    def _update_dropdown(self, *args):
        super()._update_dropdown(*args)
        Clock.schedule_once(lambda dt: self._apply_dropdown_theme(), 0.05)

    def _apply_dropdown_theme(self):
        if not hasattr(self, '_dropdown') or not self._dropdown:
            return
        try:
            dropdown = self._dropdown
            if hasattr(dropdown, 'container'):
                container = dropdown.container
                container.canvas.before.clear()
                with container.canvas.before:
                    Color(*self.dropdown_bg)
                    Rectangle(pos=container.pos, size=container.size)
                container.bind(pos=self._update_container_bg, size=self._update_container_bg)
            self._style_all_buttons(dropdown)
        except Exception as e:
            log_error(f"Spinner theme error: {e}")

    def _update_container_bg(self, instance, value=None):
        if not hasattr(instance, 'canvas'):
            return
        instance.canvas.before.clear()
        with instance.canvas.before:
            Color(*self.dropdown_bg)
            Rectangle(pos=instance.pos, size=instance.size)

    def _style_all_buttons(self, widget):
        if isinstance(widget, Button):
            theme = ThemeManager.get_theme()
            btn_bg = theme.get('action_bar_bg', self.dropdown_bg)
            text_color = theme.get('spinner_dropdown_text', self.dropdown_text_color)
            widget.background_normal = ''
            widget.background_down = ''
            widget.background_color = (0, 0, 0, 0)
            widget.canvas.before.clear()
            with widget.canvas.before:
                Color(*btn_bg)
                Rectangle(pos=widget.pos, size=widget.size)
                Color(btn_bg[0] + 0.08, btn_bg[1] + 0.08, btn_bg[2] + 0.08, 1)
                Line(rectangle=(widget.pos[0], widget.pos[1], widget.size[0], widget.size[1]), width=dp(0.5))
            widget.bind(pos=self._update_btn_bg, size=self._update_btn_bg)
            widget.color = text_color
            widget.font_name = 'SourceBold'
            widget.size_hint_x = 0.94
            widget.pos_hint = {'center_x': 0.5}
        if hasattr(widget, 'children'):
            for child in widget.children:
                self._style_all_buttons(child)

    def _update_btn_bg(self, instance, value=None):
        if not hasattr(instance, 'canvas'):
            return
        theme = ThemeManager.get_theme()
        btn_bg = theme.get('spinner_dropdown_btn_bg', self.dropdown_bg)
        instance.canvas.before.clear()
        with instance.canvas.before:
            Color(*btn_bg)
            Rectangle(pos=instance.pos, size=instance.size)
            Color(btn_bg[0] + 0.08, btn_bg[1] + 0.08, btn_bg[2] + 0.08, 1)
            Line(rectangle=(instance.pos[0], instance.pos[1], instance.size[0], instance.size[1]), width=dp(0.5))


class SettingsManager:
    """Управляет сохранением и загрузкой настроек"""
    @staticmethod
    def get_settings_path():
        settings_dir = os.path.join(os.getcwd(), 'data')
        try:
            os.makedirs(settings_dir, exist_ok=True)
        except:
            pass
        return os.path.join(settings_dir, 'python_ide_settings.json')

    @classmethod
    def load(cls):
        try:
            with open(cls.get_settings_path(), 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}

    @classmethod
    def save(cls, settings_dict):
        try:
            settings_path = cls.get_settings_path()
            os.makedirs(os.path.dirname(settings_path), exist_ok=True)
            with open(settings_path, 'w', encoding='utf-8') as f:
                json.dump(settings_dict, f, indent=2)
            return True
        except Exception as e:
            log_error(f"Error saving settings: {e}")
            return False

    @classmethod
    def get_api_key(cls):
        return cls.load().get('api_key', '')

    @classmethod
    def save_api_key(cls, api_key):
        settings = cls.load()
        settings['api_key'] = api_key
        return cls.save(settings)

    @classmethod
    def get_language(cls):
        return cls.load().get('language', 'en')

    @classmethod
    def save_language(cls, lang):
        settings = cls.load()
        settings['language'] = lang
        return cls.save(settings)

    @classmethod
    def get_theme(cls):
        return cls.load().get('theme', 'dark')

    @classmethod
    def save_theme(cls, theme_name):
        settings = cls.load()
        settings['theme'] = theme_name
        return cls.save(settings)

    @classmethod
    def get_font(cls):
        """
        Возвращает сохранённый шрифт редактора.
        По умолчанию 'JetBrainsMono'.
        """
        settings = cls.load()
        return settings.get('editor_font', 'JetBrainsMono')

    @classmethod
    def save_font(cls, font_key):
        settings = cls.load()
        settings['editor_font'] = font_key
        return cls.save(settings)


class LanguageSelectMenu:
    """Подменю выбора языка"""
    LANGUAGE_NAMES = {
        'ru': 'Русский',
        'en': 'English',
    }

    def __init__(self, app):
        self.app = app
        self._dropdown = None

    def show(self, parent_button):
        theme = ThemeManager.get_theme()
        btn_bg = theme.get('action_bar_bg', theme['widget_bg'])
        self._dropdown = DropDown()
        self._dropdown.auto_width = False
        self._dropdown.width = dp(167)

        def style_container(dropdown, theme):
            if hasattr(dropdown, 'container'):
                container = dropdown.container
                container.canvas.before.clear()
                with container.canvas.before:
                    Color(*theme.get('action_bar_bg', theme['widget_bg']))
                    Rectangle(pos=container.pos, size=container.size)
                container.bind(
                    pos=lambda inst, val: self._update_container_bg(inst, theme),
                    size=lambda inst, val: self._update_container_bg(inst, theme)
                )
        self._dropdown.bind(on_open=lambda *args: style_container(self._dropdown, theme))

        from kivy.uix.behaviors import ButtonBehavior
        class MenuItem(ButtonBehavior, BoxLayout):
            pass

        for lang_code in sorted(TRANSLATIONS.keys()):
            lang_name = self.LANGUAGE_NAMES.get(lang_code, lang_code.upper())
            display_text = f"✓ {lang_name}" if lang_code == self.app.current_language else f"    {lang_name}"
            icon_text = lang_code.upper()
            box = MenuItem(orientation='horizontal', size_hint_y=None, height=dp(30), padding=(dp(8), 0), spacing=dp(5))
            icon_lbl = Label(text=icon_text, color=theme['text_color'], font_size=dp(11), font_name='SourceBold', size_hint_x=None, width=dp(17), halign='center', valign='middle')
            box.add_widget(icon_lbl)
            lbl = Label(text=display_text, color=theme['text_color'], font_size=dp(15), font_name='SourceBold', halign='left', valign='middle')
            box.add_widget(lbl)
            box.canvas.before.clear()
            with box.canvas.before:
                Color(*btn_bg)
                Rectangle(pos=box.pos, size=box.size)
                Color(btn_bg[0] + 0.08, btn_bg[1] + 0.08, btn_bg[2] + 0.08, 1)
                Line(rectangle=(box.pos[0], box.pos[1], box.size[0], box.size[1]), width=dp(0.5))
            box.bind(pos=lambda inst, val, bg=btn_bg: self._update_btn_bg(inst, bg), size=lambda inst, val, bg=btn_bg: self._update_btn_bg(inst, bg))
            box.bind(on_release=lambda instance, code=lang_code: self._on_language_select(code))
            self._dropdown.add_widget(box)

        Clock.schedule_once(lambda dt: self._dropdown.open(parent_button), 0.1)

        def adjust_position(*args):
            win_width, win_height = Window.size
            if self._dropdown and self._dropdown.parent:
                if self._dropdown.x + self._dropdown.width > win_width:
                    self._dropdown.x = win_width - self._dropdown.width - dp(3)
                if self._dropdown.y < 0:
                    self._dropdown.y = parent_button.y + parent_button.height
                elif self._dropdown.y + self._dropdown.height > win_height:
                    self._dropdown.y = parent_button.y - self._dropdown.height
        Clock.schedule_once(adjust_position, 0.15)

    def _on_language_select(self, lang_code):
        if self._dropdown:
            try:
                self._dropdown.dismiss()
            except:
                pass
        if lang_code != self.app.current_language:
            self.app.current_language = lang_code
            self.app.tr = TRANSLATIONS[lang_code]
            self.app._examples_cache = None
            try:
                with open(os.path.join(os.getcwd(), 'language.txt'), 'w') as f:
                    f.write(lang_code)
            except:
                pass
            SettingsManager.save_language(lang_code)
            self.app._update_ui_language()
            self.app.show_result_popup(f"{self.app.tr.get('language', 'Language')}: {self.LANGUAGE_NAMES.get(lang_code, lang_code.upper())}")

    def _update_container_bg(self, instance, theme):
        if not hasattr(instance, 'canvas'):
            return
        instance.canvas.before.clear()
        with instance.canvas.before:
            Color(*theme.get('action_bar_bg', theme['widget_bg']))
            Rectangle(pos=instance.pos, size=instance.size)

    def _update_btn_bg(self, instance, bg_color):
        if not hasattr(instance, 'canvas'):
            return
        instance.canvas.before.clear()
        with instance.canvas.before:
            Color(*bg_color)
            Rectangle(pos=instance.pos, size=instance.size)
            Color(bg_color[0] + 0.08, bg_color[1] + 0.08, bg_color[2] + 0.08, 1)
            Line(rectangle=(instance.pos[0], instance.pos[1], instance.size[0], instance.size[1]), width=dp(0.5))


class ThemeSelectMenu:
    """Подменю выбора темы"""
    def __init__(self, app):
        self.app = app
        self._dropdown = None

    def show(self, parent_button):
        theme = ThemeManager.get_theme()
        btn_bg = theme.get('action_bar_bg', theme['widget_bg'])
        self._dropdown = DropDown()
        self._dropdown.auto_width = False
        self._dropdown.width = dp(167)

        def style_container(dropdown, theme_colors):
            if hasattr(dropdown, 'container'):
                container = dropdown.container
                container.canvas.before.clear()
                with container.canvas.before:
                    Color(*theme_colors.get('action_bar_bg', theme_colors['widget_bg']))
                    Rectangle(pos=container.pos, size=container.size)
                container.bind(
                    pos=lambda inst, val: self._update_container_bg(inst, theme_colors),
                    size=lambda inst, val: self._update_container_bg(inst, theme_colors)
                )
        self._dropdown.bind(on_open=lambda *args: style_container(self._dropdown, theme))

        from kivymd.uix.label import MDIcon
        from kivy.uix.behaviors import ButtonBehavior
        class MenuItem(ButtonBehavior, BoxLayout):
            pass

        available_themes = ThemeManager.get_available_themes()
        current_theme_name = ThemeManager.get_theme_name()
        theme_icons = {'dark': 'weather-night', 'light': 'weather-sunny'}

        for theme_id, theme_title in available_themes.items():
            display_text = f"✓ {theme_title}" if theme_id == current_theme_name else f"    {theme_title}"
            icon_name = theme_icons.get(theme_id, 'circle')
            box = MenuItem(orientation='horizontal', size_hint_y=None, height=dp(30), padding=(dp(8), 0), spacing=dp(5))
            icon = MDIcon(icon=icon_name, font_size=f"{dp(10)}sp", theme_text_color="Custom", text_color=theme['text_color'], size_hint_x=None, width=dp(17))
            box.add_widget(icon)
            lbl = Label(text=display_text, color=theme['text_color'], font_size=dp(15), font_name='SourceBold', halign='left', valign='middle')
            box.add_widget(lbl)
            box.canvas.before.clear()
            with box.canvas.before:
                Color(*btn_bg)
                Rectangle(pos=box.pos, size=box.size)
                Color(btn_bg[0] + 0.08, btn_bg[1] + 0.08, btn_bg[2] + 0.08, 1)
                Line(rectangle=(box.pos[0], box.pos[1], box.size[0], box.size[1]), width=dp(0.5))
            box.bind(pos=lambda inst, val, bg=btn_bg: self._update_btn_bg(inst, bg), size=lambda inst, val, bg=btn_bg: self._update_btn_bg(inst, bg))
            box.bind(on_release=lambda instance, tid=theme_id: self._on_theme_select(tid))
            self._dropdown.add_widget(box)

        Clock.schedule_once(lambda dt: self._dropdown.open(parent_button), 0.1)

        def adjust_position(*args):
            win_width, win_height = Window.size
            if self._dropdown and self._dropdown.parent:
                if self._dropdown.x + self._dropdown.width > win_width:
                    self._dropdown.x = win_width - self._dropdown.width - dp(3)
                if self._dropdown.y < 0:
                    self._dropdown.y = parent_button.y + parent_button.height
                elif self._dropdown.y + self._dropdown.height > win_height:
                    self._dropdown.y = parent_button.y - self._dropdown.height
        Clock.schedule_once(adjust_position, 0.15)

    def _on_theme_select(self, theme_id):
        if self._dropdown:
            try:
                self._dropdown.dismiss()
            except:
                pass
        if theme_id != ThemeManager.get_theme_name():
            success = ThemeManager.switch_theme(theme_id)
            if success:
                new_theme = ThemeManager.get_theme()
                Window.clearcolor = new_theme['window_bg']
                if hasattr(self.app, '_menu_dropdown'):
                    try:
                        self.app._create_menu_items(new_theme)
                    except:
                        pass
                self._show_restart_dialog(theme_id)

    def _show_restart_dialog(self, theme_id):
        tr = self.app.tr
        new_theme = ThemeManager.get_theme()
        available_themes = ThemeManager.get_available_themes()
        theme_title = available_themes.get(theme_id, theme_id)
        content = BoxLayout(orientation='vertical', padding=dp(7), spacing=dp(5))
        message = (
            f"{tr.get('theme_settings', 'Theme')}: {theme_title}\n\n"
            f"{tr.get('restart_for_syntax', 'Restart app to fully apply syntax highlighting?')}\n"
            f"{tr.get('restart_info', 'All tabs will be saved and restored.')}"
        )
        lbl = Label(text=message, font_name='SourceBold', color=new_theme['text_color'], font_size=dp(10), halign='center', valign='middle', size_hint_y=0.7)
        lbl.bind(width=lambda instance, value: setattr(instance, 'text_size', (value, None)))
        content.add_widget(lbl)
        btn_layout = BoxLayout(size_hint_y=0.3, spacing=dp(4))
        popup = ThemedPopup(
            title=tr.get('theme_settings', 'Theme'),
            title_color=new_theme['popup_title'],
            title_bg=new_theme.get('popup_title_bg', new_theme['widget_bg']),
            popup_bg=new_theme.get('popup_bg', new_theme['widget_bg']),
            separator_color=new_theme.get('popup_separator', (0.25, 0.25, 0.25, 1)),
            content=content, size_hint=(0.85, 0.35), auto_dismiss=False
        )
        btn_restart = Button(text=tr.get('restart_btn', 'Restart'), font_name='SourceBold', background_color=(0.2, 0.5, 0.2, 1), background_normal='', background_down='', color=new_theme['text_color'], font_size=dp(9), on_release=lambda x: self._do_restart(popup))
        btn_later = Button(text=tr.get('later_btn', 'Later'), font_name='SourceBold', background_color=new_theme['widget_bg'], background_normal='', background_down='', color=new_theme['text_color'], font_size=dp(9), on_release=lambda x: popup.dismiss())
        btn_layout.add_widget(btn_later)
        btn_layout.add_widget(btn_restart)
        content.add_widget(btn_layout)
        popup.open()

    def _do_restart(self, popup):
        popup.dismiss()
        if hasattr(self.app, 'tab_manager'):
            self.app.tab_manager.save_all_tabs()
        if hasattr(self.app, '_save_autosave'):
            self.app._save_autosave()
        self.app.stop()

    def _update_container_bg(self, instance, theme_colors):
        if not hasattr(instance, 'canvas'):
            return
        instance.canvas.before.clear()
        with instance.canvas.before:
            Color(*theme_colors.get('action_bar_bg', theme_colors['widget_bg']))
            Rectangle(pos=instance.pos, size=instance.size)

    def _update_btn_bg(self, instance, bg_color):
        if not hasattr(instance, 'canvas'):
            return
        instance.canvas.before.clear()
        with instance.canvas.before:
            Color(*bg_color)
            Rectangle(pos=instance.pos, size=instance.size)
            Color(bg_color[0] + 0.08, bg_color[1] + 0.08, bg_color[2] + 0.08, 1)
            Line(rectangle=(instance.pos[0], instance.pos[1], instance.size[0], instance.size[1]), width=dp(0.5))


class EditorSettingsMenu:
    """Подменю настроек редактора"""
    def __init__(self, app):
        self.app = app
        self._dropdown = None
        self._font_menu = FontSelectMenu(app)

    def show(self, parent_button):
        theme = ThemeManager.get_theme()
        btn_bg = theme.get('action_bar_bg', theme['widget_bg'])
        self._dropdown = DropDown()
        self._dropdown.auto_width = False
        self._dropdown.width = dp(167)

        def style_container(dropdown, theme_colors):
            if hasattr(dropdown, 'container'):
                container = dropdown.container
                container.canvas.before.clear()
                with container.canvas.before:
                    Color(*theme_colors.get('action_bar_bg', theme_colors['widget_bg']))
                    Rectangle(pos=container.pos, size=container.size)
                container.bind(
                    pos=lambda inst, val: self._update_container_bg(inst, theme_colors),
                    size=lambda inst, val: self._update_container_bg(inst, theme_colors)
                )
        self._dropdown.bind(on_open=lambda *args: style_container(self._dropdown, theme))

        from kivymd.uix.label import MDIcon
        from kivy.uix.behaviors import ButtonBehavior
        class MenuItem(ButtonBehavior, BoxLayout):
            pass

        menu_items = [
            ('format-font', self.app.tr.get('editor_font', 'Шрифт'), lambda: self._open_font_submenu(parent_button)),
        ]

        for icon_name, text, handler in menu_items:
            box = MenuItem(orientation='horizontal', size_hint_y=None, height=dp(30), padding=(dp(8), 0), spacing=dp(5))
            icon = MDIcon(icon=icon_name, font_size=f"{dp(10)}sp", theme_text_color="Custom", text_color=theme['text_color'], size_hint_x=None, width=dp(17))
            box.add_widget(icon)
            lbl = Label(text=text, color=theme['text_color'], font_size=dp(15), font_name='SourceBold', halign='left', valign='middle')
            box.add_widget(lbl)
            box.canvas.before.clear()
            with box.canvas.before:
                Color(*btn_bg)
                Rectangle(pos=box.pos, size=box.size)
                Color(btn_bg[0] + 0.08, btn_bg[1] + 0.08, btn_bg[2] + 0.08, 1)
                Line(rectangle=(box.pos[0], box.pos[1], box.size[0], box.size[1]), width=dp(0.5))
            box.bind(pos=lambda inst, val, bg=btn_bg: self._update_btn_bg(inst, bg), size=lambda inst, val, bg=btn_bg: self._update_btn_bg(inst, bg))
            box.bind(on_release=lambda instance, h=handler: self._on_item_click(h))
            self._dropdown.add_widget(box)

        Clock.schedule_once(lambda dt: self._dropdown.open(parent_button), 0.1)

        def adjust_position(*args):
            win_width, win_height = Window.size
            if self._dropdown and self._dropdown.parent:
                if self._dropdown.x + self._dropdown.width > win_width:
                    self._dropdown.x = win_width - self._dropdown.width - dp(3)
                if self._dropdown.y < 0:
                    self._dropdown.y = parent_button.y + parent_button.height
                elif self._dropdown.y + self._dropdown.height > win_height:
                    self._dropdown.y = parent_button.y - self._dropdown.height
        Clock.schedule_once(adjust_position, 0.15)

    def _on_item_click(self, handler):
        if self._dropdown:
            try:
                self._dropdown.dismiss()
            except:
                pass
        handler()

    def _open_font_submenu(self, parent_button):
        self._font_menu.show(parent_button)

    def _update_container_bg(self, instance, theme_colors):
        if not hasattr(instance, 'canvas'):
            return
        instance.canvas.before.clear()
        with instance.canvas.before:
            Color(*theme_colors.get('action_bar_bg', theme_colors['widget_bg']))
            Rectangle(pos=instance.pos, size=instance.size)

    def _update_btn_bg(self, instance, bg_color):
        if not hasattr(instance, 'canvas'):
            return
        instance.canvas.before.clear()
        with instance.canvas.before:
            Color(*bg_color)
            Rectangle(pos=instance.pos, size=instance.size)
            Color(bg_color[0] + 0.08, bg_color[1] + 0.08, bg_color[2] + 0.08, 1)
            Line(rectangle=(instance.pos[0], instance.pos[1], instance.size[0], instance.size[1]), width=dp(0.5))


class FontSelectMenu:
    """
    Подменю для выбора шрифта редактора кода.
    """

    FONT_NAMES = {
        'JetBrainsMono': 'JetBrains Mono',
        'FiraCode': 'Fira Code',
        'CascadiaCode': 'Cascadia Code',
        'IBMPlexMono': 'IBM Plex Mono',
        'NotoSansMono': 'Noto Sans Mono',
        'SourceCodePro': 'Source Code Pro',
        'DroidMono': 'Droid Sans Mono',
    }

    FONT_ICONS = {
        'JetBrainsMono': 'language-python',
        'FiraCode': 'code-braces',
        'CascadiaCode': 'code-tags',
        'IBMPlexMono': 'code-parentheses',
        'NotoSansMono': 'format-font',
        'SourceCodePro': 'code-json',
        'DroidMono': 'android',
    }

    FONT_FILES = {
        'JetBrainsMono': 'JetBrainsMono',
        'FiraCode': 'FiraCode',
        'CascadiaCode': 'CascadiaCode',
        'IBMPlexMono': 'IBMPlexMono',
        'NotoSansMono': 'NotoSansMono',
        'SourceCodePro': 'SourceCodePro',
        'DroidMono': 'DroidMono',
    }

    def __init__(self, app):
        self.app = app
        self._dropdown = None

    def show(self, parent_button):
        theme = ThemeManager.get_theme()
        tr = self.app.tr

        self._dropdown = DropDown()
        self._dropdown.auto_width = False
        self._dropdown.width = dp(167)

        def style_container(dropdown, theme):
            if hasattr(dropdown, 'container'):
                container = dropdown.container
                container.canvas.before.clear()
                with container.canvas.before:
                    Color(*theme.get('action_bar_bg', theme['widget_bg']))
                    Rectangle(pos=container.pos, size=container.size)
                container.bind(
                    pos=lambda inst, val: self._update_container_bg(inst, theme),
                    size=lambda inst, val: self._update_container_bg(inst, theme)
                )

        self._dropdown.bind(
            on_open=lambda *args: style_container(self._dropdown, theme))

        current_font = SettingsManager.get_font()
        btn_bg = theme.get('action_bar_bg', theme['widget_bg'])

        font_order = ['JetBrainsMono', 'FiraCode', 'CascadiaCode', 'IBMPlexMono', 'NotoSansMono', 'SourceCodePro', 'DroidMono']

        for font_key in font_order:
            font_name = self.FONT_NAMES.get(font_key, font_key)
            icon_name = self.FONT_ICONS.get(font_key, 'circle')

            if font_key == current_font:
                display_text = f"✓ {font_name}"
            else:
                display_text = f"    {font_name}"

            from kivymd.uix.label import MDIcon
            from kivy.uix.behaviors import ButtonBehavior

            class MenuItem(ButtonBehavior, BoxLayout):
                pass

            box = MenuItem(
                orientation='horizontal',
                size_hint_y=None,
                height=dp(30),
                padding=(dp(8), 0),
                spacing=dp(5),
            )

            icon = MDIcon(
                icon=icon_name,
                font_size=f"{dp(10)}sp",
                theme_text_color="Custom",
                text_color=theme['text_color'],
                size_hint_x=None,
                width=dp(17),
            )
            box.add_widget(icon)

            lbl = Label(
                text=display_text,
                color=theme['text_color'],
                font_size=dp(15),
                font_name='SourceBold',
                halign='left',
                valign='middle',
            )
            box.add_widget(lbl)

            box.canvas.before.clear()
            with box.canvas.before:
                Color(*btn_bg)
                Rectangle(pos=box.pos, size=box.size)
                Color(btn_bg[0] + 0.08, btn_bg[1] + 0.08, btn_bg[2] + 0.08, 1)
                Line(rectangle=(box.pos[0], box.pos[1],
                     box.size[0], box.size[1]), width=dp(0.5))

            box.bind(
                pos=lambda inst, val, bg=btn_bg: self._update_btn_bg(inst, bg),
                size=lambda inst, val, bg=btn_bg: self._update_btn_bg(inst, bg)
            )

            box.bind(on_release=lambda instance,
                     fk=font_key: self._on_font_select(fk))
            self._dropdown.add_widget(box)

        Clock.schedule_once(lambda dt: self._dropdown.open(parent_button), 0.1)

        def adjust_position(*args):
            win_width, win_height = Window.size
            if self._dropdown and self._dropdown.parent:
                if self._dropdown.x + self._dropdown.width > win_width:
                    self._dropdown.x = win_width - self._dropdown.width - dp(3)
                if self._dropdown.y < 0:
                    self._dropdown.y = parent_button.y + parent_button.height
                elif self._dropdown.y + self._dropdown.height > win_height:
                    self._dropdown.y = parent_button.y - self._dropdown.height

        Clock.schedule_once(adjust_position, 0.15)

    def _on_font_select(self, font_key):
        if self._dropdown:
            try:
                self._dropdown.dismiss()
            except:
                pass

        if font_key != SettingsManager.get_font():
            SettingsManager.save_font(font_key)
            self._apply_font(font_key)
            font_name = self.FONT_NAMES.get(font_key, font_key)
            self.app.show_result_popup(f"✓ Шрифт: {font_name}")

    def _apply_font(self, font_key):
        font_file = self.FONT_FILES.get(font_key, 'DroidMono')

        if not hasattr(self.app, 'tab_manager'):
            return

        for tab in self.app.tab_manager.tabs:
            editor = tab.get('editor')
            if editor and hasattr(editor, 'text_input'):
                editor.text_input.font_name = font_file
                if hasattr(editor, 'force_full_font_reset'):
                    Clock.schedule_once(editor.force_full_font_reset, 0.15)

        SettingsManager.save_font(font_key)
        self.app.show_result_popup(
            f"✓ Шрифт изменён: {self.FONT_NAMES.get(font_key, font_key)}")

    def _update_container_bg(self, instance, theme):
        if not hasattr(instance, 'canvas'):
            return
        instance.canvas.before.clear()
        with instance.canvas.before:
            Color(*theme.get('action_bar_bg', theme['widget_bg']))
            Rectangle(pos=instance.pos, size=instance.size)

    def _update_btn_bg(self, instance, bg_color):
        if not hasattr(instance, 'canvas'):
            return
        instance.canvas.before.clear()
        with instance.canvas.before:
            Color(*bg_color)
            Rectangle(pos=instance.pos, size=instance.size)
            Color(bg_color[0] + 0.08, bg_color[1] +
                  0.08, bg_color[2] + 0.08, 1)
            Line(rectangle=(instance.pos[0], instance.pos[1],
                 instance.size[0], instance.size[1]), width=dp(0.5))


class SyntaxStyleManager:
    """Управляет стилями подсветки синтаксиса"""
    KNOWN_STYLES = [
        'monokai', 'dracula', 'github-dark', 'one-dark',
        'native', 'material', 'xcode', 'xcode-dark',
        'friendly', 'github', 'autumn', 'borland',
        'trac', 'colorful', 'vs', 'sas',
        'stata-dark', 'arduino', 'rainbow_dash',
    ]

    @classmethod
    def get_available_styles(cls):
        if not HAS_PYGMENTS:
            return ['default']
        try:
            from pygments.styles import get_all_styles
            all_styles = list(get_all_styles())
            available = [s for s in cls.KNOWN_STYLES if s in all_styles]
            if not available:
                available = sorted(all_styles)
            return sorted(list(set(available)))
        except:
            return ['default', 'monokai', 'dracula']

    @classmethod
    def get_style_display_info(cls):
        style_info = {
            'monokai': {'name': 'Monokai', 'type': 'dark'},
            'dracula': {'name': 'Dracula', 'type': 'dark'},
            'github-dark': {'name': 'GitHub Dark', 'type': 'dark'},
            'one-dark': {'name': 'One Dark', 'type': 'dark'},
            'native': {'name': 'Native', 'type': 'dark'},
            'material': {'name': 'Material', 'type': 'dark'},
            'xcode-dark': {'name': 'Xcode Dark', 'type': 'dark'},
            'stata-dark': {'name': 'Stata Dark', 'type': 'dark'},
            'rainbow_dash': {'name': 'Rainbow Dash', 'type': 'dark'},
            'xcode': {'name': 'Xcode', 'type': 'light'},
            'friendly': {'name': 'Friendly', 'type': 'light'},
            'github': {'name': 'GitHub', 'type': 'light'},
            'autumn': {'name': 'Autumn', 'type': 'light'},
            'borland': {'name': 'Borland', 'type': 'light'},
            'trac': {'name': 'Trac', 'type': 'light'},
            'colorful': {'name': 'Colorful', 'type': 'light'},
            'vs': {'name': 'Visual Studio', 'type': 'light'},
            'sas': {'name': 'SAS', 'type': 'light'},
            'arduino': {'name': 'Arduino', 'type': 'light'},
        }
        available = cls.get_available_styles()
        result = {}
        for style in available:
            if style in style_info:
                result[style] = style_info[style]
            else:
                result[style] = {'name': style.replace('_', ' ').title(), 'type': 'unknown'}
        return result

    @classmethod
    def get_current_style(cls):
        try:
            settings_path = cls._get_settings_path()
            if os.path.exists(settings_path):
                with open(settings_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    style = settings.get('syntax_style', None)
                    if style and style in cls.get_available_styles():
                        return style
        except:
            pass
        return 'monokai'

    @classmethod
    def save_current_style(cls, style_name):
        try:
            settings_path = cls._get_settings_path()
            settings = {}
            if os.path.exists(settings_path):
                try:
                    with open(settings_path, 'r', encoding='utf-8') as f:
                        settings = json.load(f)
                except:
                    settings = {}
            settings['syntax_style'] = style_name
            os.makedirs(os.path.dirname(settings_path), exist_ok=True)
            with open(settings_path, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2)
            return True
        except:
            return False

    @classmethod
    def apply_style_to_all_tabs(cls, tab_manager, style_name):
        if not tab_manager or not hasattr(tab_manager, 'tabs'):
            return 0
        return len(tab_manager.tabs)

    @classmethod
    def _get_settings_path(cls):
        settings_dir = os.path.join(os.getcwd(), 'data')
        return os.path.join(settings_dir, 'python_ide_settings.json')


class SyntaxHighlightMenu:
    """Меню выбора стиля подсветки"""
    def __init__(self, app):
        self.app = app
        self._popup = None
        self._preview_popup = None
        self._preview_bg_rect = None
        self._current_menu_button = None

    def show(self, parent_button):
        self._current_menu_button = parent_button
        self._destroy_all_windows()
        theme = ThemeManager.get_theme()  # ← НАПРЯМУЮ
        tr = self._get_translations()
        styles = SyntaxStyleManager.get_available_styles()
        style_info = SyntaxStyleManager.get_style_display_info()
        current_style = SyntaxStyleManager.get_current_style()
    
        content = BoxLayout(orientation='vertical', padding=dp(5), spacing=dp(3))
        header_text = tr.get('syntax_header', 'Выберите стиль подсветки:')
        content.add_widget(Label(text=header_text, size_hint_y=None, height=dp(30), color=theme.get('text_color', (0, 0, 0, 1)), font_size=dp(17), halign='left', valign='middle'))
    
        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False, do_scroll_y=True)
        styles_list = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(1.5), padding=[0, dp(2)])
        styles_list.bind(minimum_height=styles_list.setter('height'))
    
        from kivymd.uix.label import MDIcon
        from kivy.uix.behaviors import ButtonBehavior
        btn_bg = theme.get('popup_bg', (1.0, 1.0, 1.0, 1))  # ← фон как у попапа
    
        for style_name in styles:
            info = style_info.get(style_name, {'name': style_name.replace('_', ' ').title(), 'type': 'unknown'})
            prefix = '✓ ' if style_name == current_style else '  '
            display_name = f"{prefix}{info['name']}"
    
            class MenuItem(ButtonBehavior, BoxLayout):
                pass
    
            box = MenuItem(orientation='horizontal', size_hint_y=None, height=dp(30), padding=(dp(8), 0), spacing=dp(4))
            icon = MDIcon(icon='weather-night' if info['type'] == 'dark' else 'weather-sunny', font_size=f"{dp(7)}sp", theme_text_color="Custom", text_color=theme.get('text_color', (0, 0, 0, 1)), size_hint_x=None, width=dp(13))
            box.add_widget(icon)
            lbl = Label(text=display_name, color=theme.get('text_color', (0, 0, 0, 1)), font_size=dp(15), font_name='SourceBold', halign='left', valign='middle')
            box.add_widget(lbl)
            box.canvas.before.clear()
            with box.canvas.before:
                Color(*btn_bg)
                Rectangle(pos=box.pos, size=box.size)
                Color(btn_bg[0] + 0.05, btn_bg[1] + 0.05, btn_bg[2] + 0.05, 1)
                Line(rectangle=(box.pos[0], box.pos[1], box.size[0], box.size[1]), width=dp(0.3))
            box.bind(pos=lambda inst, val, bg=btn_bg: self._update_btn_bg(inst, bg), size=lambda inst, val, bg=btn_bg: self._update_btn_bg(inst, bg))
            box.bind(on_release=lambda instance, sn=style_name: self._open_preview_after_close(sn))
            styles_list.add_widget(box)
    
        scroll.add_widget(styles_list)
        content.add_widget(scroll)
    
        close_text = tr.get('close', 'Закрыть')
        btn_close = Button(text=close_text, size_hint_y=None, height=dp(40), background_color=theme.get('widget_bg', (0.843, 0.816, 1.0, 1)), background_normal='', background_down='', color=theme.get('text_color', (0, 0, 0, 1)), font_size=dp(13), on_release=lambda x: self._destroy_all_windows())
        content.add_widget(btn_close)
    
        title = tr.get('syntax_menu_title', 'Стиль подсветки')
        self._popup = Popup(
            title=title,
            title_color=theme.get('popup_title', (0, 0, 0, 1)),
            separator_color=theme.get('popup_separator', (0.25, 0.25, 0.25, 1)),
            background='',
            background_color=theme.get('popup_bg', (1.0, 1.0, 1.0, 1)),
            content=content,
            size_hint=(0.92, 0.85),
            auto_dismiss=False
        )
        self._popup.open()

    def _open_preview_after_close(self, style_name):
        self._close_menu()
        Clock.schedule_once(lambda dt: self._open_preview(style_name), 0.3)

    def _open_preview(self, style_name):
        self._close_preview()
        theme = ThemeManager.get_theme()  # ← НАПРЯМУЮ из ThemeManager
        tr = self._get_translations()
        info = SyntaxStyleManager.get_style_display_info()
        style_info = info.get(style_name, {'name': style_name.replace('_', ' ').title(), 'type': 'unknown'})
    
        demo_code = f'''# Предпросмотр: {style_info['name']}
    def fibonacci(n):
        """Вычисляет числа Фибоначчи"""
        if n <= 1:
            return n
        a, b = 0, 1
        for _ in range(n - 1):
            a, b = b, a + b
        return b
    
    class Calculator:
        def __init__(self, name="Calc"):
            self.name = name
            self._value = 0
        def add(self, x):
            self._value += x
            return self._value
    
    calc = Calculator("Калькулятор")
    result = calc.add(10)
    print(f"{{calc.name}}: {{result}}")
    print(f"Fib(10) = {{fibonacci(10)}}")
    items = ["хлеб", "молоко", "яйца"]
    for item in items:
        print(f"- {{item}}")
    '''
        highlighted_text = self._highlight_code(demo_code, style_name, theme)
        content = BoxLayout(orientation='vertical', padding=dp(5), spacing=dp(3))
    
        from kivymd.uix.label import MDIcon
        header_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(20), spacing=dp(3))
        icon = MDIcon(icon='weather-night' if style_info['type'] == 'dark' else 'weather-sunny', font_size=f"{dp(11)}sp", theme_text_color="Custom", text_color=theme.get('text_color', (0.85, 0.88, 0.90, 1)), size_hint_x=None, width=dp(20))
        header_box.add_widget(icon)
        type_str = 'Тёмный стиль' if style_info['type'] == 'dark' else 'Светлый стиль'
        header_lbl = Label(text=f"[b]{style_info['name']}[/b] — {type_str}", markup=True, color=theme.get('text_color', (0.85, 0.88, 0.90, 1)), font_size=dp(13), font_name='SourceBold', halign='left', valign='middle')
        header_box.add_widget(header_lbl)
        content.add_widget(header_box)
    
        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False, do_scroll_y=True)
        
        # Обёртка с фоном редактора
        editor_bg_color = theme.get('editor_bg', (1.0, 1.0, 1.0, 1))
        preview_box = FloatLayout(size_hint=(1, None))
        with preview_box.canvas.before:
            Color(*editor_bg_color)
            self._preview_bg_rect = Rectangle(pos=preview_box.pos, size=preview_box.size)
        preview_box.bind(pos=self._update_preview_bg, size=self._update_preview_bg)
        
        preview_label = Label(
            text=highlighted_text,
            markup=True,
            font_size=dp(13),
            font_name='DejaVuSans',
            color=theme.get('editor_text', (0, 0, 0, 1)),
            size_hint=(1, None),
            padding=(dp(5), dp(5)),
            halign='left',
            valign='top',
            text_size=(None, None)
        )
        preview_label.bind(texture_size=lambda instance, value: setattr(instance, 'height', value[1] + dp(10)))
        preview_label.bind(texture_size=lambda instance, value: setattr(preview_box, 'height', value[1] + dp(10)))
        
        preview_box.add_widget(preview_label)
        scroll.add_widget(preview_box)
        content.add_widget(scroll)
    
        btn_layout = BoxLayout(size_hint_y=None, height=dp(33), spacing=dp(4))
        apply_text = tr.get('apply', 'Применить')
        cancel_text = tr.get('cancel', 'Отмена')
        back_text = tr.get('back', '← Назад')
        btn_back = Button(text=back_text, background_color=theme.get('widget_bg', (0.14, 0.14, 0.15, 1)), background_normal='', background_down='', color=theme.get('text_color', (0, 0, 0, 1)), font_size=dp(13), on_release=lambda x: self._back_to_menu())
        btn_cancel = Button(text=cancel_text, background_color=theme.get('widget_bg', (0.14, 0.14, 0.15, 1)), background_normal='', background_down='', color=theme.get('text_color', (0, 0, 0, 1)), font_size=dp(13), on_release=lambda x: self._destroy_all_windows())
        btn_apply = Button(text=apply_text, background_color=theme.get('btn_success_bg', (0.2, 0.5, 0.2, 1)), background_normal='', background_down='', color=(1, 1, 1, 1), font_size=dp(13), on_release=lambda x: self._apply_style(style_name))
        btn_layout.add_widget(btn_back)
        btn_layout.add_widget(btn_cancel)
        btn_layout.add_widget(btn_apply)
        content.add_widget(btn_layout)
    
        title = tr.get('syntax_preview', 'Предпросмотр: ') + style_info['name']
        
        popup_bg_color = theme.get('editor_bg', (1.0, 1.0, 1.0, 1))
        self._preview_popup = Popup(
            title=title,
            title_color=theme.get('popup_title', (0, 0, 0, 1)),
            separator_color=theme.get('popup_separator', (0.25, 0.25, 0.25, 1)),
            background='',
            background_color=popup_bg_color,
            content=content,
            size_hint=(0.95, 0.88),
            auto_dismiss=False
        )
        self._preview_popup.open()

    def _update_preview_bg(self, instance, value):
        if hasattr(self, '_preview_bg_rect') and self._preview_bg_rect:
            self._preview_bg_rect.pos = instance.pos
            self._preview_bg_rect.size = instance.size

    def _highlight_code(self, code, style_name, theme):
        try:
            from pygments.lexers import PythonLexer as PL
            from pygments.styles import get_style_by_name as gsbn
            try:
                style = gsbn(style_name)
            except:
                style = gsbn('monokai')
            lexer = PL()
            tokens = list(lexer.get_tokens(code))
            result = []
            for token_type, text in tokens:
                if text == '':
                    continue
                text = text.replace('[', '&bl;').replace(']', '&br;')
                try:
                    style_info = style.style_for_token(token_type)
                    if style_info.get('color'):
                        result.append(f"[color=#{style_info['color']}]{text}[/color]")
                    elif style_info.get('bold'):
                        result.append(f'[b]{text}[/b]')
                    elif style_info.get('italic'):
                        result.append(f'[i]{text}[/i]')
                    else:
                        result.append(text)
                except:
                    result.append(text)
            return ''.join(result)
        except:
            return code.replace('[', '&bl;').replace(']', '&br;')

    def _apply_style(self, style_name):
        self._destroy_all_windows()
        SyntaxStyleManager.save_current_style(style_name)
        if hasattr(self.app, 'tab_manager'):
            self.app.tab_manager.save_all_tabs()
        if hasattr(self.app, '_save_autosave'):
            self.app._save_autosave()
        info = SyntaxStyleManager.get_style_display_info()
        style_display = info.get(style_name, {}).get('name', style_name)
        self._show_restart_dialog(style_display)

    def _show_restart_dialog(self, style_display):
        tr = self._get_translations()
        theme = ThemeManager.get_theme()  # ← НАПРЯМУЮ
        content = BoxLayout(orientation='vertical', padding=dp(7), spacing=dp(5))
        message = (
            f"{tr.get('syntax_highlight', 'Подсветка')}: {style_display}\n\n"
            f"{tr.get('restart_for_syntax', 'Перезапустить приложение для полной смены подсветки синтаксиса?')}\n"
            f"{tr.get('restart_info', 'Все вкладки будут сохранены и восстановлены.')}"
        )
        lbl = Label(text=message, font_name='SourceBold', color=theme.get('text_color', (0, 0, 0, 1)), font_size=dp(10), halign='center', valign='middle', size_hint_y=0.7)
        lbl.bind(width=lambda instance, value: setattr(instance, 'text_size', (value, None)))
        content.add_widget(lbl)
        btn_layout = BoxLayout(size_hint_y=0.3, spacing=dp(4))
        popup = Popup(
            title=tr.get('syntax_menu_title', 'Стиль подсветки'),
            title_color=theme.get('popup_title', (0, 0, 0, 1)),
            separator_color=theme.get('popup_separator', (0.25, 0.25, 0.25, 1)),
            background='',
            background_color=theme.get('popup_bg', (1.0, 1.0, 1.0, 1)),
            content=content,
            size_hint=(0.85, 0.35),
            auto_dismiss=False
        )
        btn_restart = Button(text=tr.get('restart_btn', 'Перезапустить'), font_name='SourceBold', background_color=theme.get('btn_success_bg', (0.2, 0.5, 0.2, 1)), background_normal='', background_down='', color=(1, 1, 1, 1), font_size=dp(9), on_release=lambda x: self._do_restart(popup))
        btn_later = Button(text=tr.get('later_btn', 'Позже'), font_name='SourceBold', background_color=theme.get('widget_bg', (0.843, 0.816, 1.0, 1)), background_normal='', background_down='', color=theme.get('text_color', (0, 0, 0, 1)), font_size=dp(9), on_release=lambda x: popup.dismiss())
        btn_layout.add_widget(btn_later)
        btn_layout.add_widget(btn_restart)
        content.add_widget(btn_layout)
        popup.open()

    def _do_restart(self, popup):
        popup.dismiss()
        if hasattr(self.app, 'tab_manager'):
            self.app.tab_manager.save_all_tabs()
        if hasattr(self.app, '_save_autosave'):
            self.app._save_autosave()
        if hasattr(self.app, 'stop'):
            self.app.stop()

    def _back_to_menu(self):
        self._close_preview()
        if self._current_menu_button:
            self.show(self._current_menu_button)
        elif hasattr(self.app, 'menu_button'):
            self.show(self.app.menu_button)

    def _close_menu(self):
        if self._popup:
            try:
                self._popup.dismiss()
            except:
                pass
            self._popup = None

    def _close_preview(self):
        if self._preview_popup:
            try:
                self._preview_popup.dismiss()
            except:
                pass
            self._preview_popup = None

    def _destroy_all_windows(self):
        self._close_menu()
        self._close_preview()
        gc.collect()

    def _get_theme(self):
        try:
            if hasattr(self.app, 'get_theme'):
                return ThemeManager.get_theme()
        except:
            pass
        return {'widget_bg': (0.141, 0.145, 0.149, 1), 'text_color': (0.85, 0.88, 0.90, 1), 'editor_bg': (0.188, 0.204, 0.251, 1), 'editor_text': (0.95, 0.95, 0.95, 1), 'popup_title': (0.85, 0.88, 0.90, 1), 'popup_separator': (0.25, 0.25, 0.25, 1), 'popup_bg': (0.188, 0.204, 0.251, 1), 'btn_success_bg': (0.2, 0.5, 0.2, 1)}

    def _get_translations(self):
        if hasattr(self.app, 'tr'):
            return self.app.tr
        return {}

    def _update_btn_bg(self, instance, bg_color):
        if not hasattr(instance, 'canvas'):
            return
        instance.canvas.before.clear()
        with instance.canvas.before:
            Color(*bg_color)
            Rectangle(pos=instance.pos, size=instance.size)
            Color(bg_color[0] + 0.05, bg_color[1] + 0.05, bg_color[2] + 0.05, 1)
            Line(rectangle=(instance.pos[0], instance.pos[1], instance.size[0], instance.size[1]), width=dp(0.3))


class SettingsMenu:
    """Выпадающее меню настроек"""
    def __init__(self, app):
        self.app = app
        self._dropdown = None
        self._language_menu = LanguageSelectMenu(app)
        self._theme_menu = ThemeSelectMenu(app)
        self._editor_menu = EditorSettingsMenu(app)

    def show(self, parent_button):
        if hasattr(self.app, '_menu_dropdown') and self.app._menu_dropdown:
            try:
                self.app._menu_dropdown.dismiss()
            except:
                pass
        theme = ThemeManager.get_theme()
        btn_bg = theme.get('action_bar_bg', theme['widget_bg'])
        self._dropdown = DropDown()
        self._dropdown.auto_width = False
        self._dropdown.width = dp(167)

        def style_container(dropdown, theme_colors):
            if hasattr(dropdown, 'container'):
                container = dropdown.container
                container.canvas.before.clear()
                with container.canvas.before:
                    Color(*theme_colors.get('action_bar_bg', theme_colors['widget_bg']))
                    Rectangle(pos=container.pos, size=container.size)
                container.bind(
                    pos=lambda inst, val: self._update_container_bg(inst, theme_colors),
                    size=lambda inst, val: self._update_container_bg(inst, theme_colors)
                )
        self._dropdown.bind(on_open=lambda *args: style_container(self._dropdown, theme))

        from kivymd.uix.label import MDIcon
        from kivy.uix.behaviors import ButtonBehavior
        class MenuItem(ButtonBehavior, BoxLayout):
            pass

        menu_items = [
            ('translate', 'select_language', lambda: self._open_language_submenu(parent_button)),
            ('theme-light-dark', 'theme_settings', lambda: self._open_theme_submenu(parent_button)),
            ('palette', 'syntax_highlight', lambda: self._open_syntax_submenu(parent_button)),
            ('key', 'api_settings', lambda: self._open_api_settings()),
            ('tune', 'editor_settings', lambda: self._open_editor_submenu(parent_button)),
        ]

        for icon_name, item_key, handler in menu_items:
            box = MenuItem(orientation='horizontal', size_hint_y=None, height=dp(30), padding=(dp(8), 0), spacing=dp(5))
            icon = MDIcon(icon=icon_name, font_size=f"{dp(10)}sp", theme_text_color="Custom", text_color=theme['text_color'], size_hint_x=None, width=dp(17))
            box.add_widget(icon)
            lbl = Label(text=self.app.tr.get(item_key, item_key), color=theme['text_color'], font_size=dp(15), font_name='SourceBold', halign='left', valign='middle')
            box.add_widget(lbl)
            box.canvas.before.clear()
            with box.canvas.before:
                Color(*btn_bg)
                Rectangle(pos=box.pos, size=box.size)
                Color(btn_bg[0] + 0.08, btn_bg[1] + 0.08, btn_bg[2] + 0.08, 1)
                Line(rectangle=(box.pos[0], box.pos[1], box.size[0], box.size[1]), width=dp(0.5))
            box.bind(pos=lambda inst, val, bg=btn_bg: self._update_btn_bg(inst, bg), size=lambda inst, val, bg=btn_bg: self._update_btn_bg(inst, bg))
            box.bind(on_release=lambda instance, h=handler: self._on_item_click(h))
            self._dropdown.add_widget(box)

        Clock.schedule_once(lambda dt: self._dropdown.open(parent_button), 0.1)

        def adjust_position(*args):
            win_width, win_height = Window.size
            if self._dropdown and self._dropdown.parent:
                if self._dropdown.x + self._dropdown.width > win_width:
                    self._dropdown.x = win_width - self._dropdown.width - dp(3)
                if self._dropdown.y < 0:
                    self._dropdown.y = parent_button.y + parent_button.height
                elif self._dropdown.y + self._dropdown.height > win_height:
                    self._dropdown.y = parent_button.y - self._dropdown.height
        Clock.schedule_once(adjust_position, 0.15)

    def _on_item_click(self, handler):
        if self._dropdown:
            try:
                self._dropdown.dismiss()
            except:
                pass
        handler()

    def _open_language_submenu(self, parent_button):
        self._language_menu.show(parent_button)

    def _open_theme_submenu(self, parent_button):
        self._theme_menu.show(parent_button)

    def _open_syntax_submenu(self, parent_button):
        if not hasattr(self, '_syntax_menu'):
            self._syntax_menu = SyntaxHighlightMenu(self.app)
        self._syntax_menu.show(parent_button)

    def _open_editor_submenu(self, parent_button):
        self._editor_menu.show(parent_button)

    def _open_api_settings(self):
        self.app.show_api_key_settings()

    def _update_container_bg(self, instance, theme_colors):
        if not hasattr(instance, 'canvas'):
            return
        instance.canvas.before.clear()
        with instance.canvas.before:
            Color(*theme_colors.get('action_bar_bg', theme_colors['widget_bg']))
            Rectangle(pos=instance.pos, size=instance.size)

    def _update_btn_bg(self, instance, bg_color):
        if not hasattr(instance, 'canvas'):
            return
        instance.canvas.before.clear()
        with instance.canvas.before:
            Color(*bg_color)
            Rectangle(pos=instance.pos, size=instance.size)
            Color(bg_color[0] + 0.08, bg_color[1] + 0.08, bg_color[2] + 0.08, 1)
            Line(rectangle=(instance.pos[0], instance.pos[1], instance.size[0], instance.size[1]), width=dp(0.5))


class ThemeManager:
    """Управляет цветовой темой приложения"""
    _instance = None
    _current_theme = DARK_THEME
    _observers = []
    _themes = {
        'dark': DARK_THEME,
        'light': LIGHT_THEME,
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_theme(cls):
        return cls._current_theme

    @classmethod
    def get_theme_name(cls):
        return cls._current_theme.get('name', 'dark')

    @classmethod
    def get_available_themes(cls):
        try:
            app = App.get_running_app()
            tr = app.tr if app else TRANSLATIONS['ru']
        except:
            tr = TRANSLATIONS['ru']
        return {
            'dark': tr.get('theme_dark', 'Тёмная'),
            'light': tr.get('theme_light', 'Светлая'),
        }

    @classmethod
    def get_syntax_style(cls):
        try:
            saved_style = SyntaxStyleManager.get_current_style()
            if saved_style:
                return saved_style
        except:
            pass
        return cls._current_theme.get('syntax_style', 'monokai')

    @classmethod
    def set_theme(cls, theme_dict):
        cls._current_theme = theme_dict
        for widget in cls._observers:
            if hasattr(widget, 'apply_theme'):
                try:
                    widget.apply_theme(theme_dict)
                except Exception as e:
                    log_error(f"ThemeManager: error applying theme to {widget}: {e}")

    @classmethod
    def switch_theme(cls, theme_name):
        if theme_name in cls._themes:
            cls.set_theme(cls._themes[theme_name])
            SettingsManager.save_theme(theme_name)
            return True
        return False

    @classmethod
    def apply_saved_theme(cls):
        saved_theme = SettingsManager.get_theme()
        if saved_theme in cls._themes:
            cls._current_theme = cls._themes[saved_theme]
        else:
            cls._current_theme = DARK_THEME

    @classmethod
    def register(cls, widget):
        if widget not in cls._observers:
            cls._observers.append(widget)

    @classmethod
    def unregister(cls, widget):
        if widget in cls._observers:
            cls._observers.remove(widget)


class CodeExecutor:
    """Выполняет Python-код"""
    def __init__(self):
        self.is_running = False
        self._input_queue = []
        self._input_event = threading.Event()

    def run(self, code, input_handler, result_callback):
        if self.is_running:
            result_callback("! Код уже выполняется, подождите...")
            return False
        if not code.strip():
            result_callback("X Введите код перед запуском")
            return False
        
        self.is_running = True
        self._input_queue.clear()
        self._input_event.clear()
        
        def execute():
            old_stdout = sys.stdout
            redirected_output = io.StringIO()
            sys.stdout = redirected_output
            original_input = builtins.input
            builtins.input = input_handler
            
            try:
                exec(code, {})
                result = redirected_output.getvalue()
                if not result.strip():
                    result = "! Код выполнен успешно"
            except Exception:
                result = f"Ошибка:\n{traceback.format_exc()}"
            finally:
                sys.stdout = old_stdout
                builtins.input = original_input
                self.is_running = False
            
            Clock.schedule_once(lambda dt: result_callback(result))
        
        threading.Thread(target=execute, daemon=True).start()
        return True
    
    def provide_input(self, value):
        self._input_queue.append(value)
        self._input_event.set()
    
    def clear_input(self):
        self._input_queue.clear()
        self._input_event.clear()


class LineNumberTextInput(BoxLayout):
    """Основной компонент редактора кода с нумерацией строк"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        ThemeManager.register(self)
        self.original_lines = []
        self.current_syntax_style = 'monokai'
        self._ensuring_trailing = False
        self._keyboard_visible = True
        self._saved_selection_start = None
        self._saved_selection_end = None
        self._current_line_highlight = None
        self._indent_guides = []
        self._undo_stack = []
        self._redo_stack = []
        self._undo_max = 200
        self._undo_lock = False
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
        self.line_panel.clear_widgets()
        for i in range(n_lines):
            row = BoxLayout(orientation='horizontal', size_hint_y=None, height=lh)
            lbl = Label(text=str(i + 1), font_size=self._font_size, size_hint_x=None, width=dp(33), color=theme.get('panel_text', (0.45, 0.48, 0.50, 1)), halign='right', valign='middle', padding=(0, 0, dp(3), 0))
            row.add_widget(lbl)
            self.line_panel.add_widget(row)
        self.line_panel.height = max(self.text_input.height, n_lines * lh)
        self._update_separator()

    def apply_theme(self, theme):
        if hasattr(self, 'panel_bg_color'):
            self.panel_bg_color.rgba = theme['panel_bg']
            self._update_panel_bg()
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
        self.line_panel = BoxLayout(orientation='vertical', size_hint=(None, None), width=dp(33), spacing=0)
        self.line_panel.bind(minimum_height=self.line_panel.setter('height'))
        theme = ThemeManager.get_theme()
        with self.line_panel.canvas.before:
            self.panel_bg_color = Color(*theme.get('panel_bg', (1, 1, 1, 1)))
            self.panel_bg_rect = Rectangle(pos=self.line_panel.pos, size=self.line_panel.size)
        self.line_panel.bind(pos=self._update_panel_bg, size=self._update_panel_bg)
        theme = ThemeManager.get_theme()
        scroll_bar_color = theme.get('scroll_bar_color', (0.4, 0.4, 0.4, 0.9))
        scroll_bar_inactive = theme.get('scroll_bar_inactive', (0.25, 0.25, 0.25, 0.6))
        self.line_panel_scroll = ScrollView(size_hint=(None, 1), width=dp(33), do_scroll_x=False, do_scroll_y=True, scroll_type=['bars'], bar_width=0, effect_cls='ScrollEffect', scroll_distance=dp(17), scroll_timeout=dp(33))
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
        font_size = dp(12)
        padding_top = 0
        padding_bottom = 0
        if has_lexer and CodeInput:
            self.text_input = CodeInput(lexer=PythonLexer(), style=style_name, size_hint=(None, None), font_size=font_size, background_color=theme['editor_bg'], foreground_color=theme['editor_text'], cursor_color=theme['editor_cursor'], selection_color=theme.get('editor_selection', (1, 1, 1, 0.1)), multiline=True, do_wrap=False, padding=(dp(8), padding_top, dp(8), padding_bottom), background_normal='', background_active='')
        else:
            self.text_input = TextInput(size_hint=(None, None), font_size=font_size, background_color=theme['editor_bg'], foreground_color=theme['editor_text'], cursor_color=theme['editor_cursor'], selection_color=theme.get('editor_selection', (1, 1, 1, 0.1)), multiline=True, do_wrap=False, padding=(dp(8), padding_top, dp(8), padding_bottom), background_normal='', background_active='')
        self._font_size = font_size
        self._padding_top = padding_top
        self._padding_bottom = padding_bottom
        self.text_input.bind(minimum_height=self.text_input.setter('height'))
        if hasattr(self.text_input, 'minimum_width'):
            self.text_input.bind(minimum_width=self.text_input.setter('width'))
        self.text_input.width = dp(400)
        scroll_bar_color = theme.get('scroll_bar_color', (0.4, 0.4, 0.4, 0.9))
        scroll_bar_inactive = theme.get('scroll_bar_inactive', (0.25, 0.25, 0.25, 0.6))
        self.editor_scroll = ScrollView(size_hint=(1, 1), do_scroll_x=True, do_scroll_y=True, scroll_type=['bars', 'content'], bar_width=dp(4), bar_color=scroll_bar_color, bar_inactive_color=scroll_bar_inactive, effect_cls='ScrollEffect', scroll_distance=dp(17), scroll_timeout=dp(33))
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
                    self._undo_stack.append({'text': prev_text, 'cursor': instance.cursor_index() if hasattr(instance, 'cursor_index') else 0})
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
        Clock.unschedule(self._delayed_update_panel)
        Clock.schedule_once(self._delayed_update_panel, 0.05)
        Clock.schedule_once(self._update_text_width, 0.1)
        Clock.unschedule(self._ensure_trailing)
        Clock.schedule_once(self._ensure_trailing, 0)
        Clock.unschedule(self._draw_indent_guides)
        Clock.schedule_once(self._draw_indent_guides, 0.3)

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

    def _update_panel_bg(self, instance=None, value=None):
        if hasattr(self, 'panel_bg_rect'):
            self.panel_bg_rect.pos = self.line_panel.pos
            self.panel_bg_rect.size = self.line_panel.size

    def _update_separator(self, instance=None, value=None):
        if hasattr(self, 'separator_line') and hasattr(self, 'line_panel_scroll'):
            x = self.layout.x + self.line_panel_scroll.width
            y1 = self.layout.y
            y2 = self.layout.y + self.layout.height
            self.separator_line.points = [x, y1, x, y2]

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
        panel_width = dp(33)
        current_widgets = len(self.line_panel.children)
        if current_widgets == n_lines:
            for i, child in enumerate(reversed(self.line_panel.children)):
                if hasattr(child, 'children') and child.children:
                    lbl = child.children[0]
                    if isinstance(lbl, Label):
                        lbl.text = str(i + 1)
            return
        diff = n_lines - current_widgets
        if 0 < diff <= 10:
            for i in range(current_widgets, n_lines):
                row = BoxLayout(orientation='horizontal', size_hint_y=None, height=lh)
                lbl = Label(text=str(i + 1), font_size=self._font_size, size_hint_x=None, width=panel_width, color=theme['panel_text'], halign='right', valign='top', padding=(0, 0, dp(3), 0))
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
                lbl = Label(text=str(i + 1), font_size=self._font_size, size_hint_x=None, width=panel_width, color=theme['panel_text'], halign='right', valign='top', padding=(0, 0, dp(3), 0))
                lbl.text_size = (panel_width - dp(3), None)
                row.add_widget(lbl)
                self.line_panel.add_widget(row)
            if batch_end < n_lines:
                Clock.schedule_once(lambda dt: None, 0)
        self.line_panel.height = max(self.text_input.height, n_lines * lh)
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
            self.text_input = CodeInput(lexer=PythonLexer(), style=style_name, size_hint=(None, None), font_size=self._font_size, background_color=theme['editor_bg'], foreground_color=theme['editor_text'], cursor_color=theme['editor_cursor'], selection_color=theme.get('editor_selection', (1, 1, 1, 0.1)), multiline=True, do_wrap=False, padding=(dp(8), self._padding_top, dp(8), self._padding_bottom), background_normal='', background_active='')
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


class FileDialog(BoxLayout):
    """Диалог для открытия и сохранения файлов"""
    def __init__(self, callback, cancel, is_save=False, popup=None, **kwargs):
        super().__init__(**kwargs)
        self.callback = callback
        self.cancel = cancel
        self.popup = popup
        self.is_save = is_save
        self.orientation = 'vertical'
        self.padding = dp(7)
        self.spacing = dp(4)
        self.selected_file = None
        theme = ThemeManager.get_theme()
        app = App.get_running_app()
        self.tr = app.tr if app else TRANSLATIONS['ru']
        start_path = self._get_start_path()
        self.current_path = start_path
        self._create_navigation_bar(theme)
        self._create_path_label(theme, start_path)
        self._create_file_list(theme)
        self._create_up_button(theme)
        if is_save:
            self._create_filename_input(theme)
        self._create_action_buttons(theme)
        self._load_files()

    def _create_navigation_bar(self, theme):
        nav_box = BoxLayout(size_hint_y=None, height=dp(30), spacing=dp(3))
        btn_app = Button(text=self.tr.get('app_folder', '[App]'), font_name='SourceBold', size_hint_x=0.33, background_color=theme['widget_bg'], background_normal='', background_down='', color=theme['text_color'], font_size=dp(12))
        btn_app.bind(on_release=lambda x: self._change_path(os.getcwd()))
        nav_box.add_widget(btn_app)
        btn_dl = Button(text=self.tr.get('download_folder', '[Download]'), font_name='SourceBold', size_hint_x=0.33, background_color=theme['widget_bg'], background_normal='', background_down='', color=theme['text_color'], font_size=dp(12))
        btn_dl.bind(on_release=lambda x: self._change_path('/storage/emulated/0/Download'))
        nav_box.add_widget(btn_dl)
        btn_root = Button(text=self.tr.get('sdcard_folder', '[/sdcard]'), font_name='SourceBold', size_hint_x=0.34, background_color=theme['widget_bg'], background_normal='', background_down='', color=theme['text_color'], font_size=dp(12))
        btn_root.bind(on_release=lambda x: self._change_path('/storage/emulated/0'))
        nav_box.add_widget(btn_root)
        self.add_widget(nav_box)

    def _create_path_label(self, theme, start_path):
        self.path_label = Label(text=start_path, font_name='SourceBold', color=theme['stats_text'], font_size=dp(11), size_hint_y=None, height=dp(17), halign='left', valign='middle', text_size=(None, dp(17)), shorten=True, shorten_from='left')
        self.add_widget(self.path_label)

    def _create_file_list(self, theme):
        self.file_list_scroll = ScrollView()
        self.file_list = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(1))
        self.file_list.bind(minimum_height=self.file_list.setter('height'))
        self.file_list_scroll.add_widget(self.file_list)
        self.add_widget(self.file_list_scroll)

    def _create_up_button(self, theme):
        btn_up = Button(text=self.tr.get('up_level', 'A На уровень выше'), font_name='SourceBold', size_hint_y=None, height=dp(23), background_color=theme['widget_bg'], background_normal='', background_down='', color=theme['text_color'], font_size=dp(12))
        btn_up.bind(on_release=self._go_up)
        self.add_widget(btn_up)

    def _create_filename_input(self, theme):
        self.file_name_input = TextInput(
            text='script.py', font_name='SourceBold',
            multiline=False, size_hint_y=None, height=dp(33),
            font_size=dp(12), background_color=theme['input_bg'],
            foreground_color=theme['input_text'],
            cursor_color=theme['input_cursor'],
            hint_text=self.tr.get('file_name', 'Имя файла...'),
            hint_text_color=theme['hint_text'], padding=(dp(7), dp(7))
        )
        # При фокусе — поднимаем окно
        self.file_name_input.bind(focus=self._on_filename_focus)
        self.add_widget(self.file_name_input)

    def _create_action_buttons(self, theme):
        btns = BoxLayout(size_hint_y=None, height=dp(33), spacing=dp(5))
        btn_cancel = Button(text=self.tr.get('cancel', 'Отмена'), font_name='SourceBold', background_color=theme['widget_bg'], background_normal='', background_down='', color=theme['text_color'], font_size=dp(12))
        btn_cancel.bind(on_release=self._on_cancel)
        action_text = self.tr.get('save_file') if self.is_save else self.tr.get('open', 'Открыть')
        btn_action = Button(text=action_text, font_name='SourceBold', background_color=theme['widget_bg'], background_normal='', background_down='', color=theme['text_color'], font_size=dp(12))
        btn_action.bind(on_release=self._on_action)
        btns.add_widget(btn_cancel)
        btns.add_widget(btn_action)
        self.add_widget(btns)

    def _get_start_path(self):
        if PLYER_AVAILABLE:
            try:
                path = storagepath.get_downloads_dir()
                if path and os.path.exists(path):
                    return path
            except:
                pass
        if ANV_AVAILABLE and androidstorage:
            try:
                path = androidstorage.get_external_storage_path()
                if path:
                    download = path + '/Download'
                    if os.path.exists(download):
                        return download
                    return path
            except:
                pass
        paths = ['/storage/emulated/0/Download', '/storage/emulated/0', os.getcwd()]
        for p in paths:
            if os.path.exists(p):
                return p
        return os.getcwd()

    def _change_path(self, path):
        if os.path.exists(path):
            self.current_path = path
            self.selected_file = None
            self._load_files()

    def _go_up(self, instance):
        parent = os.path.dirname(self.current_path)
        if parent and parent != self.current_path:
            self.current_path = parent
            self.selected_file = None
            self._load_files()

    def _load_files(self):
        self.file_list.clear_widgets()
        self.path_label.text = self.current_path
        theme = ThemeManager.get_theme()
        try:
            items = os.listdir(self.current_path)
        except:
            self.file_list.add_widget(Label(text=self.tr.get('no_access', '[Нет доступа к папке]'), font_name='SourceBold', color=theme['stats_text'], font_size=dp(11), size_hint_y=None, height=dp(20)))
            return
        items.sort(key=str.lower)
        folders = []
        files = []
        for item in items:
            full = os.path.join(self.current_path, item)
            try:
                if os.path.isdir(full):
                    folders.append(item)
                else:
                    files.append(item)
            except:
                pass
        for folder in folders:
            full = os.path.join(self.current_path, folder)
            btn = Button(text=f'[+] {folder}', font_name='SourceBold', size_hint_y=None, height=dp(23), background_color=theme['widget_bg'], background_normal='', background_down='', color=theme['text_color'], font_size=dp(11), halign='left', valign='middle', padding=(dp(7), 0))
            btn.bind(on_release=lambda x, p=full: self._change_path(p))
            self.file_list.add_widget(btn)
        for file in files:
            full = os.path.join(self.current_path, file)
            btn = Button(text=f'  {file}', font_name='SourceBold', size_hint_y=None, height=dp(23), background_color=theme['input_bg'], background_normal='', background_down='', color=theme['input_text'], font_size=dp(11), halign='left', valign='middle', padding=(dp(7), 0))
            btn.bind(on_release=lambda x, p=full: self._select_file(p))
            self.file_list.add_widget(btn)
        if not folders and not files:
            self.file_list.add_widget(Label(text=self.tr.get('empty', '[Пусто]'), font_name='SourceBold', color=theme['stats_text'], font_size=dp(11), size_hint_y=None, height=dp(20)))

    def _select_file(self, path):
        self.selected_file = path
        theme = ThemeManager.get_theme()
        target_name = os.path.basename(path)
        for child in self.file_list.children:
            if isinstance(child, Button):
                if child.text.startswith('  '):
                    child.background_color = theme['input_bg']
                elif child.text.startswith('[+]'):
                    child.background_color = theme['widget_bg']
        for child in self.file_list.children:
            if isinstance(child, Button):
                if child.text == f'  {target_name}':
                    child.background_color = theme.get('btn_selected_file_bg', (0.3, 0.5, 0.3, 1))
                    break
    
    def _on_filename_focus(self, instance, focused):
        """Поднимает окно при фокусе на поле ввода имени файла."""
        if focused and self.popup:
            # Поднимаем окно выше, когда клавиатура открыта
            self.popup.pos_hint = {'top': 1.25}  # ← больше число = выше окно
        elif not focused and self.popup:
            # Возвращаем на место, когда клавиатура закрыта
            self.popup.pos_hint = {'top': 0.95}

    def _on_cancel(self, instance):
        if self.popup:
            self.popup.dismiss()
        if self.cancel:
            self.cancel()

    def _on_action(self, instance):
        if self.popup:
            self.popup.dismiss()
        if self.is_save:
            if self.callback:
                self.callback(self.current_path, self.file_name_input.text)
        else:
            if self.selected_file and self.callback:
                self.callback([self.selected_file])


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
    background_color = ColorProperty([0, 0, 0, 0])
    border = ListProperty([0, 0, 0, 0])
    background_image = StringProperty('')

    def __init__(self, text_input, **kwargs):
        kwargs.pop('background_normal', None)
        kwargs.pop('background_down', None)
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_y = None
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
        self.action_keys = [self.ACTION_UNDO, self.ACTION_REDO, self.ACTION_COPY, self.ACTION_PASTE, self.ACTION_CUT, self.ACTION_SEL_ALL, self.ACTION_AUTO, self.ACTION_KEY, self.ACTION_CLEAN, self.ACTION_FIND]
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
        self.scroll_view = ScrollView(size_hint=(1, 1), do_scroll_x=True, do_scroll_y=False, bar_width=dp(2), bar_color=scroll_bar_color, bar_inactive_color=scroll_bar_inactive)
        self.button_container = BoxLayout(orientation='horizontal', size_hint_x=None, spacing=self.spacing, padding=self.padding)
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
            self.ACTION_FIND: 'magnify',
        }
        for key in self.action_keys:
            icon_name = action_icons.get(key, None)
            if icon_name:
                from kivymd.uix.button import MDIconButton
                btn = MDIconButton(icon=icon_name, size_hint=(None, None), size=(dp(30), dp(30)), font_size=f"{dp(12)}sp", theme_icon_color="Custom", icon_color=theme['symbol_btn_text'], pos_hint={"center_y": 0.5})
            else:
                app = App.get_running_app()
                tr = app.tr if app else TRANSLATIONS['ru']
                btn = Button(text=tr.get(key, key), size_hint=(None, 1), width=dp(32), font_size=dp(11), background_color=theme['symbol_btn_bg'], background_normal='', background_down='', color=theme['symbol_btn_text'], bold=True)
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
            if action_key in [self.ACTION_COPY, self.ACTION_PASTE, self.ACTION_CUT, self.ACTION_SEL_ALL, self.ACTION_CLEAN, self.ACTION_UNDO, self.ACTION_REDO]:
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
        self._keywords_popup = self._create_filterable_dialog(tr.get('keywords_title', 'Python Keywords'), self._get_keywords_list(), insert_word)
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
        self._autocomplete_popup = self._create_filterable_dialog(tr.get('autocomplete_title', 'Autocomplete'), self._get_autocomplete_list(), insert_word)
        self._autocomplete_popup.open()

    def _create_filterable_dialog(self, title, items, insert_callback):
        theme = ThemeManager.get_theme()
        app = App.get_running_app()
        tr = app.tr if app else TRANSLATIONS['ru']
        layout = BoxLayout(orientation='vertical', spacing=dp(3), padding=dp(4))
        search_box = TextInput(hint_text=tr.get('search_hint', 'Search...'), multiline=False, font_size=dp(17), font_name='SourceBold', background_color=theme['input_bg'], foreground_color=theme['input_text'], cursor_color=theme['input_cursor'], hint_text_color=theme['hint_text'], size_hint_y=None, height=dp(28), padding=(dp(3), dp(3)))
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
                btn = Button(text=word, size_hint_y=None, height=dp(20), font_name='SourceBold', background_color=theme['input_bg'], background_normal='', background_down='', color=theme['input_text'], font_size=dp(17))
                btn.bind(on_release=lambda b, w=word: self._on_word_selected(w, insert_callback))
                inner.add_widget(btn)
        search_box.bind(text=lambda inst, val: update_buttons(val))
        update_buttons()
        close_btn = Button(text=tr.get('close', 'Close'), size_hint_y=None, height=dp(28), font_size=dp(17), font_name='SourceBold', background_color=theme['widget_bg'], background_normal='', background_down='', color=theme['text_color'])
        layout.add_widget(close_btn)
        popup = Popup(title=title, title_color=theme['popup_title'],background='', background_color=theme.get('popup_bg', (1.0, 1.0, 1.0, 1)), content=layout, size_hint=(0.9, 0.8))
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
                self._keywords_cache = ['False', 'None', 'True', 'and', 'as', 'assert', 'async', 'await', 'break', 'class', 'continue', 'def', 'del', 'elif', 'else', 'except', 'finally', 'for', 'from', 'global', 'if', 'import', 'in', 'is', 'lambda', 'nonlocal', 'not', 'or', 'pass', 'raise', 'return', 'try', 'while', 'with', 'yield']
        return self._keywords_cache

    def _get_autocomplete_list(self):
        if self._autocomplete_cache is None:
            self._autocomplete_cache = sorted(['abs', 'all', 'any', 'bin', 'bool', 'callable', 'chr', 'dict', 'dir', 'enumerate', 'filter', 'float', 'format', 'input', 'int', 'len', 'list', 'map', 'max', 'min', 'print', 'range', 'round', 'set', 'sorted', 'str', 'sum', 'tuple', 'type', 'zip'])
        return self._autocomplete_cache

    def _confirm_clean(self, ti):
        theme = ThemeManager.get_theme()
        app = App.get_running_app()
        tr = app.tr if app else TRANSLATIONS['ru']
        content = BoxLayout(orientation='vertical', padding=dp(5), spacing=dp(3))
        content.add_widget(Label(text=tr.get('clean_confirm', 'Are you sure you want to clear all code?'), color=theme['text_color'], font_size=dp(10), font_name='SourceBold', halign='center', size_hint_y=None, height=dp(20)))
        btn_layout = BoxLayout(size_hint_y=None, height=dp(18), spacing=dp(4))
        popup = ThemedPopup(title=tr.get('clean', 'Clean'), title_color=theme['popup_title'], title_bg=theme.get('popup_title_bg', theme['widget_bg']), popup_bg=theme.get('popup_bg', theme['widget_bg']), separator_color=theme.get('popup_separator', (0.25, 0.25, 0.25, 1)), content=content, size_hint=(0.8, 0.3), auto_dismiss=False)
        btn_yes = Button(text=tr.get('yes', 'Yes'), font_name='SourceBold', background_color=theme.get('btn_danger_bg', (0.5, 0.2, 0.2, 1)), background_normal='', background_down='', color=theme['text_color'], font_size=dp(9), on_release=lambda x: self._do_clean(popup, ti))
        btn_no = Button(text=tr.get('no', 'No'), font_name='SourceBold', background_color=theme['widget_bg'], background_normal='', background_down='', color=theme['text_color'], font_size=dp(9), on_release=lambda x: popup.dismiss())
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
        self.height = dp(30)
        self.spacing = dp(2)
        self.padding = [dp(2), dp(2), dp(2), dp(2)]
        self.app = None
        self.text_input = text_input
        self._saved_sel_start = None
        self._saved_sel_end = None
        ThemeManager.register(self)
        self.symbols = ['Tab', '#', '( )', '[ ]', '{ }', '" "', "' '", '=', ':', '.', '_', ',', '+', '-', '*', '/', '\\', '%', ')', ']', '}', '<', '>', '!', '|', '&', '@', '~', '?', ';', '$', '^']
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
        self.scroll_view = ScrollView(size_hint=(1, 1), do_scroll_x=True, do_scroll_y=False, bar_width=dp(2), bar_color=scroll_bar_color, bar_inactive_color=scroll_bar_inactive)
        self.button_container = BoxLayout(orientation='horizontal', size_hint_x=None, spacing=self.spacing, padding=self.padding)
        self.button_container.bind(minimum_width=self.button_container.setter('width'))
        self.scroll_view.add_widget(self.button_container)
        self.add_widget(self.scroll_view)

    def _create_buttons(self):
        theme = ThemeManager.get_theme()
        wide_symbols = {'( )': dp(37), '[ ]': dp(37), '{ }': dp(37), '" "': dp(37), "' '": dp(37), 'Tab': dp(37)}
        default_width = dp(30)
        for symbol in self.symbols:
            width = wide_symbols.get(symbol, default_width)
            btn = Button(text=symbol, font_name='SourceBold', size_hint=(None, 1), width=width, background_color=theme['symbol_btn_bg'], background_normal='', background_down='', color=theme['symbol_btn_text'], font_size=dp(13))
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


class AIAssistantPopup(BoxLayout):
    """Диалог для общения с AI-ассистентом"""
    API_URL = "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent"
    MAX_RETRIES = 5
    BASE_DELAY = 2
    TIMEOUT = 30

    def __init__(self, api_key, **kwargs):
        super().__init__(**kwargs)
        self.api_key = api_key
        self.orientation = 'vertical'
        self.padding = dp(5)
        self.spacing = dp(3)
        app = App.get_running_app()
        self.tr = app.tr if app else TRANSLATIONS['ru']
        theme = ThemeManager.get_theme()
        self._create_ui(theme)

    def _create_ui(self, theme):
        tr = self.tr
        title_label = Label(text=f'[b]{tr.get("ai_title", "AI Python Assistant")}[/b]', markup=True, color=theme['text_color'], font_size=dp(12), font_name='SourceBold', size_hint_y=None, height=dp(17))
        self.add_widget(title_label)
        self.question_input = TextInput(hint_text=tr.get('ai_hint', 'Ask me anything about Python...'), multiline=True, font_size=dp(11), font_name='SourceBold', background_color=theme['input_bg'], foreground_color=theme['input_text'], hint_text_color=theme['hint_text'], size_hint_y=None, height=dp(33), padding=(dp(5), dp(5)))
        self.add_widget(self.question_input)
        self.ask_btn = Button(text=tr.get('ai_btn', 'Ask AI'), font_name='SourceBold', size_hint_y=None, height=dp(23), background_color=theme['widget_bg'], background_normal='', background_down='', color=theme['text_color'], font_size=dp(11), bold=True)
        self.ask_btn.bind(on_release=self.ask_ai)
        self.add_widget(self.ask_btn)
        self.response_scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False, do_scroll_y=True)
        self.response_text = TextInput(text=tr.get('ai_placeholder', 'AI response will appear here...'), readonly=True, font_size=dp(10), font_name='SourceBold', background_color=theme['ai_response_bg'], foreground_color=theme['editor_text'], do_wrap=True, padding=(dp(5), dp(5)))
        self.response_scroll.add_widget(self.response_text)
        self.add_widget(self.response_scroll)
        self.loading_label = Label(text='', color=theme['text_color'], font_size=dp(9), font_name='SourceBold', size_hint_y=None, height=dp(13))
        self.add_widget(self.loading_label)

    def ask_ai(self, instance):
        question = self.question_input.text.strip()
        if not question:
            return
        self.ask_btn.disabled = True
        self.loading_label.text = self.tr.get('ai_thinking', 'Thinking...')
        self.response_text.text = ''
        threading.Thread(target=self._send_request, args=(question,), daemon=True).start()

    def _send_request(self, question):
        tr = self.tr
        for attempt in range(self.MAX_RETRIES):
            try:
                context = ssl._create_unverified_context()
                prompt = ("You are a helpful Python programming assistant. Provide clear, concise explanations and code examples when appropriate. The user is learning Python on Android.\n\nUser question: " + question + "\n\nAnswer:")
                url = f"{self.API_URL}?key={self.api_key}"
                headers = {'Content-Type': 'application/json'}
                data = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1024}}
                req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers, method='POST')
                with urllib.request.urlopen(req, timeout=self.TIMEOUT, context=context) as response:
                    resp_data = json.loads(response.read().decode('utf-8'))
                    answer = resp_data['candidates'][0]['content']['parts'][0]['text']
                Clock.schedule_once(lambda dt: self._show_response(answer))
                return
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    if attempt < self.MAX_RETRIES - 1:
                        wait_time = self.BASE_DELAY * (2 ** attempt)
                        Clock.schedule_once(lambda dt, t=wait_time: self._show_status(f"{tr.get('rate_limit', 'Rate limit. Wait')} {t} {tr.get('sec', 'sec')}..."), 0)
                        time.sleep(wait_time)
                        continue
                    else:
                        msg = tr.get('rate_limit_exceeded', 'Rate limit exceeded. Try later.')
                        Clock.schedule_once(lambda dt: self._show_response(msg))
                else:
                    msg = f"HTTP Error {e.code}: {e.reason}"
                    Clock.schedule_once(lambda dt: self._show_response(msg))
                return
            except urllib.error.URLError as e:
                msg = tr.get('network_error', 'X Network error: No internet connection')
                Clock.schedule_once(lambda dt: self._show_response(msg))
                return
            except Exception as e:
                msg = f"Error: {str(e)}"
                Clock.schedule_once(lambda dt: self._show_response(msg))
                return

    def _show_response(self, text):
        self.response_text.text = text
        self.loading_label.text = ''
        self.ask_btn.disabled = False

    def _show_status(self, text):
        self.loading_label.text = text


class SearchOnlyPopup(BoxLayout):
    """Диалог для поиска текста"""
    def __init__(self, text_input, **kwargs):
        super().__init__(**kwargs)
        self.text_input = text_input
        self.orientation = 'vertical'
        self.padding = [dp(3), dp(3), dp(3), dp(3)]
        self.spacing = dp(2)
        self.last_search = ''
        self.search_results = []
        self.current_result_index = -1
        self.popup = None
        app = App.get_running_app()
        self.tr = app.tr if app else TRANSLATIONS['ru']
        theme = ThemeManager.get_theme()
        self._create_ui(theme)

    def _create_ui(self, theme):
        tr = self.tr
        with self.canvas.before:
            bg_color = theme['widget_bg']
            lighter_bg = (bg_color[0] * 0.8 + 1.0 * 0.2, bg_color[1] * 0.8 + 1.0 * 0.2, bg_color[2] * 0.8 + 1.0 * 0.2, bg_color[3])
            Color(*lighter_bg)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)
        search_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(20), spacing=dp(2))
        self.search_input = TextInput(hint_text=tr.get('find_text', 'Search text'), multiline=False, font_size=dp(10), font_name='SourceBold', background_color=theme['input_bg'], foreground_color=theme['input_text'], cursor_color=theme['input_cursor'], hint_text_color=theme['hint_text'], size_hint_x=0.75)
        self.search_input.bind(text=self._on_search_text_change)
        search_row.add_widget(self.search_input)
        btn_close = Button(text=tr.get('close', 'Close'), font_name='SourceBold', size_hint_x=0.25, background_color=theme.get('btn_danger_bg', (0.5, 0.2, 0.2, 1)), background_normal='', background_down='', color=theme['text_color'], font_size=dp(9))
        btn_close.bind(on_release=self.dismiss)
        search_row.add_widget(btn_close)
        self.add_widget(search_row)
        nav_layout = BoxLayout(size_hint_y=None, height=dp(15), spacing=dp(3))
        btn_prev = Button(text='◀', font_name='SourceBold', background_color=theme['widget_bg'], background_normal='', background_down='', color=theme['text_color'], font_size=dp(9), on_release=lambda x: self.find_previous())
        btn_next = Button(text='▶', font_name='SourceBold', background_color=theme['widget_bg'], background_normal='', background_down='', color=theme['text_color'], font_size=dp(9), on_release=lambda x: self.find_next())
        nav_layout.add_widget(btn_prev)
        nav_layout.add_widget(btn_next)
        self.add_widget(nav_layout)

    def _update_bg(self, instance, value):
        if hasattr(self, 'bg_rect'):
            self.bg_rect.pos = instance.pos
            self.bg_rect.size = instance.size

    def _on_search_text_change(self, instance, value):
        if value != self.last_search:
            self._perform_search()

    def _perform_search(self):
        search_text = self.search_input.text
        if not search_text:
            self.search_results = []
            return
        self.last_search = search_text
        text = self.text_input.text
        if not text:
            self.search_results = []
            return
        try:
            self.search_results = []
            search_lower = search_text.lower()
            text_lower = text.lower()
            start = 0
            while True:
                pos = text_lower.find(search_lower, start)
                if pos == -1:
                    break
                self.search_results.append((pos, pos + len(search_text)))
                start = pos + 1
        except:
            self.search_results = []
        self.current_result_index = -1
        if self.search_results:
            self.find_next()

    def find_next(self):
        if not self.search_results:
            return
        self.current_result_index = (self.current_result_index + 1) % len(self.search_results)
        self._highlight_current()

    def find_previous(self):
        if not self.search_results:
            return
        self.current_result_index = (self.current_result_index - 1) % len(self.search_results)
        self._highlight_current()

    def _highlight_current(self):
        if not self.search_results or self.current_result_index < 0:
            return
        start, end = self.search_results[self.current_result_index]
        self.text_input.select_text(start, end)
        self._scroll_to_position(start)

    def _scroll_to_position(self, position):
        try:
            text = self.text_input.text
            text_before = text[:position]
            line_number = text_before.count('\n')
            total_lines = max(1, text.count('\n') + 1)
            target_y = 1.0 - (line_number / total_lines)
            target_y = max(0.0, min(1.0, target_y))
            parent = self.text_input.parent
            while parent:
                if isinstance(parent, ScrollView):
                    parent.scroll_y = target_y
                    break
                parent = parent.parent
        except:
            pass

    def set_popup(self, popup):
        self.popup = popup
        if hasattr(popup, 'bind'):
            popup.bind(on_touch_down=self._on_popup_touch)

    def _on_popup_touch(self, instance, touch):
        if self.collide_point(*touch.pos):
            return False
        if hasattr(self, 'text_input') and self.text_input:
            self.text_input.focus = True
            return False

    def dismiss(self, *args):
        if self.popup:
            self.popup.dismiss()

    def open_popup(self):
        if self.popup:
            self.popup.open()
            Clock.schedule_once(lambda dt: self._focus_search(), 0.3)

    def _focus_search(self):
        if self.search_input:
            self.search_input.focus = True


class SearchReplacePopup(BoxLayout):
    """Диалог для поиска и замены"""
    def __init__(self, text_input, **kwargs):
        super().__init__(**kwargs)
        self.text_input = text_input
        self.orientation = 'vertical'
        self.padding = [dp(3), dp(3), dp(3), dp(3)]
        self.spacing = dp(2)
        self.last_search = ''
        self.search_results = []
        self.current_result_index = -1
        self.popup = None
        app = App.get_running_app()
        self.tr = app.tr if app else TRANSLATIONS['ru']
        theme = ThemeManager.get_theme()
        self._create_ui(theme)

    def _create_ui(self, theme):
        tr = self.tr
        with self.canvas.before:
            bg_color = theme['widget_bg']
            lighter_bg = (bg_color[0] * 0.8 + 1.0 * 0.2, bg_color[1] * 0.8 + 1.0 * 0.2, bg_color[2] * 0.8 + 1.0 * 0.2, bg_color[3])
            Color(*lighter_bg)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)
        search_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(18), spacing=dp(2))
        self.search_input = TextInput(hint_text=tr.get('find_text', 'Find text'), multiline=False, font_size=dp(10), font_name='SourceBold', background_color=theme['input_bg'], foreground_color=theme['input_text'], cursor_color=theme['input_cursor'], hint_text_color=theme['hint_text'], size_hint_x=0.75)
        self.search_input.bind(text=self._on_search_text_change)
        search_row.add_widget(self.search_input)
        btn_close = Button(text=tr.get('close', 'Close'), font_name='SourceBold', size_hint_x=0.25, background_color=theme.get('btn_danger_bg', (0.5, 0.2, 0.2, 1)), background_normal='', background_down='', color=theme['text_color'], font_size=dp(9))
        btn_close.bind(on_release=self.dismiss)
        search_row.add_widget(btn_close)
        self.add_widget(search_row)
        self.replace_input = TextInput(hint_text=tr.get('replace_text', 'Replace with'), multiline=False, font_size=dp(10), font_name='SourceBold', background_color=theme['input_bg'], foreground_color=theme['input_text'], cursor_color=theme['input_cursor'], hint_text_color=theme['hint_text'], size_hint_y=None, height=dp(18))
        self.add_widget(self.replace_input)
        btn_layout = BoxLayout(size_hint_y=None, height=dp(17), spacing=dp(3))
        btn_replace = Button(text=tr.get('replace', 'Replace'), font_name='SourceBold', background_color=theme.get('btn_success_bg', (0.2, 0.5, 0.2, 1)), background_normal='', background_down='', color=theme['text_color'], font_size=dp(9), on_release=lambda x: self.replace_current())
        btn_next = Button(text='▶', font_name='SourceBold', background_color=theme['widget_bg'], background_normal='', background_down='', color=theme['text_color'], font_size=dp(9), on_release=lambda x: self.find_next())
        btn_replace_all = Button(text=tr.get('replace_all', 'Replace All'), font_name='SourceBold', background_color=theme['symbol_btn_bg'], background_normal='', background_down='', color=theme['text_color'], font_size=dp(9), on_release=lambda x: self.replace_all())
        btn_layout.add_widget(btn_replace)
        btn_layout.add_widget(btn_next)
        btn_layout.add_widget(btn_replace_all)
        self.add_widget(btn_layout)

    def _update_bg(self, instance, value):
        if hasattr(self, 'bg_rect'):
            self.bg_rect.pos = instance.pos
            self.bg_rect.size = instance.size

    def _on_search_text_change(self, instance, value):
        if value != self.last_search:
            self._perform_search()

    def _perform_search(self):
        search_text = self.search_input.text
        if not search_text:
            self.search_results = []
            return
        self.last_search = search_text
        text = self.text_input.text
        if not text:
            self.search_results = []
            return
        try:
            self.search_results = []
            search_lower = search_text.lower()
            text_lower = text.lower()
            start = 0
            while True:
                pos = text_lower.find(search_lower, start)
                if pos == -1:
                    break
                self.search_results.append((pos, pos + len(search_text)))
                start = pos + 1
        except:
            self.search_results = []
        self.current_result_index = -1
        if self.search_results:
            self.find_next()

    def find_next(self):
        if not self.search_results:
            return
        self.current_result_index = (self.current_result_index + 1) % len(self.search_results)
        self._highlight_current()

    def _highlight_current(self):
        if not self.search_results or self.current_result_index < 0:
            return
        start, end = self.search_results[self.current_result_index]
        self.text_input.select_text(start, end)

    def replace_current(self):
        if not self.search_results or self.current_result_index < 0:
            return
        if self.current_result_index >= len(self.search_results):
            return
        start, end = self.search_results[self.current_result_index]
        replace_text = self.replace_input.text
        self.text_input.text = self.text_input.text[:start] + replace_text + self.text_input.text[end:]
        self._perform_search()

    def replace_all(self):
        if not self.search_results:
            return
        replace_text = self.replace_input.text
        text = self.text_input.text
        for start, end in reversed(self.search_results):
            text = text[:start] + replace_text + text[end:]
        self.text_input.text = text
        self.search_results = []
        self.current_result_index = -1

    def set_popup(self, popup):
        self.popup = popup
        if hasattr(popup, 'bind'):
            popup.bind(on_touch_down=self._on_popup_touch)

    def _on_popup_touch(self, instance, touch):
        if self.collide_point(*touch.pos):
            return False
        if hasattr(self, 'text_input') and self.text_input:
            self.text_input.focus = True
            return False

    def dismiss(self, *args):
        if self.popup:
            self.popup.dismiss()

    def open_popup(self):
        if self.popup:
            self.popup.open()
            Clock.schedule_once(lambda dt: self._focus_search(), 0.3)

    def _focus_search(self):
        if self.search_input:
            self.search_input.focus = True


class TabManager:
    """Управляет вкладками редактора"""
    def __init__(self):
        self.tabs = []
        self.active_index = -1
        self.tab_bar = None
        self.app = None
        self.tab_offset = 0
        self.max_visible = 3

    def add_tab(self, title=None, text="", file_path=None):
        if title is None:
            tr = self.app.tr if self.app else {}
            title = tr.get('untitled_tab', 'Новый')
        editor = LineNumberTextInput(size_hint_y=1.0)
        editor.set_text(text)
        def set_cursor_to_start(dt):
            try:
                if editor and hasattr(editor, 'text_input') and editor.text_input:
                    editor.text_input.cursor = (0, 0)
                    editor.text_input.focus = True
            except:
                pass
        Clock.schedule_once(set_cursor_to_start, 0.3)
        tab = {'title': title, 'editor': editor, 'file': file_path, 'saved': True}
        self.tabs.append(tab)
        self.active_index = len(self.tabs) - 1
        self._update_tab_bar()
        self.save_all_tabs()
        return editor

    def close_tab(self, index):
        if len(self.tabs) <= 1:
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
            self.tabs[self.active_index]['title'] = os.path.basename(file_path) if file_path else tr.get('untitled_tab', 'Новый')
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
        self.tab_bar = BoxLayout(size_hint_y=None, height=dp(30), spacing=dp(1), padding=[dp(1), dp(1), dp(1), dp(1)])
        with self.tab_bar.canvas.before:
            Color(*theme.get('tab_bar_bg', theme['action_bar_bg']))
            self.tab_bg_rect = Rectangle(pos=self.tab_bar.pos, size=self.tab_bar.size)
        self.tab_bar.bind(pos=self._update_tab_bg, size=self._update_tab_bg)
        self.btn_left = Button(text='◀', font_name='SourceBold', size_hint_x=None, width=dp(20), background_color=theme.get('tab_inactive_bg', theme['widget_bg']), background_normal='', background_down='', color=theme['text_color'], font_size=dp(10), bold=True)
        self.btn_left.bind(on_release=lambda x: self._scroll_tabs(-1))
        self.tab_bar.add_widget(self.btn_left)
        self.tab_buttons_container = BoxLayout(spacing=dp(1), size_hint=(1, 1), padding=[dp(0.7), dp(2), dp(0.7), 0])
        self.tab_bar.add_widget(self.tab_buttons_container)
        self.btn_right = Button(text='▶', font_name='SourceBold', size_hint_x=None, width=dp(20), background_color=theme.get('tab_inactive_bg', theme['widget_bg']), background_normal='', background_down='', color=theme['text_color'], font_size=dp(10), bold=True)
        self.btn_right.bind(on_release=lambda x: self._scroll_tabs(1))
        self.tab_bar.add_widget(self.btn_right)
        btn_add = Button(text='+', font_name='SourceBold', size_hint_x=None, width=dp(25), background_color=theme.get('tab_add_btn_bg', theme['widget_bg']), background_normal='', background_down='', color=theme['text_color'], font_size=dp(17), bold=True)
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
        editor = self.add_tab()
        if self.app:
            self.app._on_tab_changed(editor)

    def _on_tab_press(self, index):
        editor = self.switch_to_tab(index)
        if editor and self.app:
            self.app._on_tab_changed(editor)

    def _on_tab_close(self, index):
        if self.close_tab(index):
            editor = self.get_active_editor()
            if editor and self.app:
                self.app._on_tab_changed(editor)

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
                    bg_color = (base_bg[0] * 1.15 if base_bg[0] * 1.15 <= 1 else 1, base_bg[1] * 1.15 if base_bg[1] * 1.15 <= 1 else 1, base_bg[2] * 1.15 if base_bg[2] * 1.15 <= 1 else 1, 1)
                text_color = theme['text_color']
            else:
                bg_color = theme.get('tab_inactive_bg', theme['widget_bg'])
                text_color = theme['text_color']
            tab_box = BoxLayout(spacing=dp(0.3), size_hint_x=None, width=dp(95))
            btn_tab = Button(text=title, font_name='SourceBold', background_color=bg_color, background_normal='', background_down='', color=text_color, font_size=dp(11), halign='left', valign='middle', padding=(dp(3), 0))
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
                btn_close = Button(text='x', font_name='SourceBold', size_hint_x=None, width=dp(20), background_color=bg_color, background_normal='', background_down='', color=theme.get('tab_close_btn_text', text_color), font_size=dp(15))
                btn_close.bind(on_release=lambda x, idx=i: self._on_tab_close(idx))
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
        
        btn_rename = Button(
            text=tr.get('rename_tab', 'Переименовать'),
            size_hint_y=None, height=dp(30),
            background_color=theme['widget_bg'],
            background_normal='', background_down='',
            color=theme['text_color'], font_size=dp(11)
        )
        btn_rename.bind(on_release=lambda x: self._rename_tab(index, menu))
        menu.add_widget(btn_rename)
        
        btn_duplicate = Button(
            text=tr.get('duplicate_tab', 'Дублировать'),
            size_hint_y=None, height=dp(30),
            background_color=theme['widget_bg'],
            background_normal='', background_down='',
            color=theme['text_color'], font_size=dp(11)
        )
        btn_duplicate.bind(on_release=lambda x: self._duplicate_tab(index, menu))
        menu.add_widget(btn_duplicate)
        
        if len(self.tabs) > 1:
            btn_close_others = Button(
                text=tr.get('close_other_tabs', 'Закрыть другие'),
                size_hint_y=None, height=dp(30),
                background_color=theme['widget_bg'],
                background_normal='', background_down='',
                color=theme['text_color'], font_size=dp(11)
            )
            btn_close_others.bind(on_release=lambda x: self._close_other_tabs(index, menu))
            menu.add_widget(btn_close_others)
        
        if len(self.tabs) > 1:
            btn_close_all = Button(
                text=tr.get('close_all_tabs', 'Закрыть все'),
                size_hint_y=None, height=dp(30),
                background_color=theme.get('tab_context_danger_bg', (0.3, 0.1, 0.1, 1)),
                background_normal='', background_down='',
                color=theme['text_color'], font_size=dp(11)
            )
            btn_close_all.bind(on_release=lambda x: self._close_all_tabs(menu))
            menu.add_widget(btn_close_all)
        
        try:
            menu.open(button)
        except:
            if hasattr(self, 'tab_bar') and self.tab_bar:
                try:
                    menu.open(self.tab_bar)
                except:
                    pass

    def _rename_tab(self, index, menu):
        menu.dismiss()
        if self.app:
            self.app._show_rename_tab_dialog(index)

    def _duplicate_tab(self, index, menu):
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
        menu.dismiss()
        if 0 <= index < len(self.tabs):
            tab = self.tabs[index]
            for t in self.tabs:
                if t != tab and hasattr(t['editor'], 'cleanup'):
                    t['editor'].cleanup()
            self.tabs = [tab]
            self.active_index = 0
            self._update_tab_bar()
            self.save_all_tabs()
            if self.app:
                self.app._on_tab_changed(tab['editor'])

    def _close_all_tabs(self, menu):
        menu.dismiss()
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

    def save_all_tabs(self):
        try:
            tabs_data = {'active_index': self.active_index, 'tabs': []}
            for tab in self.tabs:
                tabs_data['tabs'].append({'title': tab['title'], 'file': tab['file'], 'text': tab['editor'].get_text() if tab['editor'] else ''})
            save_path = os.path.join(os.getcwd(), 'tabs.json')
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(tabs_data, f, indent=2)
        except:
            pass

    def load_all_tabs(self):
        try:
            save_path = os.path.join(os.getcwd(), 'tabs.json')
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
                text = data.get('text', '')
                if text and text.strip():
                    editor.set_text(text)
                else:
                    editor.set_text('')
                tab = {'title': data.get('title', tr.get('untitled_tab', 'Новый')), 'editor': editor, 'file': data.get('file'), 'saved': True}
                self.tabs.append(tab)
            if 0 <= active_index < len(self.tabs):
                self.active_index = active_index
            else:
                self.active_index = 0
            self._update_tab_bar()
            return True
        except:
            return False


class AutoCompleteWidget(BoxLayout):
    """Панель автодополнения"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.size_hint_y = None
        self.height = 0
        self.code_input = None
        self.visible = False
        self.all_words = self._build_word_list()
        self.suggestions_box = BoxLayout(orientation='horizontal', size_hint_x=None, height=dp(23), spacing=dp(2), padding=[dp(3), dp(3)])
        self.suggestions_box.bind(minimum_width=self.suggestions_box.setter('width'))
        self.scroll = ScrollView(size_hint=(1, 1), do_scroll_x=True, do_scroll_y=False, bar_width=dp(2))
        self.scroll.add_widget(self.suggestions_box)
        self.add_widget(self.scroll)

    def _build_word_list(self):
        words = ['False', 'None', 'True', 'and', 'as', 'assert', 'async', 'await', 'break', 'class', 'continue', 'def', 'del', 'elif', 'else', 'except', 'finally', 'for', 'from', 'global', 'if', 'import', 'in', 'is', 'lambda', 'nonlocal', 'not', 'or', 'pass', 'raise', 'return', 'try', 'while', 'with', 'yield', 'print', 'input', 'len', 'range', 'int', 'str', 'float', 'list', 'dict', 'set', 'tuple', 'open', 'type', 'abs', 'max', 'min', 'sum', 'sorted', 'enumerate', 'zip', 'append', 'extend', 'insert', 'remove', 'pop', 'keys', 'values', 'items', 'get', 'update', 'split', 'join', 'replace', 'strip', 'lower', 'upper', 'startswith', 'endswith', 'self', '__init__', '__name__', '__main__']
        return sorted(set(words))

    def update_words_from_code(self):
        if not self.code_input:
            return
        text = self.code_input.text
        code_words = set(re.findall(r'[a-zA-Z_]\w+', text))
        self.all_words = sorted(set(self._build_word_list() + list(code_words)))

    def show_suggestions(self, current_word):
        self.suggestions_box.clear_widgets()
        if self.code_input and self.code_input.text.strip():
            self.update_words_from_code()
        if not current_word or len(current_word) < 2:
            self.height = 0
            self.visible = False
            return
        word_lower = current_word.lower()
        starts_with = [w for w in self.all_words if w.lower().startswith(word_lower)]
        contains = [w for w in self.all_words if word_lower in w.lower() and not w.lower().startswith(word_lower)]
        matches = starts_with + contains
        matches = matches[:8]
        if not matches:
            self.height = 0
            self.visible = False
            return
        theme = ThemeManager.get_theme()
        for word in matches:
            btn = Button(text=word, size_hint_x=None, width=len(word) * dp(7) + dp(10), height=dp(18), font_size=dp(13), font_name='SourceBold', background_color=theme['widget_bg'], background_normal='', background_down='', color=theme['text_color'])
            btn.word = word
            btn.bind(on_release=self._on_suggestion_click)
            self.suggestions_box.add_widget(btn)
        self.height = dp(23)
        self.visible = True

    def _on_suggestion_click(self, instance):
        if not self.code_input:
            return
        word = instance.word
        text = self.code_input.text
        cursor_pos = self.code_input.cursor_index()
        start = cursor_pos
        while start > 0 and (text[start - 1].isalnum() or text[start - 1] == '_'):
            start -= 1
        new_text = text[:start] + word + text[cursor_pos:]
        self.code_input.text = new_text
        new_pos = start + len(word)
        try:
            self.code_input.cursor = self.code_input.get_cursor_from_index(new_pos)
        except:
            pass
        self.hide()
        self.code_input.focus = True

    def hide(self):
        self.height = 0
        self.visible = False
        self.suggestions_box.clear_widgets()


class PythonLearningApp(MDApp):
    """Главный класс приложения Python Learning App"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_language = self._load_language()
        self.tr = TRANSLATIONS[self.current_language]
        self.history = []
        self._max_history = 20
        self._popup = None
        self._current_popup_type = None
        self._exit_popup = None
        self.current_input_widget = None
        self.search_popup = None
        self.saved_api_key = ''
        self.current_theme_name = 'dark'
        self.code_executor = CodeExecutor()
        self.tab_manager = TabManager()
        self.tab_manager.app = self
        self._settings_menu = None
        self._current_file = None
        self._last_autosave_time = 0
        self._has_unsaved_changes = False
        self._pending_new_file = False
        self._original_title = "Python Learning App"
        self.title = self._original_title
        self._autosave_file = self._get_autosave_path()
        self._restore_on_start = True
        self._examples_cache = None
        self._examples_loading = False
        self._ui_ready = False
        self._pending_operations = []
        self._cleanup_scheduled = False
        ThemeManager.apply_saved_theme()
        ThemeManager.register(self)
        self._load_api_key_async()

    def _load_language(self):
        try:
            lang_file = os.path.join(os.getcwd(), 'language.txt')
            if os.path.exists(lang_file):
                with open(lang_file, 'r') as f:
                    lang = f.read().strip()
                    if lang in ['ru', 'en']:
                        return lang
        except:
            pass
        try:
            lang = SettingsManager.get_language()
            if lang in ['ru', 'en']:
                return lang
        except:
            pass
        return 'en'

    def build(self):
        self._load_fonts()
        self._request_android_permissions()
        #self._request_permissions()
        self._request_storage_permission()
        Window.keyboard_anim_args = {'d': 0.2, 't': 'in_out_quad'}
        Window.bind(on_key_down=self._keyboard_handler)
        theme = ThemeManager.get_theme()
        main_layout = BoxLayout(orientation='vertical', padding=dp(3), spacing=dp(3))
        with main_layout.canvas.before:
            self.bg_color = Color(*theme['app_bg'])
            self.bg_rect = Rectangle(size=main_layout.size, pos=main_layout.pos)
        main_layout.bind(size=self._update_bg, pos=self._update_bg)
        self.top_bar = self._create_top_bar(theme)
        main_layout.add_widget(self.top_bar)
        self.action_bar = MyActionBar(None)
        self.action_bar.app = self
        main_layout.add_widget(self.action_bar)
        self.symbol_bar = MySymbolScrollBar(None)
        self.symbol_bar.app = self
        main_layout.add_widget(self.symbol_bar)
        tab_bar = self.tab_manager.create_tab_bar(theme)
        main_layout.add_widget(tab_bar)
        Clock.schedule_once(self._apply_saved_syntax_style, 0.5)
        self.autocomplete = AutoCompleteWidget()
        self.autocomplete.code_input = None
        main_layout.add_widget(self.autocomplete)
        tabs_loaded = self.tab_manager.load_all_tabs()
        if not tabs_loaded:
            self.editor = self.tab_manager.add_tab(title=self.tr.get('untitled_tab', 'New'), text="")
            self.code_input = self.editor.text_input
            self.action_bar.text_input = self.code_input
            self.symbol_bar.text_input = self.code_input
            self.autocomplete.code_input = self.code_input
            self._set_initial_empty_lines()
            self._restore_on_start = True
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
            if saved_font in font_files:
                self.code_input.font_name = font_files[saved_font]
            def set_cursor_to_first_line(dt):
                try:
                    if hasattr(self, 'code_input') and self.code_input:
                        self.code_input.cursor = (0, 0)
                        self.code_input.focus = True
                except:
                    pass
            Clock.schedule_once(set_cursor_to_first_line, 0.5)
            Clock.schedule_once(set_cursor_to_first_line, 0.7)
        else:
            self.editor = self.tab_manager.get_active_editor()
            self.code_input = self.editor.text_input
            self.action_bar.text_input = self.code_input
            self.symbol_bar.text_input = self.code_input
            self.autocomplete.code_input = self.code_input
            self._current_file = self.tab_manager.get_active_file()
            self._has_unsaved_changes = False
            self._update_title_saved()
            self._restore_on_start = False
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
            if saved_font in font_files:
                self.code_input.font_name = font_files[saved_font]
            def set_cursor_to_first_line(dt):
                try:
                    if hasattr(self, 'code_input') and self.code_input:
                        self.code_input.cursor = (0, 0)
                        self.code_input.focus = True
                except:
                    pass
            Clock.schedule_once(set_cursor_to_first_line, 0.5)
            Clock.schedule_once(set_cursor_to_first_line, 0.7)
        self.editor_container = BoxLayout()
        self.editor_container.add_widget(self.editor)
        main_layout.add_widget(self.editor_container)
        self._setup_autosave()
        self._ui_ready = True
        self._process_pending_operations()
        main_layout.bind(on_touch_down=self._on_main_touch_down)
        Clock.schedule_once(self._apply_saved_syntax_style, 0.5)
        root_layout = FloatLayout()
        root_layout.add_widget(main_layout)
        from kivymd.uix.label import MDIcon
        from kivy.uix.behaviors import ButtonBehavior
        run_btn_size = dp(67)
        margin_right = dp(8)
        margin_bottom = dp(67)
        class RunButton(ButtonBehavior, FloatLayout):
            pass
        self.run_btn = RunButton(size_hint=(None, None), size=(run_btn_size, run_btn_size))
        self.run_btn.always_release = True
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
        play_icon = MDIcon(icon='play', font_size=f"{dp(23)}sp", theme_text_color="Custom", text_color=icon_color, pos_hint={"center_x": 0.5, "center_y": 0.5})
        self.run_btn.add_widget(play_icon)
        def set_btn_pos(instance, value):
            x = root_layout.width - run_btn_size - margin_right
            y = margin_bottom
            self.run_btn.pos = (x, y)
        root_layout.bind(size=set_btn_pos, pos=set_btn_pos)
        Clock.schedule_once(lambda dt: set_btn_pos(None, None), 0.3)
        self.run_btn.bind(on_press=lambda btn: self.run_code(btn))
        self.run_btn.bind(on_press=lambda btn: print("DEBUG: Run button pressed!"))
        root_layout.add_widget(self.run_btn)
        if platform == 'android':
            def lock_window_position(dt):
                try:
                    Window.top = 0
                    Window.update_viewport()
                except:
                    pass
            Clock.schedule_once(lock_window_position, 0.2)
            Clock.schedule_once(lock_window_position, 0.5)
            Clock.schedule_once(lock_window_position, 1.0)
        Clock.schedule_once(self._fix_layout_on_start, 0.5)
        return root_layout
    
    def _request_android_permissions(self):
        """Запрос разрешений на чистом Android."""
        try:
            from android.permissions import request_permissions, Permission
            request_permissions([
                Permission.READ_EXTERNAL_STORAGE,
                Permission.WRITE_EXTERNAL_STORAGE
            ])
        except:
            pass

    def on_start(self):
        Window.clearcolor = ThemeManager.get_theme()['window_bg']
        self._update_ui_language()
        if self._restore_on_start:
            Clock.schedule_once(self._restore_autosaved_code, 0.3)
        Clock.schedule_once(lambda dt: self._preload_examples(), 0.5)

    def _fix_layout_on_start(self, dt):
        try:
            Window.update_viewport()
            if hasattr(self, 'editor') and self.editor:
                self.editor._update_text_width(0)
        except:
            pass

    def on_pause(self):
        self.tab_manager.save_all_tabs()
        return True

    def on_resume(self):
        pass

    def on_stop(self):
        self.tab_manager.save_all_tabs()
        self._save_autosave()
        if self._has_unsaved_changes and self.code_input.text.strip():
            self._show_exit_confirmation()
            return False
        self._cleanup_resources()
        return True

    def _get_autosave_path(self):
        app_dir = os.getcwd()
        data_dir = os.path.join(app_dir, 'data')
        try:
            os.makedirs(data_dir, exist_ok=True)
        except:
            pass
        return os.path.join(data_dir, 'autosave.py')

    def _load_api_key_async(self):
        def load_key():
            try:
                self.saved_api_key = SettingsManager.get_api_key()
            except:
                self.saved_api_key = ''
        threading.Thread(target=load_key, daemon=True).start()

    def _load_fonts(self):
        """Регистрирует шрифты для корректного отображения символов."""
        try:
            # Системный шрифт Android (всегда доступен)
            SYSTEM_FONT = '/system/fonts/DroidSans.ttf'
            
            LabelBase.register(name='Roboto', fn_regular=SYSTEM_FONT)
            LabelBase.register(name='JetBrainsMono', fn_regular=SYSTEM_FONT)
            LabelBase.register(name='FiraCode', fn_regular=SYSTEM_FONT)
            LabelBase.register(name='CascadiaCode', fn_regular=SYSTEM_FONT)
            LabelBase.register(name='IBMPlexMono', fn_regular=SYSTEM_FONT)
            LabelBase.register(name='NotoSansMono', fn_regular=SYSTEM_FONT)
            LabelBase.register(name='SourceCodePro', fn_regular=SYSTEM_FONT)
            LabelBase.register(name='DroidMono', fn_regular=SYSTEM_FONT)
            # Системный шрифт для основного текста
            cjk_path = '/system/fonts/NotoSansCJK-Regular.ttc'
            if os.path.exists(cjk_path):
                LabelBase.register(name='Roboto', fn_regular=cjk_path)
    
            # Шрифт для спецсимволов
            dejavu_paths = [
                os.path.join(os.getcwd(), 'fonts', 'DejaVuSans.ttf'),
                '/system/fonts/DejaVuSans.ttf',
            ]
            for path in dejavu_paths:
                if os.path.exists(path):
                    LabelBase.register(name='DejaVuSans', fn_regular=path)
                    break
    
            # Запасной системный Roboto
            roboto_path = '/system/fonts/Roboto-Regular.ttf'
            if os.path.exists(roboto_path):
                LabelBase.register(name='SystemRoboto', fn_regular=roboto_path)
    
            # Жирный шрифт для интерфейса
            droid_bold = '/system/fonts/DroidSans-Bold.ttf'
            if os.path.exists(droid_bold):
                LabelBase.register(name='DroidBold', fn_regular=droid_bold)
    
            # Системный моноширинный шрифт (запасной)
            droid_mono = '/system/fonts/DroidSansMono.ttf'
            if os.path.exists(droid_mono):
                LabelBase.register(name='DroidMono', fn_regular=droid_mono)
    
            # JetBrains Mono
            jetbrains_path = os.path.join(os.getcwd(), 'fonts', 'JetBrainsMono.ttf')
            if os.path.exists(jetbrains_path):
                LabelBase.register(name='JetBrainsMono', fn_regular=jetbrains_path)
    
            # Fira Code
            fira_path = os.path.join(os.getcwd(), 'fonts', 'FiraCode-Regular.ttf')
            if os.path.exists(fira_path):
                LabelBase.register(name='FiraCode', fn_regular=fira_path)
    
            # Cascadia Code
            cascadia_path = os.path.join(os.getcwd(), 'fonts', 'CascadiaCode.ttf')
            if os.path.exists(cascadia_path):
                LabelBase.register(name='CascadiaCode', fn_regular=cascadia_path)
    
            # IBM Plex Mono
            ibm_path = os.path.join(os.getcwd(), 'fonts', 'IBMPlexMono-Regular.ttf')
            if os.path.exists(ibm_path):
                LabelBase.register(name='IBMPlexMono', fn_regular=ibm_path)
    
            # Noto Sans Mono
            noto_path = os.path.join(os.getcwd(), 'fonts', 'NotoSansMono.ttf')
            if os.path.exists(noto_path):
                LabelBase.register(name='NotoSansMono', fn_regular=noto_path)
    
            # Source Code Pro
            source_path = os.path.join(os.getcwd(), 'fonts', 'SourceCodePro-Regular.otf')
            if os.path.exists(source_path):
                LabelBase.register(name='SourceCodePro', fn_regular=source_path)
    
        except Exception as e:
            log_error(f"Font error: {e}")

    def _request_permissions(self):
        if ANV_AVAILABLE:
            try:
                request_permissions([Permission.WRITE_EXTERNAL_STORAGE, Permission.READ_EXTERNAL_STORAGE])
            except:
                pass

    def _request_storage_permission(self):
        try:
            from jnius import autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            activity = PythonActivity.mActivity
            permissions = ["android.permission.READ_EXTERNAL_STORAGE", "android.permission.WRITE_EXTERNAL_STORAGE"]
            VERSION = autoclass('android.os.Build$VERSION')
            if VERSION.SDK_INT >= 23:
                activity.requestPermissions(permissions, 1)
        except:
            pass

    def _set_initial_empty_lines(self):
        def set_lines(dt):
            try:
                self.code_input.text = ''
                if hasattr(self, 'editor') and self.editor:
                    self.editor.original_lines = ['']
                    self.editor._update_line_panel()
                self._has_unsaved_changes = False
                self._update_title_saved()
                self.code_input.cursor = (0, 0)
            except:
                pass
        Clock.schedule_once(set_lines, 0.3)

    def _restore_autosaved_code(self, dt):
        try:
            if not os.path.exists(self._autosave_file):
                return
            with open(self._autosave_file, 'r', encoding='utf-8') as f:
                content = f.read()
            if not content or not content.strip():
                return
            try:
                data = json.loads(content)
                if isinstance(data, dict) and 'tabs' in data:
                    tabs_data = data.get('tabs', [])
                    if tabs_data:
                        self.tab_manager.tabs.clear()
                        for tab_info in tabs_data:
                            editor = self.tab_manager.add_tab(title=tab_info.get('title', 'Untitled'), text=tab_info.get('text', ''))
                        active_idx = data.get('active_index', 0)
                        if 0 <= active_idx < len(self.tab_manager.tabs):
                            self.tab_manager.active_index = active_idx
                            self._on_tab_changed(self.tab_manager.get_active_editor())
                        self._has_unsaved_changes = False
                        self._update_title_saved()
                        return
            except (json.JSONDecodeError, ValueError):
                pass
            if hasattr(self, 'editor') and self.editor:
                self.code_input.text = content
                self.editor.original_lines = content.split('\n')
                self.editor._update_line_panel()
            self._has_unsaved_changes = False
            self._update_title_saved()
        except:
            pass

    def _process_pending_operations(self):
        if not self._ui_ready:
            return
        for op in self._pending_operations:
            try:
                op()
            except:
                pass
        self._pending_operations.clear()

    def apply_theme(self, theme):
        self.current_theme_name = theme['name']
        Window.clearcolor = theme['window_bg']
        if hasattr(self, 'bg_color'):
            self.bg_color.rgba = theme['app_bg']
        if hasattr(self, 'spinner'):
            self.spinner.background_color = theme['spinner_bg']
            self.spinner.background_normal = ''
            self.spinner.background_down = ''
            self.spinner.color = theme['spinner_text']
            if hasattr(self.spinner, 'canvas'):
                self.spinner.canvas.ask_update()
        if hasattr(self, 'menu_button'):
            self.menu_button.background_color = theme.get('menu_btn_bg', theme['widget_bg'])
            self.menu_button.background_normal = ''
            self.menu_button.background_down = ''
            self.menu_button.color = theme.get('menu_btn_text', theme['text_color'])
            if hasattr(self.menu_button, 'canvas'):
                self.menu_button.canvas.ask_update()
        if hasattr(self, 'run_btn'):
            bg_color = theme.get('run_btn_bg', (0.85, 0.88, 0.90, 1))
            icon_color = theme.get('run_btn_text', (0.18, 0.18, 0.19, 1))
            def update_bg(btn, *args):
                btn.canvas.before.clear()
                with btn.canvas.before:
                    Color(*bg_color)
                    Ellipse(pos=btn.pos, size=btn.size)
            update_bg(self.run_btn)
            for child in self.run_btn.children:
                if hasattr(child, 'text_color'):
                    child.text_color = icon_color
        if hasattr(self, 'current_input_widget') and self.current_input_widget:
            try:
                self.current_input_widget.background_color = theme['input_bg']
                self.current_input_widget.foreground_color = theme['input_text']
                self.current_input_widget.cursor_color = theme['input_cursor']
            except:
                pass
        if hasattr(self, 'tab_manager'):
            self.tab_manager.update_tab_bar_theme(theme)

    def _update_bg(self, instance, value):
        if hasattr(self, 'bg_rect'):
            self.bg_rect.size = instance.size
            self.bg_rect.pos = instance.pos

    def _update_top_bar_bg(self, instance, value):
        if hasattr(self, 'top_bar_bg_rect'):
            self.top_bar_bg_rect.pos = instance.pos
            self.top_bar_bg_rect.size = instance.size

    def _on_main_touch_down(self, instance, touch):
        if hasattr(self, 'editor') and hasattr(self.editor, 'text_input'):
            editor = self.editor.text_input
            if not editor.collide_point(*touch.pos):
                editor.focus = False
                if hasattr(self.editor, '_keyboard_visible'):
                    self.editor._keyboard_visible = False
        return False

    def _apply_saved_syntax_style(self, dt):
        try:
            saved_style = SyntaxStyleManager.get_current_style()
            if hasattr(self, 'tab_manager'):
                SyntaxStyleManager.apply_style_to_all_tabs(self.tab_manager, saved_style)
        except:
            pass

    def _create_top_bar(self, theme):
        top_bar = BoxLayout(size_hint_y=0.10, spacing=0, padding=[dp(3), dp(3), dp(3), dp(3)])
        with top_bar.canvas.before:
            Color(*theme.get('top_bar_bg', theme['widget_bg']))
            self.top_bar_bg_rect = Rectangle(pos=top_bar.pos, size=top_bar.size)
        top_bar.bind(pos=self._update_top_bar_bg, size=self._update_top_bar_bg)
        self.spinner = ThemedSpinner(text=self.tr.get('examples', 'Examples'), values=self._get_example_titles(), size_hint_x=0.70, background_color=theme['spinner_bg'], background_normal='', background_down='', color=theme['spinner_text'], font_size=dp(18), font_name='SourceBold', dropdown_bg=theme['spinner_dropdown_bg'], dropdown_text_color=theme['spinner_dropdown_text'], dropdown_selected_bg=theme['spinner_dropdown_selected_bg'])
        self.spinner.bind(text=self.load_example)
        self.spinner.bind(on_press=self._update_spinner_dropdown_colors)
        menu_anchor = AnchorLayout(anchor_x='right', anchor_y='center', size_hint_x=0.15)
        self.menu_button = Button(text='☰', font_name='DejaVuSans', size_hint=(None, 1), width=dp(60), background_color=theme.get('menu_btn_bg', theme['widget_bg']), background_normal='', background_down='', color=theme.get('menu_btn_text', theme['text_color']), font_size=dp(23), bold=True)
        self.menu_button.bind(on_release=self.show_context_menu)
        menu_anchor.add_widget(self.menu_button)
        top_bar.add_widget(self.spinner)
        top_bar.add_widget(menu_anchor)
        return top_bar

    def _get_example_titles(self):
        tr = self.tr
        return [tr['example_1'], tr['example_2'], tr['example_3'], tr['example_4'], tr['example_5'], tr['example_6'], tr['example_7'], tr['example_8'], tr['example_9'], tr['example_10'], tr['example_11'], tr['example_12'], tr['example_13'], tr['example_14'], tr['example_15'], tr['example_16'], tr['example_17'], tr['example_18']]

    def _update_spinner_dropdown_colors(self, instance):
        theme = ThemeManager.get_theme()
        if hasattr(self, 'spinner'):
            self.spinner.dropdown_bg = theme['spinner_dropdown_bg']
            self.spinner.dropdown_text_color = theme['spinner_dropdown_text']
            self.spinner.dropdown_selected_bg = theme['spinner_dropdown_selected_bg']

    def show_context_menu(self, instance):
        theme = ThemeManager.get_theme()
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

    def menu_action(self, button, func):
        if hasattr(self, '_menu_dropdown'):
            self._menu_dropdown.dismiss()
        func(None)

    def _create_menu_items(self, theme):
        self._menu_dropdown.clear_widgets()
        tr = self.tr
        if hasattr(self._menu_dropdown, 'container'):
            container = self._menu_dropdown.container
            container.canvas.before.clear()
            with container.canvas.before:
                Color(*theme.get('action_bar_bg', theme['widget_bg']))
                Rectangle(pos=container.pos, size=container.size)
            container.bind(pos=lambda inst, val: self._update_menu_container_bg(inst, theme), size=lambda inst, val: self._update_menu_container_bg(inst, theme))
        menu_items = [('file-plus', tr['new'], self.new_file), ('folder-open', tr['load'], self.show_load_dialog), ('content-save', tr['save'], self.show_save_dialog), ('magnify', tr['find'], self.show_search_only_dialog), ('find-replace', tr['find_replace'], self.show_search_replace_dialog), ('history', tr['history'], self.show_history), ('code-tags', tr['format'], self.format_code), ('robot', tr['ai_assistant'], self.show_ai_assistant), ('cog', tr['settings'], self._open_settings_menu)]
        from kivymd.uix.label import MDIcon
        from kivy.uix.behaviors import ButtonBehavior
        btn_bg = theme.get('action_bar_bg', theme['widget_bg'])
        for icon_name, text, func in menu_items:
            class MenuItem(ButtonBehavior, BoxLayout):
                pass
            box = MenuItem(orientation='horizontal', size_hint_y=None, height=dp(35), padding=(dp(8), 0), spacing=dp(5))
            icon = MDIcon(icon=icon_name, font_size=f"{dp(10)}sp", theme_text_color="Custom", text_color=theme['text_color'], size_hint_x=None, width=dp(17))
            box.add_widget(icon)
            lbl = Label(text=text, color=theme['text_color'], font_size=dp(15), font_name='SourceBold', halign='left', valign='middle')
            box.add_widget(lbl)
            box.canvas.before.clear()
            with box.canvas.before:
                Color(*btn_bg)
                Rectangle(pos=box.pos, size=box.size)
                Color(btn_bg[0] + 0.08, btn_bg[1] + 0.08, btn_bg[2] + 0.08, 1)
                Line(rectangle=(box.pos[0], box.pos[1], box.size[0], box.size[1]), width=dp(0.5))
            box.bind(pos=lambda inst, val, bg=btn_bg: self._update_menu_btn_bg(inst, bg), size=lambda inst, val, bg=btn_bg: self._update_menu_btn_bg(inst, bg))
            box.bind(on_release=lambda bt, f=func: self.menu_action(bt, f))
            self._menu_dropdown.add_widget(box)
        self._menu_dropdown.width = dp(167)

    def _update_menu_container_bg(self, instance, theme):
        if not hasattr(instance, 'canvas'):
            return
        instance.canvas.before.clear()
        with instance.canvas.before:
            Color(*theme.get('action_bar_bg', theme['widget_bg']))
            Rectangle(pos=instance.pos, size=instance.size)

    def _update_menu_btn_bg(self, instance, bg_color):
        if not hasattr(instance, 'canvas'):
            return
        instance.canvas.before.clear()
        with instance.canvas.before:
            Color(*bg_color)
            Rectangle(pos=instance.pos, size=instance.size)
            Color(bg_color[0] + 0.08, bg_color[1] + 0.08, bg_color[2] + 0.08, 1)
            Line(rectangle=(instance.pos[0], instance.pos[1], instance.size[0], instance.size[1]), width=dp(0.5))

    def _on_tab_changed(self, new_editor):
        self.editor_container.clear_widgets()
        self.editor = new_editor
        self.code_input = new_editor.text_input
        self.editor_container.add_widget(new_editor)
        self.action_bar.text_input = self.code_input
        self.symbol_bar.text_input = self.code_input
        self.autocomplete.code_input = self.code_input
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
        if saved_font in font_files:
            self.code_input.font_name = font_files[saved_font]
        self._setup_autosave()
        self._current_file = self.tab_manager.get_active_file()
        self._has_unsaved_changes = False
        self._update_title_saved()
        Clock.schedule_once(self._autosave_tabs, 1)
        def set_cursor_to_first_line(dt):
            try:
                if hasattr(self, 'code_input') and self.code_input:
                    self.code_input.cursor = (0, 0)
                    self.code_input.focus = True
            except:
                pass
        Clock.schedule_once(set_cursor_to_first_line, 0.5)
        Clock.schedule_once(set_cursor_to_first_line, 0.7)

    def _autosave_tabs(self, dt=None):
        try:
            self.tab_manager.save_all_tabs()
        except:
            pass
    
    def _setup_autosave(self):
        self._last_autosave_time = 0
        self.code_input.unbind(text=self._on_code_change_for_autosave)
        self.code_input.bind(text=self._on_code_change_for_autosave)
    
    def _on_code_change_for_autosave(self, instance, value):
        self.tab_manager.mark_active_unsaved()
        is_empty = all(line.strip() == '' for line in value.split('\n')) if value else True
        if not self._has_unsaved_changes and not is_empty:
            self._has_unsaved_changes = True
            self._update_title_with_unsaved()
        elif self._has_unsaved_changes and is_empty and value:
            self._has_unsaved_changes = False
            self._update_title_saved()
        current_time = time.time()
        if current_time - self._last_autosave_time > 2:
            self._last_autosave_time = current_time
            Clock.unschedule(self._do_autosave)
            Clock.unschedule(self._autosave_tabs)
            Clock.schedule_once(self._do_autosave, 3)
            Clock.schedule_once(self._autosave_tabs, 3)
    
    def _do_autosave(self, dt):
        self._last_autosave_time = time.time()
        self._save_autosave()
        if hasattr(self, '_current_file') and self._current_file:
            try:
                with open(self._current_file, 'w', encoding='utf-8') as f:
                    f.write(self.code_input.text)
                self._has_unsaved_changes = False
                self._update_title_saved()
            except:
                pass
    
    def _save_autosave(self):
        try:
            tabs_data = {'active_index': self.tab_manager.active_index, 'tabs': []}
            for tab in self.tab_manager.tabs:
                tabs_data['tabs'].append({'title': tab['title'], 'file': tab['file'], 'text': tab['editor'].get_text() if tab['editor'] else ''})
            dir_path = os.path.dirname(self._autosave_file)
            os.makedirs(dir_path, exist_ok=True)
            with open(self._autosave_file, 'w', encoding='utf-8') as f:
                json.dump(tabs_data, f, indent=2)
        except:
            pass
    
    def _update_title_with_unsaved(self):
        if self._current_file:
            filename = os.path.basename(self._current_file)
            self.title = f"*{filename} - {self._original_title}"
        else:
            self.title = f"*Untitled - {self._original_title}"
    
    def _update_title_saved(self):
        self._has_unsaved_changes = False
        if self._current_file:
            filename = os.path.basename(self._current_file)
            self.title = f"{filename} - {self._original_title}"
        else:
            self.title = self._original_title
    
    def new_file(self, instance=None):
        if self._has_unsaved_changes and self.code_input.text.strip():
            self._pending_new_file = True
            self._show_new_file_confirmation()
            return
        self._do_new_file()
    
    def _do_new_file(self):
        self.code_input.text = ''
        self._current_file = None
        self._has_unsaved_changes = False
        self._update_title_saved()
        if hasattr(self, 'editor') and self.editor:
            self.editor.original_lines = ['']
            self.editor._update_line_panel()
        def set_cursor(dt):
            try:
                self.code_input.cursor = (0, 0)
                self.code_input.focus = True
            except:
                pass
        Clock.schedule_once(set_cursor, 0.5)
        Clock.schedule_once(set_cursor, 0.7)
        self.show_result_popup(self.tr.get('new_file_created', '✓ New file created'))
    
    def show_save_dialog(self, instance=None):
        theme = ThemeManager.get_theme()
        popup = Popup(title=self.tr.get('save', 'Save'), title_color=theme['popup_title'],background='', background_color=theme.get('popup_bg', (1.0, 1.0, 1.0, 1)), size_hint=(0.92, 0.85), auto_dismiss=False)
        content = FileDialog(callback=self.save_file, cancel=self.dismiss_popup, is_save=True, popup=popup)
        popup.content = content
        self._popup = popup
        self._current_popup_type = 'save'
        popup.open()
    
    def save_file(self, path, filename):
        tr = self.tr
        try:
            if not filename or not filename.strip():
                filename = 'script.py'
            if not filename.endswith('.py'):
                filename += '.py'
            filename = filename.strip()
            invalid_chars = '<>:"/\\|?*'
            for char in invalid_chars:
                filename = filename.replace(char, '_')
            if not os.path.exists(path):
                os.makedirs(path, exist_ok=True)
            full_path = os.path.join(path, filename)
            if os.path.exists(full_path):
                self._confirm_overwrite(full_path)
                return
            self._do_save_file(full_path, filename)
        except PermissionError:
            self.show_result_popup(tr.get('error_save', 'X Error') + ': ' + tr.get('no_permission', 'No permission'))
        except Exception as e:
            self.show_result_popup(tr.get('error_save', 'X Error') + f':\n{e}')
    
    def _do_save_file(self, full_path, filename):
        try:
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(self.code_input.text)
            self._current_file = full_path
            self._has_unsaved_changes = False
            self._update_title_saved()
            self.tab_manager.set_active_file(full_path)
            self.show_result_popup(f"✓ {self.tr.get('file_saved', 'Saved')}:\n{filename}")
        except Exception as e:
            self.show_result_popup(f"X {self.tr.get('error_save', 'Error')}:\n{e}")
    
    def show_load_dialog(self, instance=None):
        theme = ThemeManager.get_theme()
        popup = Popup(title=self.tr.get('open', 'Open'), title_color=theme['popup_title'],background='', background_color=theme.get('popup_bg', (1.0, 1.0, 1.0, 1)), size_hint=(0.92, 0.85), auto_dismiss=False)
        content = FileDialog(callback=self.load_file, cancel=self.dismiss_popup, is_save=False, popup=popup)
        popup.content = content
        self._popup = popup
        self._current_popup_type = 'load'
        popup.open()
    
    def load_file(self, selection):
        tr = self.tr
        if not selection:
            return
        file_path = selection[0]
        try:
            file_size = os.path.getsize(file_path)
            if file_size > 1_000_000:
                self._load_large_file(file_path, file_size)
                return
            content = self._read_file_content(file_path)
            if content is None:
                self.show_result_popup(tr.get('encoding_error', 'X Cannot determine encoding'))
                return
            self._apply_loaded_content(content, file_path)
            filename = os.path.basename(file_path)
            self.show_result_popup(tr.get('file_loaded', '✓ Loaded') + f':\n{filename}')
        except Exception as e:
            self.show_result_popup(tr.get('error_load', 'X Error') + f':\n{e}')
    
    def _read_file_content(self, file_path):
        with open(file_path, 'rb') as f:
            raw_start = f.read(4)
        if raw_start.startswith(b'\xef\xbb\xbf'):
            encoding = 'utf-8-sig'
        elif raw_start.startswith(b'\xff\xfe'):
            encoding = 'utf-16-le'
        elif raw_start.startswith(b'\xfe\xff'):
            encoding = 'utf-16-be'
        elif raw_start.startswith(b'\x00\x00\xfe\xff'):
            encoding = 'utf-32-be'
        elif raw_start.startswith(b'\xff\xfe\x00\x00'):
            encoding = 'utf-32-le'
        else:
            encoding = 'utf-8'
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            pass
        for encoding in ['cp1251', 'latin-1', 'windows-1251']:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
        return None
    
    def _load_large_file(self, file_path, file_size):
        tr = self.tr
        self.show_result_popup(tr.get('file_too_big', '! Большой файл') + f' ({file_size // 1024} KB)\nЗагрузка...')
        def load_in_background():
            try:
                content = self._read_file_content(file_path)
                if content is None:
                    Clock.schedule_once(lambda dt: self.show_result_popup(tr.get('encoding_error', 'X Cannot determine encoding')))
                    return
                Clock.schedule_once(lambda dt: self._apply_loaded_content(content, file_path))
                filename = os.path.basename(file_path)
                Clock.schedule_once(lambda dt: self.show_result_popup(tr.get('file_loaded', '✓ Loaded') + f':\n{filename}'))
            except Exception as e:
                Clock.schedule_once(lambda dt: self.show_result_popup(tr.get('error_load', 'X Error') + f':\n{e}'))
        threading.Thread(target=load_in_background, daemon=True).start()
    
    def _apply_loaded_content(self, content, file_path):
        self.code_input.text = content
        self._current_file = file_path
        if hasattr(self, 'editor') and self.editor:
            self.editor.original_lines = content.split('\n')
            if hasattr(self.editor, '_cached_max_line_length'):
                del self.editor._cached_max_line_length
            if hasattr(self.editor, '_cached_max_line_index'):
                del self.editor._cached_max_line_index
            self.editor._update_line_panel()
            Clock.schedule_once(self.editor._update_text_width, 0.1)
        self._has_unsaved_changes = False
        self._update_title_saved()
        self.tab_manager.set_active_file(file_path)
    
    def _show_exit_confirmation(self):
        tr = self.tr
        theme = ThemeManager.get_theme()
        content = BoxLayout(orientation='vertical', padding=dp(7), spacing=dp(5))
        message = tr.get('unsaved_changes', 'You have unsaved changes.')
        if self._current_file:
            message += f"\n{tr.get('save_before_exit', 'Save before exit?')} '{os.path.basename(self._current_file)}'?"
        else:
            message += "\n" + tr.get('save_before_exit', 'Save before exit?')
        content.add_widget(Label(text=message, color=theme['text_color'], font_size=dp(11), font_name='SourceBold', halign='center', size_hint_y=None, height=dp(33)))
        btn_layout = BoxLayout(size_hint_y=None, height=dp(23), spacing=dp(4))
        popup = Popup(title=tr.get('exit_title', 'Exit'), title_color=theme['popup_title'],background='', background_color=theme.get('popup_bg', (1.0, 1.0, 1.0, 1)), content=content, size_hint=(0.85, 0.35), auto_dismiss=False)
        btn_save = Button(text=tr.get('save_and_exit', 'Save & Exit'), font_name='SourceBold', background_color=(0.2, 0.5, 0.2, 1), background_normal='', background_down='', color=theme['text_color'], font_size=dp(10), on_release=lambda x: self._on_exit_save(popup))
        btn_exit = Button(text=tr.get('exit_without_save', 'Exit'), font_name='SourceBold', background_color=(0.5, 0.2, 0.2, 1), background_normal='', background_down='', color=theme['text_color'], font_size=dp(10), on_release=lambda x: self._on_exit_force(popup))
        btn_cancel = Button(text=tr.get('cancel', 'Cancel'), font_name='SourceBold', background_color=theme['widget_bg'], background_normal='', background_down='', color=theme['text_color'], font_size=dp(10), on_release=lambda x: popup.dismiss())
        btn_layout.add_widget(btn_save)
        btn_layout.add_widget(btn_exit)
        btn_layout.add_widget(btn_cancel)
        content.add_widget(btn_layout)
        popup.open()
        self._exit_popup = popup
    
    def _on_exit_save(self, popup):
        popup.dismiss()
        if self._current_file:
            self._do_save_file(self._current_file, os.path.basename(self._current_file))
        else:
            self._save_before_exit()
        Clock.schedule_once(lambda dt: self._force_exit(), 0.5)
    
    def _on_exit_force(self, popup):
        popup.dismiss()
        self._force_exit()
    
    def _show_new_file_confirmation(self):
        tr = self.tr
        theme = ThemeManager.get_theme()
        content = BoxLayout(orientation='vertical', padding=dp(7), spacing=dp(5))
        content.add_widget(Label(text=tr.get('new_file_confirm', 'Create without saving?'), color=theme['text_color'], font_size=dp(11), font_name='SourceBold', halign='center', size_hint_y=None, height=dp(27)))
        btn_layout = BoxLayout(size_hint_y=None, height=dp(23), spacing=dp(4))
        popup = Popup(title=tr.get('confirm_title', 'Confirm'), title_color=theme['popup_title'],background='', background_color=theme.get('popup_bg', (1.0, 1.0, 1.0, 1)), content=content, size_hint=(0.8, 0.3), auto_dismiss=False)
        btn_yes = Button(text=tr.get('yes', 'Yes'), font_name='SourceBold', background_color=(0.2, 0.5, 0.2, 1), background_normal='', background_down='', color=theme['text_color'], font_size=dp(10), on_release=lambda x: self._on_new_file_confirm(popup))
        btn_no = Button(text=tr.get('no', 'No'), font_name='SourceBold', background_color=theme['widget_bg'], background_normal='', background_down='', color=theme['text_color'], font_size=dp(10), on_release=lambda x: popup.dismiss())
        btn_layout.add_widget(btn_yes)
        btn_layout.add_widget(btn_no)
        content.add_widget(btn_layout)
        popup.open()
    
    def _on_new_file_confirm(self, popup):
        popup.dismiss()
        self._do_new_file()
        self._pending_new_file = False
    
    def _confirm_overwrite(self, full_path):
        tr = self.tr
        theme = ThemeManager.get_theme()
        filename = os.path.basename(full_path)
        content = BoxLayout(orientation='vertical', padding=dp(7), spacing=dp(5))
        content.add_widget(Label(text=f"{tr.get('file_exists', 'File')} '{filename}' {tr.get('already_exists', 'exists')}.\n{tr.get('overwrite_confirm', 'Overwrite?')}", color=theme['text_color'], font_size=dp(11), font_name='SourceBold', halign='center', size_hint_y=None, height=dp(27)))
        btn_layout = BoxLayout(size_hint_y=None, height=dp(23), spacing=dp(4))
        popup = Popup(title=tr.get('confirm_title', 'Confirm'), title_color=theme['popup_title'],background='', background_color=theme.get('popup_bg', (1.0, 1.0, 1.0, 1)), content=content, size_hint=(0.8, 0.35), auto_dismiss=False)
        btn_yes = Button(text=tr.get('yes', 'Yes'), font_name='SourceBold', background_color=(0.2, 0.5, 0.2, 1), background_normal='', background_down='', color=theme['text_color'], font_size=dp(10), on_release=lambda x: self._on_overwrite_confirm(popup, full_path, filename))
        btn_no = Button(text=tr.get('no', 'No'), font_name='SourceBold', background_color=theme['widget_bg'], background_normal='', background_down='', color=theme['text_color'], font_size=dp(10), on_release=lambda x: popup.dismiss())
        btn_layout.add_widget(btn_yes)
        btn_layout.add_widget(btn_no)
        content.add_widget(btn_layout)
        popup.open()
    
    def _on_overwrite_confirm(self, popup, full_path, filename):
        popup.dismiss()
        self._do_save_file(full_path, filename)
    
    def _save_before_exit(self):
        try:
            save_path = '/storage/emulated/0/Download'
            if ANV_AVAILABLE and androidstorage:
                try:
                    save_path = androidstorage.get_external_storage_path() + '/Download'
                except:
                    pass
            os.makedirs(save_path, exist_ok=True)
            filename = f"script_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
            full_path = os.path.join(save_path, filename)
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(self.code_input.text)
            self._current_file = full_path
        except:
            pass
    
    def _force_exit(self):
        self._cleanup_resources()
        App.get_running_app().stop()
    
    def _cleanup_resources(self):
        if self._cleanup_scheduled:
            return
        self._cleanup_scheduled = True
        self.history.clear()
        self.dismiss_popup()
        if self._exit_popup:
            try:
                self._exit_popup.dismiss()
            except:
                pass
        if hasattr(self, 'action_bar') and hasattr(self.action_bar, 'cleanup'):
            self.action_bar.cleanup()
        if hasattr(self, 'symbol_bar') and hasattr(self.symbol_bar, 'cleanup'):
            self.symbol_bar.cleanup()
        ThemeManager.unregister(self)
    
    def run_code(self, instance):
        tr = self.tr
        code = self.code_input.text        
        if not code.strip():
            self.show_result_popup(tr.get('enter_code', 'X Enter code'))
            return
        instance.disabled = True
        
        def input_handler(prompt=""):
            return self._handle_input(prompt)
        
        def result_callback(result):
            instance.disabled = False
            self._show_result(result)
        
        if not self.code_executor.run(code, input_handler, result_callback):
            instance.disabled = False
    
    def _handle_input(self, prompt=""):
        tr = self.tr
        self.code_executor.clear_input()
        input_result = [None]
        input_event = threading.Event()
        
        def show_popup(dt):
            theme = ThemeManager.get_theme()
            content = BoxLayout(orientation='vertical', padding=dp(5), spacing=dp(4))
            content.add_widget(Label(text=prompt or tr.get('input_prompt', 'Enter value:'), color=theme['text_color'], font_size=dp(14), font_name='SourceBold', size_hint_y=None, height=dp(25)))
            text_input = TextInput(multiline=False, font_size=dp(14), font_name='SourceBold', background_color=theme['input_bg'], foreground_color=theme['input_text'], cursor_color=theme['input_cursor'], hint_text=tr.get('input_hint', 'Enter text...'), hint_text_color=theme['hint_text'], size_hint_y=None, height=dp(35), padding=(dp(5), dp(5)))
            self.current_input_widget = text_input
            content.add_widget(text_input)
            buttons = BoxLayout(size_hint_y=None, height=dp(30), spacing=dp(5))
            
            def on_ok(*args):
                value = text_input.text.strip()
                input_result[0] = value if value else ""
                self.code_executor.provide_input(value if value else "")
                self.current_input_widget = None
                popup.dismiss()
                input_event.set()
            
            def on_cancel(*args):
                input_result[0] = ""
                self.code_executor.provide_input("")
                self.current_input_widget = None
                popup.dismiss()
                input_event.set()
            
            btn_cancel = Button(text=tr.get('cancel', 'Cancel'), font_name='SourceBold', background_color=theme['widget_bg'], background_normal='', background_down='', color=theme['text_color'], font_size=dp(12), on_release=on_cancel)
            btn_ok = Button(text=tr.get('ok', 'OK'), font_name='SourceBold', background_color=theme['widget_bg'], background_normal='', background_down='', color=theme['text_color'], font_size=dp(12), on_release=on_ok)
            buttons.add_widget(btn_cancel)
            buttons.add_widget(btn_ok)
            content.add_widget(buttons)
            popup = Popup(title=tr.get('input_title', 'Input'), title_color=theme['popup_title'],background='', background_color=theme.get('popup_bg', (1.0, 1.0, 1.0, 1)), content=content, size_hint=(0.93, 0.45), pos_hint={'top': 0.95}, auto_dismiss=False)
            popup.bind(on_dismiss=lambda *args: input_event.set())
            popup.open()
            
            def focus_input(dt):
                if text_input and text_input.parent:
                    text_input.focus = True
            Clock.schedule_once(focus_input, 0.3)
        
        Clock.schedule_once(show_popup, 0.1)
        input_event.wait(timeout=180)
        return input_result[0] if input_result[0] is not None else ""
    
    def _show_result(self, result):
        self.history.append({"time": datetime.now().strftime("%H:%M:%S"), "out": result})
        if len(self.history) > self._max_history:
            self.history = self.history[-self._max_history:]
        self.show_result_popup(result)


    def load_example(self, spinner, text):
        if not text or text == self.tr.get('examples', 'Examples'):
            return
        examples = self._examples_cache if self._examples_cache else self._build_examples()
        example_map = {'1. Hello World': '1. Hello World', '2. Variables': '2. Переменные', '2. Переменные': '2. Переменные', '3. Input': '3. Ввод данных', '3. Ввод': '3. Ввод данных', '4. Conditions': '4. Условия', '4. Условия': '4. Условия', '5. For Loop': '5. Цикл For', '5. Цикл For': '5. Цикл For', '6. While Loop': '6. Цикл While', '6. Цикл While': '6. Цикл While', '7. Lists': '7. Списки', '7. Списки': '7. Списки', '8. List Comprehensions': '8. Генераторы списков', '8. Генераторы списков': '8. Генераторы списков', '9. Dictionaries': '9. Словари', '9. Словари': '9. Словари', '10. Functions': '10. Функции', '10. Функции': '10. Функции', '11. Lambda': '11. Lambda', '12. Classes': '12. Классы', '12. Классы': '12. Классы', '13. Inheritance': '13. Наследование', '13. Наследование': '13. Наследование', '14. Errors': '14. Ошибки', '14. Ошибки': '14. Ошибки', '15. Files': '15. Файлы', '15. Файлы': '15. Файлы', '16. Recursion': '16. Рекурсия', '16. Рекурсия': '16. Рекурсия', '17. Generators': '17. Генераторы', '17. Генераторы': '17. Генераторы', '18. Decorators': '18. Декораторы', '18. Декораторы': '18. Декораторы'}
        key = example_map.get(text, text)
        code = examples.get(key, '# Example not found')
        self.code_input.text = code
        if hasattr(self, 'editor') and self.editor:
            self.editor.original_lines = code.split('\n')
            self.editor._update_line_panel()
            Clock.schedule_once(self.editor._update_text_width, 0.1)
        self._current_file = None
        self._has_unsaved_changes = False
        self._update_title_saved()

    def _preload_examples(self):
        if self._examples_loading:
            return
        self._examples_loading = True
        def load_examples():
            self._examples_cache = self._build_examples()
            self._examples_loading = False
        threading.Thread(target=load_examples, daemon=True).start()

    def _build_examples(self):
        lang = self.current_language
        if lang == 'en':
            return {
                '1. Hello World': '''# My first program
print("Hello, World!")
print("I am learning Python!")''',

                '2. Переменные': '''# Create variables
name = "Alice"
age = 25
height = 1.68

print("Name:", name)
print("Age:", age)
print("Height:", height)

# Change value
age = age + 1
print("Next year will be:", age)''',

                '3. Ввод данных': '''# Program asks your name
name = input("What is your name? ")
print("Hello,", name + "!")

# Ask age
age_str = input("How old are you? ")
if age_str.strip():
    age = int(age_str)
    print("Next year you will be", age + 1)
else:
    print("You didn't enter age")''',

                '4. Условия': '''# Check grade
grade = 85

if grade >= 90:
    print("Excellent! Grade A")
elif grade >= 80:
    print("Good! Grade B")
elif grade >= 70:
    print("Satisfactory! Grade C")
else:
    print("Need to study more")

# Age check
age = 18
if age >= 18:
    print("You can drive a car")
else:
    print("Too early to drive")''',

                '5. Цикл For': '''# Count from 1 to 5
print("Count from 1 to 5:")
for i in range(1, 6):
    print("Number:", i)

# Shopping list
items = ["bread", "milk", "eggs"]
print("\\nNeed to buy:")
for item in items:
    print("-", item)''',

                '6. Цикл While': '''# Count to 5
counter = 1
while counter <= 5:
    print("Counter:", counter)
    counter = counter + 1

# Sum of numbers
total = 0
num = 1
while num <= 10:
    total = total + num
    num = num + 1
print("Sum 1-10 =", total)''',

                '7. Списки': '''# Create list of numbers
numbers = [1, 2, 3, 4, 5]
print("List:", numbers)

# Add element
numbers.append(6)
print("Added 6:", numbers)

# Remove element
numbers.remove(3)
print("Removed 3:", numbers)

# List length
print("List length:", len(numbers))''',

                '8. Генераторы списков': '''# Squares of numbers
squares = [x**2 for x in range(1, 6)]
print("Squares 1-5:", squares)

# Only even numbers
evens = [x for x in range(1, 11) if x % 2 == 0]
print("Evens 1-10:", evens)''',

                '9. Словари': '''# Person info
person = {
    "name": "Alice",
    "age": 25,
    "city": "Moscow"
}

print("Name:", person["name"])
print("Age:", person["age"])

# Add new field
person["email"] = "alice@mail.ru"
print("Email added")''',

                '10. Функции': '''# Greeting function
def greet(name):
    return "Hello, " + name + "!"

# Call function
print(greet("Alice"))
print(greet("Bob"))

# Addition function
def add(a, b):
    return a + b

print("5 + 3 =", add(5, 3))''',

                '11. Lambda': '''# Short function
square = lambda x: x ** 2
print("5^2 =", square(5))

# Multiplication
multiply = lambda x, y: x * y
print("3 * 4 =", multiply(3, 4))''',

                '12. Классы': '''# Create Dog class
class Dog:
    def __init__(self, name):
        self.name = name
    
    def bark(self):
        return self.name + " says: Woof!"

# Create a dog
my_dog = Dog("Buddy")
print(my_dog.bark())''',

                '13. Наследование': '''# Base class
class Animal:
    def __init__(self, name):
        self.name = name

# Inherit from Animal
class Cat(Animal):
    def meow(self):
        return self.name + " says: Meow!"

cat = Cat("Murka")
print(cat.meow())''',

                '14. Ошибки': '''# Error handling
try:
    num = int(input("Enter a number: "))
    print("10 /", num, "=", 10 / num)
except ValueError:
    print("That's not a number!")
except ZeroDivisionError:
    print("Cannot divide by zero!")''',

                '15. Файлы': '''# Write to file
with open("test.txt", "w") as f:
    f.write("Hello, World!\\n")
    f.write("This is my file")
print("File created!")

# Read file
with open("test.txt", "r") as f:
    text = f.read()
print("Contents:")
print(text)''',

                '16. Рекурсия': '''# Factorial via recursion
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)

print("5! =", factorial(5))
print("7! =", factorial(7))''',

                '17. Генераторы': '''# Countdown generator
def countdown(n):
    while n > 0:
        yield n
        n -= 1

print("Countdown from 5:")
for num in countdown(5):
    print(num, end=" ")''',

                '18. Декораторы': '''# Timer decorator
import time

def measure_time(func):
    def wrapper():
        start = time.time()
        func()
        end = time.time()
        print(f"\\nTime: {end - start:.2f} sec")
    return wrapper

@measure_time
def pause():
    time.sleep(2)
    print("Done!")

pause()'''
            }
        else:
            return {
                '1. Hello World': '''# Моя первая программа
print("Привет, мир!")
print("Я учу Python!")''',

                '2. Переменные': '''# Создаем переменные
имя = "Алиса"
возраст = 25
рост = 1.68

print("Имя:", имя)
print("Возраст:", возраст)
print("Рост:", рост)

# Меняем значение
возраст = возраст + 1
print("В следующем году будет:", возраст)''',

                '3. Ввод данных': '''# Программа спрашивает ваше имя
имя = input("Как вас зовут? ")
print("Привет,", имя + "!")

# Спрашиваем возраст
возраст_стр = input("Сколько вам лет? ")
if возраст_стр.strip():
    возраст = int(возраст_стр)
    print("Через год вам будет", возраст + 1)
else:
    print("Вы не ввели возраст")''',

                '4. Условия': '''# Проверяем оценку
оценка = 85

if оценка >= 90:
    print("Отлично! Оценка A")
elif оценка >= 80:
    print("Хорошо! Оценка B")
elif оценка >= 70:
    print("Удовлетворительно! Оценка C")
else:
    print("Нужно подучить")

# Проверка возраста
возраст = 18
if возраст >= 18:
    print("Можно водить машину")
else:
    print("Ещё рано водить")''',

                '5. Цикл For': '''# Считаем от 1 до 5
print("Счет от 1 до 5:")
for i in range(1, 6):
    print("Число:", i)

# Список покупок
покупки = ["хлеб", "молоко", "яйца"]
print("\\nНужно купить:")
for товар in покупки:
    print("-", товар)''',

                '6. Цикл While': '''# Считаем до 5
счетчик = 1
while счетчик <= 5:
    print("Счетчик:", счетчик)
    счетчик = счетчик + 1

# Сумма чисел
сумма = 0
число = 1
while число <= 10:
    сумма = сумма + число
    число = число + 1
print("Сумма 1-10 =", сумма)''',

                '7. Списки': '''# Создаем список чисел
числа = [1, 2, 3, 4, 5]
print("Список:", числа)

# Добавляем элемент
числа.append(6)
print("Добавили 6:", числа)

# Удаляем элемент
числа.remove(3)
print("Удалили 3:", числа)

# Длина списка
print("Длина списка:", len(числа))''',

                '8. Генераторы списков': '''# Квадраты чисел
квадраты = [x**2 for x in range(1, 6)]
print("Квадраты 1-5:", квадраты)

# Только четные числа
четные = [x for x in range(1, 11) if x % 2 == 0]
print("Четные 1-10:", четные)''',

                '9. Словари': '''# Информация о человеке
человек = {
    "имя": "Алиса",
    "возраст": 25,
    "город": "Москва"
}

print("Имя:", человек["имя"])
print("Возраст:", человек["возраст"])

# Добавляем новое поле
человек["email"] = "alice@mail.ru"
print("Email добавлен")''',

                '10. Функции': '''# Функция приветствия
def приветствие(имя):
    return "Привет, " + имя + "!"

# Вызываем функцию
print(приветствие("Алиса"))
print(приветствие("Боб"))

# Функция сложения
def сложить(a, b):
    return a + b

print("5 + 3 =", сложить(5, 3))''',

                '11. Lambda': '''# Короткая функция
квадрат = lambda x: x ** 2
print("5^2 =", квадрат(5))

# Умножение
умножить = lambda x, y: x * y
print("3 * 4 =", умножить(3, 4))''',

                '12. Классы': '''# Создаем класс Собака
class Собака:
    def __init__(self, имя):
        self.имя = имя
    
    def гав(self):
        return self.имя + " говорит: Гав!"

# Создаем собаку
мой_пес = Собака("Бобик")
print(мой_пес.гав())''',

                '13. Наследование': '''# Базовый класс
class Животное:
    def __init__(self, имя):
        self.имя = имя

# Наследуем от Животного
class Кошка(Животное):
    def мяу(self):
        return self.имя + " говорит: Мяу!"

кошка = Кошка("Мурка")
print(кошка.мяу())''',

                '14. Ошибки': '''# Обработка ошибок
try:
    число = int(input("Введите число: "))
    print("10 /", число, "=", 10 / число)
except ValueError:
    print("Это не число!")
except ZeroDivisionError:
    print("На ноль делить нельзя!")''',

                '15. Файлы': '''# Записываем в файл
with open("тест.txt", "w") as ф:
    ф.write("Привет, мир!\\n")
    ф.write("Это мой файл")
print("Файл создан!")

# Читаем файл
with open("тест.txt", "r") as ф:
    текст = ф.read()
print("Содержимое:")
print(текст)''',

                '16. Рекурсия': '''# Факториал через рекурсию
def факториал(n):
    if n <= 1:
        return 1
    return n * факториал(n - 1)

print("5! =", факториал(5))
print("7! =", факториал(7))''',

                '17. Генераторы': '''# Генератор обратного отсчета
def отсчет(n):
    while n > 0:
        yield n
        n -= 1

print("Отсчет от 5:")
for число in отсчет(5):
    print(число, end=" ")''',

                '18. Декораторы': '''# Декоратор для замера времени
import time

def замерить_время(func):
    def обертка():
        начало = time.time()
        func()
        конец = time.time()
        print(f"\\nВремя: {конец - начало:.2f} сек")
    return обертка

@замерить_время
def пауза():
    time.sleep(2)
    print("Готово!")

пауза()'''
            }

    def show_search_only_dialog(self, instance=None):
        self.dismiss_search()
        content = SearchOnlyPopup(self.code_input)
        container = FloatLayout()
        search_box = BoxLayout(orientation='vertical', size_hint=(0.95, 0.15), pos_hint={'top': 1.0, 'center_x': 0.5})
        search_box.add_widget(content)
        container.add_widget(search_box)
        popup = Popup(title='', title_color=(0, 0, 0, 0), separator_color=(0, 0, 0, 0), background='', background_color=(0, 0, 0, 0), content=container, size_hint=(1, 1), auto_dismiss=False, overlay_color=(0, 0, 0, 0))
        content.set_popup(popup)
        content.open_popup()
        self.search_popup = popup

    def show_search_replace_dialog(self, instance=None):
        self.dismiss_search()
        content = SearchReplacePopup(self.code_input)
        container = FloatLayout()
        replace_box = BoxLayout(orientation='vertical', size_hint=(0.95, 0.22), pos_hint={'top': 1.0, 'center_x': 0.5})
        replace_box.add_widget(content)
        container.add_widget(replace_box)
        popup = Popup(title='', title_color=(0, 0, 0, 0), separator_color=(0, 0, 0, 0), background='', background_color=(0, 0, 0, 0), content=container, size_hint=(1, 1), auto_dismiss=False, overlay_color=(0, 0, 0, 0))
        content.set_popup(popup)
        content.open_popup()
        self.search_popup = popup

    def dismiss_search(self):
        if self.search_popup:
            try:
                self.search_popup.dismiss()
            except:
                pass
            self.search_popup = None
        if hasattr(self, 'code_input') and self.code_input:
            self.code_input.focus = True

    def show_search_dialog_from_button(self):
        self.show_search_only_dialog(None)

    def show_history(self, instance):
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
        if not HAS_AUTOPEP8:
            self.show_result_popup("! autopep8 not installed")
            return
        code = self.code_input.text
        if not code.strip():
            return
        self.run_btn.text = "..."
        self.run_btn.disabled = True
        def do_format():
            try:
                formatted = autopep8.fix_code(code, options={'aggressive': 1, 'indent_size': 4})
                Clock.schedule_once(lambda dt: self._format_done(formatted))
            except Exception as e:
                Clock.schedule_once(lambda dt: self._format_error(str(e)))
        threading.Thread(target=do_format, daemon=True).start()

    def _format_done(self, formatted):
        self.run_btn.text = self.tr.get('run', '▶')
        self.run_btn.disabled = False
        if formatted:
            cursor_pos = self.code_input.cursor_index()
            self.code_input.text = formatted
            if hasattr(self, 'editor') and self.editor:
                self.editor.original_lines = formatted.split('\n')
                self.editor._update_line_panel()
            try:
                if cursor_pos <= len(formatted):
                    self.code_input.cursor = self.code_input.get_cursor_from_index(cursor_pos)
            except:
                pass
            self.show_result_popup(self.tr.get('formatted_ok', '! Code formatted'))
        else:
            self.show_result_popup(self.tr.get('formatted_fail', '! Format failed'))

    def _format_error(self, error_msg):
        self.run_btn.text = self.tr.get('run', '▶')
        self.run_btn.disabled = False
        self.show_result_popup(f"{self.tr.get('error', 'Error')}:\n{error_msg}")

    def show_api_key_settings(self, instance=None):
        tr = self.tr
        current_key = self.saved_api_key or SettingsManager.get_api_key()
        theme = ThemeManager.get_theme()
        content = BoxLayout(orientation='vertical', padding=dp(5), spacing=dp(3))
        status_label = Label(text=tr.get('api_ok', '✓ Key set') if current_key else tr.get('api_not_set', '! Key not set'), font_name='SourceBold', color=theme['text_color'], font_size=dp(10), size_hint_y=None, height=dp(15))
        content.add_widget(status_label)
        key_input = TextInput(text=current_key, font_name='SourceBold', hint_text=tr.get('api_key_hint', 'Paste API key'), multiline=False, font_size=dp(10), background_color=theme['input_bg'], foreground_color=theme['input_text'], hint_text_color=theme['hint_text'], size_hint_y=None, height=dp(27), padding=(dp(5), dp(5)))
        content.add_widget(key_input)
        info_label = Label(text=tr.get('api_info', 'Get key: aistudio.google.com'), font_name='SourceBold', color=theme['stats_text'], font_size=dp(8), size_hint_y=None, height=dp(13))
        content.add_widget(info_label)
        btn_layout = BoxLayout(size_hint_y=None, height=dp(22), spacing=dp(4))
        popup = Popup(title=tr.get('api_title', 'API Key'), title_color=theme['popup_title'],background='', background_color=theme.get('popup_bg', (1.0, 1.0, 1.0, 1)), content=content, size_hint=(0.9, 0.5), auto_dismiss=True)
        btn_clear = Button(text=tr.get('delete', 'Delete'), font_name='SourceBold', background_color=(0.3, 0.1, 0.1, 1), background_normal='', background_down='', color=theme['text_color'], font_size=dp(9), on_release=lambda x: self._clear_api_key(key_input, status_label))
        btn_save = Button(text=tr.get('save', 'Save'), font_name='SourceBold', background_color=theme['widget_bg'], background_normal='', background_down='', color=theme['text_color'], font_size=dp(9), on_release=lambda x: self._save_api_key(key_input, status_label, popup))
        btn_cancel = Button(text=tr.get('cancel', 'Cancel'), font_name='SourceBold', background_color=theme['widget_bg'], background_normal='', background_down='', color=theme['text_color'], font_size=dp(9), on_release=lambda x: popup.dismiss())
        btn_layout.add_widget(btn_clear)
        btn_layout.add_widget(btn_save)
        btn_layout.add_widget(btn_cancel)
        content.add_widget(btn_layout)
        popup.open()

    def _clear_api_key(self, key_input, status_label):
        key_input.text = ''
        SettingsManager.save_api_key('')
        self.saved_api_key = ''
        status_label.text = self.tr.get('api_not_set', '! Key not set')
        self.show_result_popup(self.tr.get('api_deleted', 'X Key deleted'))

    def _save_api_key(self, key_input, status_label, popup):
        api_key = key_input.text.strip()
        if api_key:
            SettingsManager.save_api_key(api_key)
            self.saved_api_key = api_key
            status_label.text = self.tr.get('api_ok', '✓ Key set')
            self.show_result_popup(self.tr.get('api_saved', '✓ Key saved!'))
        popup.dismiss()

    def show_ai_assistant(self, instance):
        api_key = self.saved_api_key or SettingsManager.get_api_key()
        if not api_key:
            self.show_result_popup(self.tr.get('no_api_key', '! API key not set'))
            return
        content = AIAssistantPopup(api_key=api_key)
        theme = ThemeManager.get_theme()
        popup = Popup(title=self.tr.get('ai_title', 'AI Assistant'), title_color=theme['popup_title'],background='', background_color=theme.get('popup_bg', (1.0, 1.0, 1.0, 1)), content=content, size_hint=(0.95, 0.9))
        popup.open()

    def switch_language(self, instance=None):
        self.current_language = 'en' if self.current_language == 'ru' else 'ru'
        self.tr = TRANSLATIONS[self.current_language]
        try:
            with open(os.path.join(os.getcwd(), 'language.txt'), 'w') as f:
                f.write(self.current_language)
        except:
            pass
        SettingsManager.save_language(self.current_language)
        self._update_ui_language()
        self.show_result_popup(self.tr.get('language', 'Language') + ': ' + self.current_language.upper())

    def _update_ui_language(self):
        tr = self.tr
        self._examples_cache = None
        if hasattr(self, 'tab_manager'):
            for tab in self.tab_manager.tabs:
                if tab['title'] in ['Untitled', 'New', 'New']:
                    tab['title'] = tr.get('untitled_tab', 'New')
            self.tab_manager._update_tab_bar()
        if hasattr(self, 'spinner'):
            try:
                self.spinner.values = self._get_example_titles()
                self.spinner.text = tr.get('examples', 'Examples')
            except:
                pass
        if hasattr(self, 'action_bar'):
            try:
                self.action_bar.action_keys = ['undo', 'redo', 'copy', 'paste', 'cut', 'sel_all', 'auto', 'key', 'clean', 'find']
                self.action_bar._create_buttons()
                self.action_bar.button_container.clear_widgets()
                for btn in self.action_bar.buttons:
                    self.action_bar.button_container.add_widget(btn)
            except:
                pass
        if hasattr(self, 'run_btn'):
            try:
                self.run_btn.text = tr.get('run', '▶')
            except:
                pass
        if hasattr(self, '_menu_dropdown'):
            try:
                self._create_menu_items(ThemeManager.get_theme())
            except:
                pass
        try:
            if self._has_unsaved_changes:
                self._update_title_with_unsaved()
            else:
                self._update_title_saved()
        except:
            pass

    def _open_settings_menu(self, button):
        if self._settings_menu is None:
            self._settings_menu = SettingsMenu(self)
        self._settings_menu.show(self.menu_button)

    def show_result_popup(self, result):
        """Показывает результат в всплывающем окне."""
        tr = self.tr
    
        if len(result) > 50000:
            result = result[:50000] + "\n\n... " + \
                tr.get('output_truncated', '(truncated)')
    
        theme = ThemeManager.get_theme()
        content = BoxLayout(orientation='vertical', padding=dp(5), spacing=dp(3))
    
        scroll = ScrollView(size_hint=(1, 0.85),
                            do_scroll_x=False, do_scroll_y=True)
        output_view = TextInput(
            text=str(result),
            readonly=True,
            font_size=dp(10),
            font_name='SourceBold',
            background_color=theme['result_bg'],
            foreground_color=theme['result_text'],
            do_wrap=True,
            multiline=True,
            size_hint_y=None,
            height=dp(33),
            padding=(dp(5), dp(5), dp(5), dp(5))
        )
        output_view.bind(minimum_height=output_view.setter('height'))
        scroll.add_widget(output_view)
        content.add_widget(scroll)
    
        btn_layout = BoxLayout(size_hint_y=None, height=dp(18), spacing=dp(3))
    
        btn_copy = Button(
            text=tr.get('copy_btn', 'Copy'),
            font_name='SourceBold',
            background_color=theme['widget_bg'],
            background_normal='',
            background_down='',
            color=theme['text_color'],
            font_size=dp(15),
            size_hint_y=None,
            height=dp(33),
            on_release=lambda x: self._copy_result(result)
        )
    
        btn_close = Button(
            text=tr.get('close', 'Close'),
            font_name='SourceBold',
            background_color=theme['widget_bg'],
            background_normal='',
            background_down='',
            color=theme['text_color'],
            font_size=dp(15),
            size_hint_y=None,
            height=dp(33)
        )
    
        btn_layout.add_widget(btn_copy)
        btn_layout.add_widget(btn_close)
        content.add_widget(btn_layout)
    
        popup = ThemedPopup(
            title=tr.get('result_title', 'Result'),
            popup_bg=theme.get('popup_bg', (0.188, 0.204, 0.251, 1)),
            title_bg=theme.get('popup_title_bg', (0.188, 0.204, 0.251, 1)),
            title_color=theme['popup_title'],
            content=content,
            size_hint=(0.90, 0.82),
            auto_dismiss=False,
            separator_color=theme.get('popup_separator', (0.25, 0.25, 0.25, 1))
        )
        btn_close.bind(on_release=popup.dismiss)
        popup.open()
        self._popup = popup
        self._current_popup_type = 'result'

    def _copy_result(self, text):
        Clipboard.copy(text)
        if platform == 'android':
            android_copy(text)
        self.show_result_popup(self.tr.get('result_copied', '✓ Copied'))

    def dismiss_popup(self, *args):
        if self._popup:
            try:
                if hasattr(self._popup, 'dismiss'):
                    self._popup.dismiss()
            except:
                pass
            finally:
                self._popup = None
                self._current_popup_type = None

    def _show_rename_tab_dialog(self, index):
        """Показывает диалог переименования вкладки."""
        tr = self.tr
        theme = ThemeManager.get_theme()
    
        if index < 0 or index >= len(self.tab_manager.tabs):
            return
    
        current_title = self.tab_manager.tabs[index]['title']
    
        content = BoxLayout(orientation='vertical', padding=[dp(7), dp(2), dp(7), dp(7)], spacing=dp(33))
    
        content.add_widget(Label(
            text=tr.get('rename_tab', 'Rename tab'),
            color=theme['text_color'], font_size=dp(15),
            font_name='SourceBold',
            size_hint_y=None, height=dp(15)
        ))
    
        name_input = TextInput(
            text=current_title, multiline=False, font_size=dp(15),
            font_name='SourceBold',
            background_color=theme['input_bg'],
            foreground_color=theme['input_text'],
            size_hint_y=None, height=dp(30),
            padding=(dp(5), dp(5))
        )
        content.add_widget(name_input)
    
        btn_layout = BoxLayout(size_hint_y=None, height=dp(18), spacing=dp(51))
    
        popup = Popup(
            title=tr.get('rename_tab', 'Rename'),
            title_color=theme['popup_title'],
            background='',
            background_color=theme.get('popup_bg', (1.0, 1.0, 1.0, 1)),
            content=content,
            size_hint=(0.85, 0.35),
            pos_hint={'top': 0.80},
            auto_dismiss=False
        )
    
        btn_ok = Button(
            text=tr.get('ok', 'OK'),
            font_name='SourceBold',
            background_color=theme['widget_bg'],
            background_normal='', background_down='',
            color=theme['text_color'], font_size=dp(15),
            size_hint_y=None, height=dp(30),
            on_release=lambda x: self._rename_tab_confirm(popup, index, name_input)
        )
        
        btn_cancel = Button(
            text=tr.get('cancel', 'Cancel'),
            font_name='SourceBold',
            background_color=theme['widget_bg'],
            background_normal='', background_down='',
            color=theme['text_color'], font_size=dp(15),
            size_hint_y=None, height=dp(30),
            on_release=lambda x: popup.dismiss()
        )
    
        btn_layout.add_widget(btn_cancel)
        btn_layout.add_widget(btn_ok)
        content.add_widget(btn_layout)
        popup.open()
        self._popup = popup

    def _rename_tab_confirm(self, popup, index, name_input):
        new_title = name_input.text.strip()
        if new_title:
            self.tab_manager.tabs[index]['title'] = new_title
            self.tab_manager._update_tab_bar()
            self.tab_manager.save_all_tabs()
        popup.dismiss()

    def _keyboard_handler(self, window, key, scancode=None, codepoint=None, modifier=None):
        if hasattr(self, 'current_input_widget') and self.current_input_widget:
            try:
                if self.current_input_widget.focus:
                    return False
            except:
                pass
        ctrl_pressed = modifier and 'ctrl' in modifier
        if ctrl_pressed:
            hotkeys = {115: self.show_save_dialog, 111: self.show_load_dialog, 102: self.show_search_only_dialog, 114: self.run_code, 104: self.show_history, 110: self.new_file}
            if key in hotkeys:
                Clock.schedule_once(lambda dt, f=hotkeys[key]: f(None), 0)
                return True
        return False


if __name__ == '__main__':
    try:
        PythonLearningApp().run()
    except Exception as e:
        error_msg = f"FATAL ERROR: {e}\n\nTraceback:\n{traceback.format_exc()}"
        try:
            with open('/storage/emulated/0/Download/app_error.log', 'w', encoding='utf-8') as f:
                f.write(error_msg)
        except:
            pass
        raise

















































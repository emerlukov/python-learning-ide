"""
Theme and syntax highlighting management
"""
import os
import json
from kivy.app import App
from kivy.core.window import Window
from ide_core.settings import SettingsManager
from utils.debug_utils import log_error

# Try to import pygments
try:
    from pygments.styles import get_style_by_name
    HAS_PYGMENTS = True
except ImportError:
    HAS_PYGMENTS = False


# [ВСЕ ЦВЕТОВЫЕ СХЕМЫ]
# ==================== ТЁМНАЯ ТЕМА ====================
DARK_THEME = {
    'name': 'dark',

    # ==================== ОСНОВНЫЕ ФОНЫ ====================
    'app_bg': (0.188, 0.204, 0.251, 1),  # фон всего приложения
    'window_bg': (0.06, 0.06, 0.06, 1),  # фон за границами приложения (Window.clearcolor)
    'widget_bg': (0.141, 0.145, 0.149, 1),  # фон кнопок, вкладок, попапов
    'text_color': (0.85, 0.88, 0.90, 1),  # цвет текста везде

    # ==================== ПАНЕЛИ ИНСТРУМЕНТОВ ====================
    'action_bar_bg': (0.18, 0.18, 0.19, 1),  # фон панели кнопок действий
    'top_bar_bg': (0.18, 0.18, 0.19, 1),  # фон верхней панели (Spinner + кнопка ☰)
    'symbol_btn_bg': (0.141, 0.145, 0.149, 1),  # фон кнопок на панелях
    'symbol_btn_text': (0.85, 0.88, 0.90, 1),  # цвет текста/иконок на кнопках панелей

    # ==================== РЕДАКТОР КОДА ====================
    'editor_bg': (0.188, 0.204, 0.251, 1),  # фон редактора кода
    'editor_text': (0.95, 0.95, 0.95, 1),  # цвет текста в редакторе
    'editor_cursor': (1.0, 1.0, 1.0, 1),  # цвет курсора
    'editor_selection': (1, 1, 1, 0.15),  # цвет выделения текста
    'panel_bg': (0.188, 0.204, 0.251, 1),  # фон панели с номерами строк
    'panel_text': (0.45, 0.48, 0.50, 1),  # цвет номеров строк
    'separator_color': (0.5, 0.5, 0.5, 0.3),  # разделитель панели строк и кода
    'current_line_highlight': (1, 1, 1, 0.04),  # подсветка текущей строки
    'indent_guide_color': (0.35, 0.38, 0.40, 0.30),  # направляющие отступов

    # ==================== ПОЛЯ ВВОДА ====================
    'input_bg': (0.188, 0.204, 0.251, 1),  # фон полей ввода
    'input_text': (1.0, 1.0, 1.0, 1),  # цвет текста в полях ввода
    'input_cursor': (1.0, 1.0, 1.0, 1),  # цвет курсора в полях ввода
    'hint_text': (0.45, 0.48, 0.50, 1),  # цвет подсказок в пустых полях

    # ==================== ВКЛАДКИ ====================
    'tab_bar_bg': (0.18, 0.18, 0.19, 1),  # фон панели вкладок
    'tab_inactive_bg': (0.141, 0.145, 0.149, 1),  # фон неактивных вкладок
    'tab_active_bg': (0.188, 0.204, 0.251, 1),  # фон активной вкладки
    'tab_add_btn_bg': (0.141, 0.145, 0.149, 1),  # фон кнопки добавления вкладки
    'tab_close_btn_text': (0.85, 0.88, 0.90, 1),  # цвет кнопки закрытия вкладки
    'tab_context_danger_bg': (0.5, 0.2, 0.2, 1),  # фон кнопки "Закрыть все"

    # ==================== ВЕРХНЯЯ ПАНЕЛЬ (Spinner + ☰) ====================
    'spinner_bg': (0.141, 0.145, 0.149, 1),  # фон выпадающего списка Примеров
    'spinner_text': (0.85, 0.88, 0.90, 1),  # текст в списке Примеров
    'spinner_dropdown_bg': (0.188, 0.204, 0.251, 1),  # фон выпавшего меню Примеров
    'spinner_dropdown_text': (0.85, 0.88, 0.90, 1),  # цвет пунктов в выпавшем меню
    'spinner_dropdown_selected_bg': (0.141, 0.145, 0.149, 1),  # фон выбранного пункта
    'spinner_dropdown_btn_bg': (0.141, 0.14, 0.149, 1),  # фон кнопок-примеров
    'menu_btn_bg': (0.141, 0.145, 0.149, 1),  # фон кнопки ☰
    'menu_btn_text': (0.85, 0.88, 0.90, 1),  # цвет значка ☰

    # ==================== ВСПЛЫВАЮЩИЕ ОКНА ====================
    'popup_bg': (0.188, 0.204, 0.251, 1),  # фон всплывающих окон
    'popup_title': (0.85, 0.88, 0.90, 1),  # цвет заголовка попапа
    'popup_title_bg': (0.188, 0.204, 0.251, 1),  # фон заголовка попапа
    'popup_separator': (0.25, 0.25, 0.25, 1),  # разделитель под заголовком попапа

    # ==================== КНОПКИ РАЗНЫХ ТИПОВ ====================
    'btn_success_bg': (0.2, 0.5, 0.2, 1),  # зелёные кнопки (Apply, Save)
    'btn_danger_bg': (0.5, 0.2, 0.2, 1),  # красные кнопки (Close, Delete)
    'btn_selected_file_bg': (0.3, 0.5, 0.3, 1),  # выделенный файл в диалоге
    'fold_btn_bg': (0.141, 0.145, 0.149, 1),  # фон кнопок сворачивания
    'fold_btn_text': (0.75, 0.78, 0.80, 1),  # текст кнопок сворачивания

    # ==================== КНОПКА ЗАПУСКА ====================
    'run_btn_bg': (0.85, 0.88, 0.90, 1),  # фон кнопки Run
    'run_btn_text': (0.18, 0.18, 0.19, 1),  # цвет значка ▶
    'run_btn_shadow': (0, 0, 0, 0.35),  # тень кнопки Run

    # ==================== ПРОЧЕЕ ====================
    'syntax_style': 'dracula',  # стиль подсветки по умолчанию
    'result_bg': (0.188, 0.204, 0.251, 1),  # фон окна результата
    'result_text': (0.85, 0.88, 0.90, 1),  # текст в окне результата
    'stats_text': (0.60, 0.63, 0.65, 1),  # цвет пути к файлу
    'ai_response_bg': (0.06, 0.06, 0.06, 1),  # фон ответа AI
    'scroll_bar_color': (0.4, 0.4, 0.4, 0.9),  # полоса прокрутки активная
    'scroll_bar_inactive': (0.25, 0.25, 0.25, 0.6),  # полоса прокрутки неактивная

    # ==================== ПОЛЯ ВВОДА В УРОКАХ ====================
    'lesson_input_bg': (0.25, 0.30, 0.40, 1),  # тёмно-синий фон
    'lesson_input_text': (0.95, 0.95, 0.95, 1),  # белый текст
    'tab_bg': (0.25, 0.30, 0.40, 1),
    'accent': (0.95, 0.95, 1.00, 1),
}

# ==================== СВЕТЛАЯ ТЕМА ====================
LIGHT_THEME = {
    'name': 'light',

    # ==================== ОСНОВНЫЕ ФОНЫ ====================
    'app_bg': (1.0, 1.0, 1.0, 1),  # фон всего приложения — белый
    'window_bg': (1.0, 1.0, 1.0, 1),  # фон за границами — белый
    'widget_bg': (0.843, 0.816, 1.0, 1),  # фон кнопок — светло-фиолетовый #D7D0FF
    'text_color': (0, 0, 0, 1),  # цвет текста — чёрный

    # ==================== ПАНЕЛИ ИНСТРУМЕНТОВ ====================
    'action_bar_bg': (0.843, 0.816, 1.0, 1),  # фон панели кнопок — #D7D0FF
    'top_bar_bg': (0.843, 0.816, 1.0, 1),  # фон верхней панели — #D7D0FF
    'symbol_btn_bg': (0.596, 0.486, 1.0, 1),  # фон кнопок на панелях — #987CFF
    'symbol_btn_text': (0, 0, 0, 1),  # текст на кнопках панелей — чёрный

    # ==================== РЕДАКТОР КОДА ====================
    'editor_bg': (1.0, 1.0, 1.0, 1),  # фон редактора — белый
    'editor_text': (0, 0, 0, 1),  # текст в редакторе — чёрный
    'editor_cursor': (0, 0, 0, 1),  # курсор — чёрный
    'editor_selection': (0, 0, 0, 0.12),  # выделение текста
    'panel_bg': (0.843, 0.816, 1.0, 1),  # панель номеров строк — #D7D0FF
    'panel_text': (0.40, 0.40, 0.40, 1),  # номера строк — тёмно-серый
    'separator_color': (0.5, 0.5, 0.5, 0.3),  # разделитель панели строк
    'current_line_highlight': (0.7, 0.7, 0.7, 0.08),  # подсветка строки курсора
    'indent_guide_color': (0.7, 0.7, 0.7, 0.30),  # направляющие отступов

    # ==================== ПОЛЯ ВВОДА ====================
    'input_bg': (1.0, 1.0, 1.0, 1),  # фон полей ввода — белый
    'input_text': (0, 0, 0, 1),  # текст в полях — чёрный
    'input_cursor': (0, 0, 0, 1),  # курсор — чёрный
    'hint_text': (0.50, 0.50, 0.50, 1),  # подсказки — серый

    # ==================== ВКЛАДКИ ====================
    'tab_bar_bg': (0.596, 0.486, 1.0, 1),  # фон панели вкладок — #987CFF
    'tab_inactive_bg': (0.843, 0.816, 1.0, 1),  # неактивные вкладки — #D7D0FF
    'tab_active_bg': (1.0, 1.0, 1.0, 1),  # фон активной вкладки — белый
    'tab_add_btn_bg': (0.843, 0.816, 1.0, 1),  # кнопка добавления — #D7D0FF
    'tab_close_btn_text': (0, 0, 0, 1),  # кнопка закрытия — чёрный
    'tab_context_danger_bg': (0.7, 0.2, 0.2, 1),  # кнопка "Закрыть все" — красный

    # ==================== ВЕРХНЯЯ ПАНЕЛЬ (Spinner + ☰) ====================
    'spinner_bg': (0.596, 0.486, 1.0, 1),  # фон Примеров — #987CFF
    'spinner_text': (0, 0, 0, 1),  # текст Примеров — чёрный
    'spinner_dropdown_bg': (1.0, 1.0, 1.0, 1),  # фон меню Примеров — белый
    'spinner_dropdown_text': (0, 0, 0, 1),  # пункты меню — чёрный
    'spinner_dropdown_selected_bg': (0.843, 0.816, 1.0, 1),  # выбранный пункт — #D7D0FF
    'spinner_dropdown_btn_bg': (1.0, 1.0, 1.0, 1),  # кнопки-примеры — белый
    'menu_btn_bg': (0.596, 0.486, 1.0, 1),  # кнопка ☰ — #987CFF
    'menu_btn_text': (0, 0, 0, 1),  # значок ☰ — чёрный

    # ==================== ВСПЛЫВАЮЩИЕ ОКНА ====================
    'popup_bg': (1.0, 1.0, 1.0, 1),  # фон попапов — белый
    'popup_title': (0, 0, 0, 1),  # заголовок попапа — чёрный
    'popup_title_bg': (0.843, 0.816, 1.0, 1),  # фон заголовка — #D7D0FF
    'popup_separator': (0.70, 0.69, 0.66, 1),  # разделитель попапа — светлый

    # ==================== КНОПКИ РАЗНЫХ ТИПОВ ====================
    'btn_success_bg': (0.2, 0.5, 0.2, 1),  # зелёные кнопки
    'btn_danger_bg': (0.7, 0.2, 0.2, 1),  # красные кнопки
    'btn_selected_file_bg': (0.3, 0.5, 0.3, 1),  # выделенный файл
    'fold_btn_bg': (0.843, 0.816, 1.0, 1),  # кнопки сворачивания — #D7D0FF
    'fold_btn_text': (0.35, 0.35, 0.35, 1),  # текст сворачивания — тёмный

    # ==================== КНОПКА ЗАПУСКА ====================
    'run_btn_bg': (0.596, 0.486, 1.0, 1),  # кнопка Run — #987CFF
    'run_btn_text': (0, 0, 0, 1),  # значок ▶ — чёрный
    'run_btn_shadow': (0, 0, 0, 0.25),  # тень кнопки

    # ==================== ПРОЧЕЕ ====================
    'syntax_style': 'default',  # стиль подсветки по умолчанию
    'result_bg': (1.0, 1.0, 1.0, 1),  # фон результата — белый
    'result_text': (0, 0, 0, 1),  # текст результата — чёрный
    'stats_text': (0.40, 0.40, 0.40, 1),  # путь к файлу — тёмно-серый
    'ai_response_bg': (1.0, 1.0, 1.0, 1),  # фон ответа AI — белый
    'scroll_bar_color': (0.6, 0.6, 0.6, 0.9),  # полоса прокрутки активная
    'scroll_bar_inactive': (0.8, 0.8, 0.8, 0.6),  # полоса прокрутки неактивная

    # ==================== ПОЛЯ ВВОДА В УРОКАХ ====================
    'lesson_input_bg': (0.596, 0.486, 1.0, 1),  # фиолетовый #987CFF
    'lesson_input_text': (0, 0, 0, 1),  # чёрный текст
    'tab_bg': (0.843, 0.816, 1.0, 1),   # светло-фиолетовый #D7D0FF
    'accent': (0, 0, 0, 1), # чёрный текст
}

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
        from utils.paths import user_data_path, ensure_user_data_dir
        ensure_user_data_dir()
        return user_data_path('python_ide_settings.json')

    @classmethod
    def get_styles_by_theme(cls, theme_name):
        """Возвращает список стилей для указанной темы"""
        dark_styles = ['monokai', 'dracula', 'github-dark', 'one-dark', 'native', 'material', 'xcode-dark',
                       'stata-dark', 'rainbow_dash']
        light_styles = ['default', 'xcode', 'friendly', 'github', 'autumn', 'borland', 'trac', 'colorful', 'vs', 'sas',
                        'arduino']

        if theme_name == 'dark':
            return [s for s in cls.get_available_styles() if s in dark_styles]
        else:
            return [s for s in cls.get_available_styles() if s in light_styles]

    @classmethod
    def get_default_style_for_theme(cls, theme_name):
        """Возвращает стиль по умолчанию для темы"""
        if theme_name == 'dark':
            return 'monokai'
        else:
            return 'arduino'


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
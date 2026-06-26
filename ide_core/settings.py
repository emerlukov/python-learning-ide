"""
Settings management for the application
"""
import os
import json
from utils.debug_utils import log_error
from utils.paths import user_data_path, ensure_user_data_dir

class SettingsManager:
    """Управляет сохранением и загрузкой настроек"""
    _saving = False

    @staticmethod
    def get_settings_path():
        ensure_user_data_dir()
        return user_data_path('python_ide_settings.json')

    @classmethod
    def load(cls):
        try:
            with open(cls.get_settings_path(), 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}

    @classmethod
    def save(cls, settings_dict):
        # ДОБАВИТЬ ПРОВЕРКУ В НАЧАЛЕ МЕТОДА
        if cls._saving:
            return True  # Предотвращаем рекурсивный вызов

        cls._saving = True
        try:
            settings_path = cls.get_settings_path()
            os.makedirs(os.path.dirname(settings_path), exist_ok=True)
            with open(settings_path, 'w', encoding='utf-8') as f:
                json.dump(settings_dict, f, indent=2)
            return True
        except Exception as e:
            log_error(f"Error saving settings: {e}")
            return False
        finally:
            cls._saving = False  # ВАЖНО: сбрасываем флаг в любом случае

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

    @classmethod
    def get_vibration_enabled(cls):
        """Возвращает состояние вибрации (по умолчанию True)"""
        settings = cls.load()
        return settings.get('vibration_enabled', True)

    @classmethod
    def save_vibration_enabled(cls, enabled):
        """Сохраняет состояние вибрации"""
        settings = cls.load()
        settings['vibration_enabled'] = enabled
        return cls.save(settings)
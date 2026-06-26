# tests/test_settings.py
"""
Unit tests for SettingsManager
"""
import os
import json
import tempfile
import unittest
from unittest.mock import patch, MagicMock


class TestSettingsManager(unittest.TestCase):
    """Тесты для SettingsManager"""

    def setUp(self):
        """Подготовка перед каждым тестом"""
        # Создаём временную директорию для тестов
        self.temp_dir = tempfile.mkdtemp()

        # Переопределяем user data dir для тестов
        from utils import paths
        self.user_dir = os.path.join(self.temp_dir, 'user')
        os.makedirs(self.user_dir, exist_ok=True)
        paths.set_user_data_dir(self.user_dir)

        # Импортируем SettingsManager после патча
        from ide_core.settings import SettingsManager
        self.SettingsManager = SettingsManager
        self.paths = paths

        # Сбрасываем флаг _saving перед каждым тестом
        self.SettingsManager._saving = False

    def tearDown(self):
        """Очистка после каждого теста"""
        self.paths.reset_paths()

        # Удаляем временную директорию
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_get_settings_path(self):
        """Тест: путь к файлу настроек"""
        path = self.SettingsManager.get_settings_path()
        expected = os.path.join(self.user_dir, 'python_ide_settings.json')
        self.assertEqual(path, expected)

    def test_save_and_load_api_key(self):
        """Тест: сохранение и загрузка API ключа"""
        # Сохраняем ключ
        result = self.SettingsManager.save_api_key("test_api_key_123")
        self.assertTrue(result)

        # Загружаем ключ
        loaded_key = self.SettingsManager.get_api_key()
        self.assertEqual(loaded_key, "test_api_key_123")

    def test_save_and_load_language(self):
        """Тест: сохранение и загрузка языка"""
        # Сохраняем русский язык
        result = self.SettingsManager.save_language('ru')
        self.assertTrue(result)

        # Загружаем язык
        lang = self.SettingsManager.get_language()
        self.assertEqual(lang, 'ru')

        # Сохраняем английский
        self.SettingsManager.save_language('en')
        lang = self.SettingsManager.get_language()
        self.assertEqual(lang, 'en')

    def test_save_and_load_theme(self):
        """Тест: сохранение и загрузка темы"""
        # Сохраняем тёмную тему
        result = self.SettingsManager.save_theme('dark')
        self.assertTrue(result)

        # Загружаем тему
        theme = self.SettingsManager.get_theme()
        self.assertEqual(theme, 'dark')

        # Сохраняем светлую
        self.SettingsManager.save_theme('light')
        theme = self.SettingsManager.get_theme()
        self.assertEqual(theme, 'light')

    def test_save_and_load_font(self):
        """Тест: сохранение и загрузка шрифта"""
        # Сохраняем шрифт
        result = self.SettingsManager.save_font('JetBrainsMono')
        self.assertTrue(result)

        # Загружаем шрифт
        font = self.SettingsManager.get_font()
        self.assertEqual(font, 'JetBrainsMono')

        # Сохраняем другой шрифт
        self.SettingsManager.save_font('FiraCode')
        font = self.SettingsManager.get_font()
        self.assertEqual(font, 'FiraCode')

    def test_default_values(self):
        """Тест: значения по умолчанию"""
        # Очищаем настройки
        settings_path = self.SettingsManager.get_settings_path()
        if os.path.exists(settings_path):
            os.remove(settings_path)

        # Должны вернуться значения по умолчанию
        self.assertEqual(self.SettingsManager.get_api_key(), '')
        self.assertEqual(self.SettingsManager.get_language(), 'en')
        self.assertEqual(self.SettingsManager.get_theme(), 'dark')
        self.assertEqual(self.SettingsManager.get_font(), 'JetBrainsMono')

    def test_save_empty_settings(self):
        """Тест: сохранение пустых настроек"""
        result = self.SettingsManager.save({})
        self.assertTrue(result)

        # Проверяем, что файл создан
        settings_path = self.SettingsManager.get_settings_path()
        self.assertTrue(os.path.exists(settings_path))

        # Проверяем содержимое
        with open(settings_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.assertEqual(data, {})

    def test_load_malformed_json(self):
        """Тест: загрузка повреждённого JSON"""
        settings_path = self.SettingsManager.get_settings_path()
        os.makedirs(os.path.dirname(settings_path), exist_ok=True)

        # Записываем повреждённый JSON
        with open(settings_path, 'w', encoding='utf-8') as f:
            f.write('{invalid json}')

        # Должен вернуться пустой словарь без ошибки
        data = self.SettingsManager.load()
        self.assertEqual(data, {})

    def test_prevent_recursive_save(self):
        """Тест: предотвращение рекурсивного сохранения"""
        self.SettingsManager._saving = True

        # Попытка сохранить должна вернуть True без ошибки
        result = self.SettingsManager.save({'test': 'value'})
        self.assertTrue(result)

        # Сбрасываем флаг
        self.SettingsManager._saving = False


if __name__ == '__main__':
    unittest.main()
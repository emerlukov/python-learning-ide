# tests/test_theme_manager.py
"""
Unit tests for ThemeManager and SyntaxStyleManager
"""
import unittest
from unittest.mock import patch, MagicMock


class TestThemeManager(unittest.TestCase):
    """Тесты для ThemeManager"""

    def setUp(self):
        """Подготовка перед каждым тестом"""
        from ide_core.themes import ThemeManager, DARK_THEME, LIGHT_THEME
        self.ThemeManager = ThemeManager
        self.DARK_THEME = DARK_THEME
        self.LIGHT_THEME = LIGHT_THEME

        # Сброс состояния перед тестами
        self.ThemeManager._current_theme = DARK_THEME
        self.ThemeManager._observers = []

    def test_get_theme(self):
        """Тест: получение текущей темы"""
        theme = self.ThemeManager.get_theme()
        self.assertIsNotNone(theme)
        self.assertIn('name', theme)

    def test_get_theme_name(self):
        """Тест: получение имени текущей темы"""
        name = self.ThemeManager.get_theme_name()
        self.assertIn(name, ['dark', 'light'])

    def test_get_available_themes(self):
        """Тест: получение списка доступных тем"""
        # Мокаем App.get_running_app
        mock_app = MagicMock()
        mock_app.tr = {'theme_dark': 'Тёмная', 'theme_light': 'Светлая'}

        with patch('kivy.app.App.get_running_app', return_value=mock_app):
            themes = self.ThemeManager.get_available_themes()
            self.assertIsInstance(themes, dict)
            self.assertIn('dark', themes)
            self.assertIn('light', themes)

    def test_switch_theme_dark_to_light(self):
        """Тест: переключение с тёмной на светлую тему"""
        result = self.ThemeManager.switch_theme('light')
        self.assertTrue(result)
        self.assertEqual(self.ThemeManager.get_theme_name(), 'light')

    def test_switch_theme_light_to_dark(self):
        """Тест: переключение со светлой на тёмную тему"""
        self.ThemeManager.switch_theme('light')
        result = self.ThemeManager.switch_theme('dark')
        self.assertTrue(result)
        self.assertEqual(self.ThemeManager.get_theme_name(), 'dark')

    def test_switch_theme_invalid(self):
        """Тест: переключение на несуществующую тему"""
        result = self.ThemeManager.switch_theme('invalid_theme')
        self.assertFalse(result)

    def test_apply_saved_theme(self):
        """Тест: применение сохранённой темы"""
        with patch('ide_core.settings.SettingsManager.get_theme', return_value='light'):
            self.ThemeManager.apply_saved_theme()
            self.assertEqual(self.ThemeManager.get_theme_name(), 'light')

    def test_register_observer(self):
        """Тест: регистрация наблюдателя"""
        observer = MagicMock()
        self.ThemeManager.register(observer)
        self.assertIn(observer, self.ThemeManager._observers)

    def test_unregister_observer(self):
        """Тест: удаление наблюдателя"""
        observer = MagicMock()
        self.ThemeManager.register(observer)
        self.ThemeManager.unregister(observer)
        self.assertNotIn(observer, self.ThemeManager._observers)

    def test_notify_observers_on_theme_change(self):
        """Тест: уведомление наблюдателей при смене темы"""
        observer = MagicMock()
        observer.apply_theme = MagicMock()
        self.ThemeManager.register(observer)

        self.ThemeManager.switch_theme('light')

        observer.apply_theme.assert_called_once()


class TestSyntaxStyleManager(unittest.TestCase):
    """Тесты для SyntaxStyleManager"""

    def setUp(self):
        """Подготовка перед каждым тестом"""
        from ide_core.themes import SyntaxStyleManager
        self.SyntaxStyleManager = SyntaxStyleManager

    def test_get_available_styles(self):
        """Тест: получение списка доступных стилей"""
        styles = self.SyntaxStyleManager.get_available_styles()
        self.assertIsInstance(styles, list)
        self.assertGreater(len(styles), 0)

    def test_get_style_display_info(self):
        """Тест: получение информации о стилях"""
        info = self.SyntaxStyleManager.get_style_display_info()
        self.assertIsInstance(info, dict)

    def test_get_styles_by_theme_dark(self):
        """Тест: получение стилей для тёмной темы"""
        styles = self.SyntaxStyleManager.get_styles_by_theme('dark')
        self.assertIsInstance(styles, list)
        # Тёмные стили должны содержать monokai или dracula
        self.assertTrue('monokai' in styles or 'dracula' in styles)

    def test_get_styles_by_theme_light(self):
        """Тест: получение стилей для светлой темы"""
        styles = self.SyntaxStyleManager.get_styles_by_theme('light')
        self.assertIsInstance(styles, list)

    def test_get_default_style_for_theme_dark(self):
        """Тест: стиль по умолчанию для тёмной темы"""
        style = self.SyntaxStyleManager.get_default_style_for_theme('dark')
        self.assertEqual(style, 'monokai')

    def test_get_default_style_for_theme_light(self):
        """Тест: стиль по умолчанию для светлой темы"""
        style = self.SyntaxStyleManager.get_default_style_for_theme('light')
        self.assertEqual(style, 'arduino')


if __name__ == '__main__':
    unittest.main()
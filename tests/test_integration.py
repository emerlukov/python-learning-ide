# tests/test_integration.py
"""
Integration tests for Python Learning IDE
"""
import unittest
import os
import tempfile
import shutil
from unittest.mock import MagicMock, patch


class TestIntegration(unittest.TestCase):
    """Интеграционные тесты для проверки взаимодействия компонентов"""

    def setUp(self):
        """Подготовка перед каждым тестом"""
        from managers.tab_manager import TabManager
        from ide_core.settings import SettingsManager
        from ide_core.themes import ThemeManager
        from managers.examples_manager import examples_manager
        from widgets.editor import LineNumberTextInput

        # Создаём временную директорию
        self.temp_dir = tempfile.mkdtemp()

        # Создаём мок приложения
        self.mock_app = MagicMock()
        self.mock_app.tr = {'untitled_tab': 'New'}

        # Инициализируем компоненты
        self.tab_manager = TabManager()
        self.tab_manager.app = self.mock_app
        self.settings_manager = SettingsManager()
        self.theme_manager = ThemeManager()
        self.editor = LineNumberTextInput()

    def tearDown(self):
        """Очистка после каждого теста"""
        shutil.rmtree(self.temp_dir)

    def test_tab_and_editor_integration(self):
        """Тест: интеграция вкладок и редактора"""
        # Создаём вкладку с текстом
        editor = self.tab_manager.add_tab(title="Test", text="print('Hello')")

        # Проверяем, что редактор создан
        self.assertIsNotNone(editor)
        self.assertEqual(editor.get_text(), "print('Hello')")

        # Переключаемся на вкладку
        active_editor = self.tab_manager.get_active_editor()
        self.assertEqual(active_editor.get_text(), "print('Hello')")

    def test_multiple_tabs_integration(self):
        """Тест: работа с несколькими вкладками"""
        # Создаём несколько вкладок
        editor1 = self.tab_manager.add_tab(title="Tab1", text="Code 1")
        editor2 = self.tab_manager.add_tab(title="Tab2", text="Code 2")
        editor3 = self.tab_manager.add_tab(title="Tab3", text="Code 3")

        self.assertEqual(len(self.tab_manager.tabs), 3)

        # Переключаемся между вкладками
        self.tab_manager.switch_to_tab(1)
        self.assertEqual(self.tab_manager.active_index, 1)

        self.tab_manager.switch_to_tab(0)
        self.assertEqual(self.tab_manager.active_index, 0)

        # Закрываем вкладку
        self.tab_manager.close_tab(1)
        self.assertEqual(len(self.tab_manager.tabs), 2)

    def test_tab_unsaved_state(self):
        """Тест: состояние несохранённой вкладки"""
        editor = self.tab_manager.add_tab(title="Test", text="Original")

        # Изначально сохранена
        self.assertTrue(self.tab_manager.tabs[0]['saved'])

        # Меняем текст
        editor.set_text("Changed")
        self.tab_manager.check_tab_changed(0)

        # Теперь не сохранена
        self.assertFalse(self.tab_manager.tabs[0]['saved'])

    def test_theme_and_editor_integration(self):
        """Тест: интеграция темы и редактора"""
        from ide_core.themes import DARK_THEME, LIGHT_THEME

        # Применяем тёмную тему
        self.theme_manager.set_theme(DARK_THEME)
        self.editor.apply_theme(DARK_THEME)

        # Проверяем цвета
        self.assertEqual(self.editor.current_theme_name, 'dark')

        # Применяем светлую тему
        self.theme_manager.set_theme(LIGHT_THEME)
        self.editor.apply_theme(LIGHT_THEME)

        self.assertEqual(self.editor.current_theme_name, 'light')

    def test_settings_and_editor_font_integration(self):
        """Тест: интеграция настроек шрифта и редактора"""
        # Сохраняем шрифт
        self.settings_manager.save_font('JetBrainsMono')

        # Применяем шрифт к редактору
        saved_font = self.settings_manager.get_font()
        self.editor.text_input.font_name = saved_font

        self.assertEqual(self.editor.text_input.font_name, 'JetBrainsMono')

    def test_examples_and_editor_integration(self):
        """Тест: интеграция примеров и редактора"""
        from managers.examples_manager import examples_manager

        # Загружаем пример
        examples_manager._examples = {
            "1. Hello World": {
                "ru": 'print("Привет, мир!")',
                "en": 'print("Hello, World!")'
            }
        }

        code = examples_manager.get_example("1. Hello World", "ru")
        self.editor.set_text(code)

        self.assertEqual(self.editor.get_text(), 'print("Привет, мир!")')

    def test_search_dialog_and_editor_integration(self):
        """Тест: интеграция диалога поиска и редактора"""
        from widgets.dialogs import SearchOnlyPopup

        # Устанавливаем текст в редакторе
        self.editor.set_text("Hello world\nTest line\nAnother line")

        # Создаём диалог поиска
        popup = SearchOnlyPopup(self.editor.text_input)
        popup.search_input.text = "line"
        popup._perform_search()

        # Должны быть найдены совпадения
        self.assertGreater(len(popup.search_results), 0)

    def test_file_manager_and_editor_integration(self):
        """Тест: интеграция файлового менеджера и редактора"""
        from file_manager import FileManager

        # Создаём тестовый файл
        test_file = os.path.join(self.temp_dir, 'test.py')
        with open(test_file, 'w') as f:
            f.write("print('Integration test')")

        # Загружаем файл через менеджер
        file_manager = FileManager(self.mock_app)

        result_content = []

        def callback(content, error):
            result_content.append(content)

        file_manager.read_file(test_file, callback)

        import time
        time.sleep(0.3)

        self.assertIsNotNone(result_content[0])

        # Устанавливаем содержимое в редактор
        self.editor.set_text(result_content[0])
        self.assertEqual(self.editor.get_text(), "print('Integration test')")

    def test_full_workflow(self):
        """Тест: полный рабочий процесс"""
        # 1. Создаём новую вкладку
        editor = self.tab_manager.add_tab(title="Workflow Test")

        # 2. Пишем код
        code = "print('Hello, World!')\nname = input('Name: ')\nprint(f'Hello, {name}')"
        editor.set_text(code)

        # 3. Сохраняем в файл
        test_file = os.path.join(self.temp_dir, 'workflow_test.py')
        with open(test_file, 'w') as f:
            f.write(code)

        # 4. Обновляем информацию о файле во вкладке
        self.tab_manager.tabs[0]['file'] = test_file
        self.tab_manager.tabs[0]['saved'] = True

        # 5. Проверяем состояние
        self.assertTrue(self.tab_manager.tabs[0]['saved'])
        self.assertEqual(self.tab_manager.tabs[0]['file'], test_file)

        # 6. Закрываем вкладку
        self.tab_manager.close_tab(0)
        self.assertEqual(len(self.tab_manager.tabs), 1)  # Осталась пустая вкладка

    def test_file_manager_and_editor_integration(self):
        """Тест: интеграция файлового менеджера и редактора"""
        self.skipTest("Требует реального файлового ввода-вывода")

    def test_search_dialog_and_editor_integration(self):
        """Тест: интеграция диалога поиска и редактора"""
        self.skipTest("Требует реального GUI и шрифтов")


if __name__ == '__main__':
    unittest.main()
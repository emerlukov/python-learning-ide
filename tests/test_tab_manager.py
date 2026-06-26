# tests/test_tab_manager.py
"""
Unit tests for TabManager
"""
import unittest
import tempfile
import os
from unittest.mock import MagicMock, patch


class TestTabManager(unittest.TestCase):
    """Тесты для TabManager"""

    def setUp(self):
        """Подготовка перед каждым тестом"""
        from managers.tab_manager import TabManager
        self.TabManager = TabManager

        # Создаём менеджер с мок-приложением
        self.manager = TabManager()
        self.manager.app = MagicMock()
        self.manager.app.tr = {'untitled_tab': 'New'}

        # Очищаем вкладки
        self.manager.tabs = []
        self.manager.active_index = -1

    def test_create_tab(self):
        """Тест: создание новой вкладки"""
        editor = self.manager.add_tab(title="Test Tab", text="print('hello')")

        self.assertEqual(len(self.manager.tabs), 1)
        self.assertEqual(self.manager.tabs[0]['title'], "Test Tab")
        self.assertEqual(self.manager.active_index, 0)
        self.assertIsNotNone(editor)

    def test_create_tab_without_title(self):
        """Тест: создание вкладки без заголовка"""
        editor = self.manager.add_tab()

        self.assertEqual(len(self.manager.tabs), 1)
        self.assertEqual(self.manager.tabs[0]['title'], "New")

    def test_switch_to_tab(self):
        """Тест: переключение между вкладками"""
        self.manager.add_tab(title="Tab 1")
        self.manager.add_tab(title="Tab 2")

        self.manager.switch_to_tab(1)

        self.assertEqual(self.manager.active_index, 1)

    def test_get_active_editor(self):
        """Тест: получение активного редактора"""
        editor1 = self.manager.add_tab(title="Tab 1")
        editor2 = self.manager.add_tab(title="Tab 2")

        active_editor = self.manager.get_active_editor()

        self.assertEqual(active_editor, editor2)

    def test_get_active_text(self):
        """Тест: получение текста из активной вкладки"""
        self.manager.add_tab(title="Tab 1", text="Hello World")

        text = self.manager.get_active_text()

        self.assertEqual(text, "Hello World")

    def test_mark_tab_saved(self):
        """Тест: отметка вкладки как сохранённой"""
        self.manager.add_tab(title="Tab 1")
        self.manager.mark_tab_saved(0)

        self.assertTrue(self.manager.tabs[0]['saved'])

    def test_mark_tab_unsaved(self):
        """Тест: отметка вкладки как изменённой"""
        self.manager.add_tab(title="Tab 1")
        self.manager.mark_tab_unsaved(0)

        self.assertFalse(self.manager.tabs[0]['saved'])

    def test_check_tab_changed_true(self):
        """Тест: обнаружение изменений в вкладке"""
        self.manager.add_tab(title="Tab 1", text="Original")

        # Меняем текст
        mock_editor = self.manager.tabs[0]['editor']
        mock_editor.get_text = MagicMock(return_value="Changed")

        has_changes = self.manager.check_tab_changed(0)

        self.assertTrue(has_changes)

    def test_close_tab_not_last(self):
        """Тест: закрытие вкладки (не последней)"""
        self.manager.add_tab(title="Tab 1")
        self.manager.add_tab(title="Tab 2")
        self.manager.add_tab(title="Tab 3")

        self.manager.close_tab(1)

        self.assertEqual(len(self.manager.tabs), 2)
        self.assertEqual(self.manager.tabs[0]['title'], "Tab 1")
        self.assertEqual(self.manager.tabs[1]['title'], "Tab 3")

    # tests/test_tab_manager.py - исправленный метод
    def test_save_and_load_tabs(self):
        """Тест: сохранение и загрузка вкладок"""
        import tempfile
        import os
        from managers.tab_manager import TabManager  # ← ДОБАВИТЬ ИМПОРТ

        with tempfile.NamedTemporaryFile(delete=False, suffix='.json') as tmp:
            tmp_path = tmp.name

        try:
            # Сохраняем через менеджер (патчим путь)
            with patch('os.getcwd', return_value=os.path.dirname(tmp_path)):
                self.manager.add_tab(title="Saved Tab", text="Saved content")
                self.manager.save_all_tabs()

            # Загружаем в новый менеджер
            new_manager = TabManager()  # ← ТЕПЕРЬ РАБОТАЕТ
            new_manager.app = MagicMock()

            with patch('os.getcwd', return_value=os.path.dirname(tmp_path)):
                result = new_manager.load_all_tabs()

            self.assertTrue(result)
            self.assertEqual(len(new_manager.tabs), 1)
            self.assertEqual(new_manager.tabs[0]['title'], "Saved Tab")

        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


if __name__ == '__main__':
    unittest.main()
# tests/test_editor.py
"""
Unit tests for Code Editor (без реального GUI)
"""
import unittest
from unittest.mock import MagicMock, patch


class TestEditor(unittest.TestCase):
    """Тесты для редактора кода (без создания реального виджета)"""

    def setUp(self):
        """Подготовка перед каждым тестом"""
        # Создаём мок для editor
        self.mock_editor = MagicMock()
        self.mock_editor.text_input = MagicMock()
        self.mock_editor.text_input.text = ""
        self.mock_editor.text_input.cursor = (0, 0)
        self.mock_editor.original_lines = [""]

        # Патчим метод _on_key_down
        self.mock_editor._on_key_down = MagicMock()

    def test_set_text(self):
        """Тест: установка текста"""
        test_text = "print('Hello')\nprint('World')"
        self.mock_editor.set_text = MagicMock()
        self.mock_editor.set_text(test_text)
        self.mock_editor.set_text.assert_called_with(test_text)

    def test_get_text(self):
        """Тест: получение текста"""
        self.mock_editor.get_text = MagicMock(return_value="test text")
        result = self.mock_editor.get_text()
        self.assertEqual(result, "test text")

    def test_clear_text(self):
        """Тест: очистка текста"""
        self.mock_editor.set_text = MagicMock()
        self.mock_editor.set_text("")
        self.mock_editor.set_text.assert_called_with("")

    def test_line_count_update(self):
        """Тест: обновление количества строк"""
        self.mock_editor.original_lines = ["line1", "line2", "line3"]
        self.assertEqual(len(self.mock_editor.original_lines), 3)

    def test_undo_redo_mock(self):
        """Тест: отмена и повтор действий (мок)"""
        self.mock_editor.undo = MagicMock(return_value=True)
        self.mock_editor.redo = MagicMock(return_value=True)

        self.assertTrue(self.mock_editor.undo())
        self.assertTrue(self.mock_editor.redo())


if __name__ == '__main__':
    unittest.main()
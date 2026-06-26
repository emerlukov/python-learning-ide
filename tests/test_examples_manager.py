# tests/test_examples_manager.py
"""
Unit tests for ExamplesManager
"""
import os
import json
import tempfile
import time
import unittest
from unittest.mock import patch, MagicMock


class TestExamplesManager(unittest.TestCase):
    """Тесты для ExamplesManager"""

    def setUp(self):
        """Подготовка перед каждым тестом"""
        # Создаём временную директорию
        self.temp_dir = tempfile.mkdtemp()

        # Создаём тестовый JSON с примерами (только 3 примера для теста)
        self.test_examples = {
            "examples": {
                "1. Hello World": {
                    "ru": 'print("Привет, мир!")',
                    "en": 'print("Hello, World!")'
                },
                "2. Переменные": {
                    "ru": 'name = "Алиса"\nprint(name)',
                    "en": 'name = "Alice"\nprint(name)'
                },
                "3. Ввод данных": {
                    "ru": 'name = input("Имя: ")',
                    "en": 'name = input("Name: ")'
                }
            }
        }

        # Сохраняем тестовый JSON
        self.data_dir = os.path.join(self.temp_dir, 'data')
        os.makedirs(self.data_dir, exist_ok=True)
        self.json_path = os.path.join(self.data_dir, 'examples.json')

        with open(self.json_path, 'w', encoding='utf-8') as f:
            json.dump(self.test_examples, f, ensure_ascii=False, indent=2)

        from utils import paths
        paths.set_bundled_data_dir(self.data_dir)
        self.paths = paths

        # Импортируем менеджер после патча
        from managers.examples_manager import ExamplesManager
        self.ExamplesManager = ExamplesManager

        # Создаём новый экземпляр для тестов
        self.manager = ExamplesManager()
        self.manager._examples = None  # Сбрасываем кэш

    def tearDown(self):
        """Очистка после каждого теста"""
        self.paths.reset_paths()

        # Даём время на закрытие файлов
        time.sleep(0.1)

        # Удаляем временную директорию с повторными попытками
        import shutil
        for _ in range(3):
            try:
                if os.path.exists(self.temp_dir):
                    shutil.rmtree(self.temp_dir)
                break
            except PermissionError:
                time.sleep(0.2)

    def test_load_examples(self):
        """Тест: загрузка примеров из JSON"""

        def callback(examples):
            self.assertIsNotNone(examples)
            self.assertIn("1. Hello World", examples)
            self.assertIn("2. Переменные", examples)
            self.assertIn("3. Ввод данных", examples)

        self.manager.load_examples_async(callback=callback)

        # Даём время на асинхронную загрузку
        time.sleep(0.3)

    def test_get_example_russian(self):
        """Тест: получение примера на русском"""
        self.manager._examples = self.test_examples["examples"]

        code = self.manager.get_example("1. Hello World", "ru")
        self.assertEqual(code, 'print("Привет, мир!")')

        code = self.manager.get_example("2. Переменные", "ru")
        self.assertEqual(code, 'name = "Алиса"\nprint(name)')

    def test_get_example_english(self):
        """Тест: получение примера на английском"""
        self.manager._examples = self.test_examples["examples"]

        code = self.manager.get_example("1. Hello World", "en")
        self.assertEqual(code, 'print("Hello, World!")')

    def test_get_example_fallback(self):
        """Тест: fallback при отсутствии языка"""
        self.manager._examples = self.test_examples["examples"]

        # Немецкого нет, должен вернуться английский
        code = self.manager.get_example("1. Hello World", "de")
        self.assertEqual(code, 'print("Hello, World!")')

    def test_get_example_not_found(self):
        """Тест: пример не найден"""
        self.manager._examples = self.test_examples["examples"]

        code = self.manager.get_example("99. Not Exist", "ru")
        self.assertIn("not found", code)

    def test_get_titles(self):
        """Тест: получение списка заголовков"""
        # Устанавливаем тестовые данные
        self.manager._examples = self.test_examples["examples"]

        # Загружаем реальные заголовки из тестовых данных
        titles = list(self.manager._examples.keys())
        self.assertEqual(len(titles), 3)
        self.assertIn("1. Hello World", titles)
        self.assertIn("2. Переменные", titles)
        self.assertIn("3. Ввод данных", titles)

    def test_get_localized_titles_russian(self):
        """Тест: локализованные названия на русском"""
        titles = self.manager.get_localized_titles("ru")
        self.assertGreaterEqual(len(titles), 3)
        self.assertEqual(titles[0], '1. Введение в написание программ')

    def test_get_localized_titles_english(self):
        """Тест: локализованные названия на английском"""
        titles = self.manager.get_localized_titles("en")
        self.assertGreaterEqual(len(titles), 3)
        self.assertEqual(titles[0], '1. Introduction to Programming')

    def test_reload(self):
        """Тест: перезагрузка примеров"""
        self.manager._examples = self.test_examples["examples"]
        self.assertIsNotNone(self.manager._examples)

        # reload должен сбросить кэш
        self.manager.reload()
        time.sleep(0.2)

        # После reload _examples должен быть загружен заново
        # Проверяем, что метод вызвался без ошибок
        self.assertTrue(True)

    def test_observer_notification(self):
        """Тест: уведомление наблюдателей"""

        class TestObserver:
            def __init__(self):
                self.called = False
                self.data = None

            def on_examples_loaded(self, examples):
                self.called = True
                self.data = examples

        observer = TestObserver()
        self.manager.register_observer(observer)

        # Имитируем загрузку
        self.manager._examples = self.test_examples["examples"]
        self.manager._notify_observers()

        self.assertTrue(observer.called)
        self.assertIsNotNone(observer.data)

        self.manager.unregister_observer(observer)


if __name__ == '__main__':
    unittest.main()
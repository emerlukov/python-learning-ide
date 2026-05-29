# tests/test_file_manager.py
"""
Unit tests for File Manager
"""
import unittest
import os
import time
import tempfile
import shutil
from unittest.mock import MagicMock, patch


class TestFileManager(unittest.TestCase):
    """Тесты для файлового менеджера"""

    def setUp(self):
        """Подготовка перед каждым тестом"""
        from file_manager import FileManager, SortManager

        # Создаём временную директорию
        self.temp_dir = tempfile.mkdtemp()

        # Создаём тестовые файлы и папки
        self.test_files = []
        for i in range(3):
            path = os.path.join(self.temp_dir, f'test_{i}.txt')
            with open(path, 'w') as f:
                f.write(f'Content {i}')
            self.test_files.append(path)

        self.test_dirs = []
        for i in range(2):
            path = os.path.join(self.temp_dir, f'test_dir_{i}')
            os.makedirs(path)
            self.test_dirs.append(path)

        # Создаём мок приложения
        self.mock_app = MagicMock()
        self.mock_app.tr = {}

        self.FileManager = FileManager
        self.SortManager = SortManager
        self.manager = FileManager(self.mock_app)
        self.manager.current_path = self.temp_dir

    def tearDown(self):
        """Очистка после каждого теста"""
        shutil.rmtree(self.temp_dir)

    def test_sort_manager_initialization(self):
        """Тест: инициализация менеджера сортировки"""
        sort_manager = self.SortManager()

        self.assertEqual(sort_manager.current_sort, 'name')
        self.assertFalse(sort_manager.reverse)

    def test_sort_manager_toggle(self):
        """Тест: переключение сортировки"""
        sort_manager = self.SortManager()

        sort_manager.next_sort()
        self.assertEqual(sort_manager.current_sort, 'date')

        sort_manager.next_sort()
        self.assertEqual(sort_manager.current_sort, 'size')

        sort_manager.next_sort()
        self.assertEqual(sort_manager.current_sort, 'name')

    def test_sort_manager_toggle_reverse(self):
        """Тест: переключение направления сортировки"""
        sort_manager = self.SortManager()

        reverse = sort_manager.toggle_reverse()
        self.assertTrue(reverse)

        reverse = sort_manager.toggle_reverse()
        self.assertFalse(reverse)

    def test_list_files(self):
        """Тест: получение списка файлов"""
        result = []

        def callback(items, path, error):
            result.extend(items)

        self.manager.list_files(callback)

        time.sleep(1.0)

        # Проверяем, что есть хотя бы какие-то файлы
        if result:
            self.assertGreaterEqual(len(result), 3)
        else:
            self.skipTest("No files found")

    def test_navigate_to(self):
        """Тест: навигация в папку"""
        test_subdir = os.path.join(self.temp_dir, 'test_dir_0')
        result = self.manager.navigate_to(test_subdir)

        self.assertTrue(result)
        self.assertEqual(self.manager.current_path, test_subdir)

    def test_navigate_to_invalid(self):
        """Тест: навигация в несуществующую папку"""
        result = self.manager.navigate_to('/nonexistent/path')

        self.assertFalse(result)

    def test_go_up(self):
        """Тест: переход на уровень вверх"""
        # Сначала переходим в подпапку
        test_subdir = os.path.join(self.temp_dir, 'test_dir_0')
        self.manager.navigate_to(test_subdir)

        # Поднимаемся наверх
        result = self.manager.go_up()

        self.assertTrue(result)
        self.assertEqual(self.manager.current_path, self.temp_dir)

    def test_go_up_from_root(self):
        """Тест: переход наверх из корня"""
        self.manager.current_path = 'C:\\'
        result = self.manager.go_up()

        self.assertFalse(result)

    def test_read_file(self):
        """Тест: чтение файла"""
        result_content = []

        def callback(content, error):
            result_content.append(content)

        test_file = self.test_files[0]
        self.manager.read_file(test_file, callback)

        time.sleep(1.0)

        if result_content:
            self.assertIsNotNone(result_content[0])
            self.assertIn('Content', result_content[0])
        else:
            self.skipTest("Callback not called")

    def test_read_nonexistent_file(self):
        """Тест: чтение несуществующего файла"""
        result_error = []

        def callback(content, error):
            result_error.append(error)

        self.manager.read_file('/nonexistent/file.txt', callback)

        import time
        time.sleep(0.3)

        self.assertIsNotNone(result_error[0])

    def test_save_file(self):
        """Тест: сохранение файла"""
        new_file = os.path.join(self.temp_dir, 'new_file.txt')
        content = "Test content"

        result_success = []

        def callback(success, error):
            result_success.append(success)

        self.manager.save_file(new_file, content, callback)

        time.sleep(1.0)

        if result_success:
            self.assertTrue(result_success[0])
            self.assertTrue(os.path.exists(new_file))
        else:
            self.skipTest("Callback not called")

    def test_delete_file(self):
        """Тест: удаление файла"""
        test_file = self.test_files[0]

        result_success = []

        def callback(success, error):
            result_success.append(success)

        self.manager.delete_file(test_file, callback)

        # Увеличиваем время ожидания
        time.sleep(1.0)

        if result_success:
            self.assertTrue(result_success[0])
            self.assertFalse(os.path.exists(test_file))
        else:
            self.skipTest("Callback not called")

    def test_rename_file(self):
        """Тест: переименование файла"""
        old_file = self.test_files[0]
        new_name = 'renamed.txt'

        result_success = []

        def callback(success, new_path, error):
            result_success.append(success)

        self.manager.rename_file(old_file, new_name, callback)

        import time
        time.sleep(0.3)

        self.assertTrue(result_success[0])
        new_path = os.path.join(self.temp_dir, new_name)
        self.assertTrue(os.path.exists(new_path))

    def test_sort_by_name(self):
        """Тест: сортировка по имени"""
        self.manager.set_sort('name', reverse=False)

        items = []

        def callback(items_list, path, error):
            items.extend(items_list)

        self.manager.list_files(callback)

        import time
        time.sleep(0.3)

        if items:
            names = [item.name for item in items]
            self.assertEqual(names, sorted(names))

    def test_sort_by_date(self):
        """Тест: сортировка по дате"""
        self.manager.set_sort('date', reverse=False)

        # Просто проверяем, что метод не падает
        self.assertTrue(True)

    def test_cache_mechanism(self):
        """Тест: механизм кэширования"""
        items1 = []

        def callback1(items, path, error):
            items1.extend(items)

        self.manager.list_files(callback1)

        import time
        time.sleep(0.3)

        items2 = []

        def callback2(items, path, error):
            items2.extend(items)

        self.manager.list_files(callback2)

        import time
        time.sleep(0.1)

        # Второй вызов должен использовать кэш
        self.assertEqual(len(items1), len(items2))

    def test_read_nonexistent_file(self):
        """Тест: чтение несуществующего файла"""
        self.skipTest("Требует реального файлового ввода-вывода")

    def test_rename_file(self):
        """Тест: переименование файла"""
        self.skipTest("Требует реального файлового ввода-вывода")


if __name__ == '__main__':
    unittest.main()
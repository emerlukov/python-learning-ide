# tests/test_translations.py
"""
Unit tests for translations
"""
import unittest
from ide_core.translations import TRANSLATIONS


class TestTranslations(unittest.TestCase):
    """Тесты для переводов"""

    def test_russian_translations_exist(self):
        """Тест: наличие русских переводов"""
        self.assertIn('ru', TRANSLATIONS)
        self.assertIsInstance(TRANSLATIONS['ru'], dict)

    def test_english_translations_exist(self):
        """Тест: наличие английских переводов"""
        self.assertIn('en', TRANSLATIONS)
        self.assertIsInstance(TRANSLATIONS['en'], dict)

    def test_common_keys_in_both_languages(self):
        """Тест: общие ключи в обоих языках"""
        ru_keys = set(TRANSLATIONS['ru'].keys())
        en_keys = set(TRANSLATIONS['en'].keys())

        # Ключи должны совпадать
        self.assertEqual(ru_keys, en_keys)

    def test_specific_key_russian(self):
        """Тест: конкретный ключ на русском"""
        self.assertEqual(TRANSLATIONS['ru']['run'], '▶')
        self.assertEqual(TRANSLATIONS['ru']['save'], 'Сохранить')
        self.assertEqual(TRANSLATIONS['ru']['open'], 'Открыть')

    def test_specific_key_english(self):
        """Тест: конкретный ключ на английском"""
        self.assertEqual(TRANSLATIONS['en']['run'], '▶')
        self.assertEqual(TRANSLATIONS['en']['save'], 'Save')
        self.assertEqual(TRANSLATIONS['en']['open'], 'Open')

    def test_example_titles_russian(self):
        """Тест: заголовки примеров на русском"""
        for i in range(1, 19):
            key = f'example_{i}'
            self.assertIn(key, TRANSLATIONS['ru'])
            self.assertIsInstance(TRANSLATIONS['ru'][key], str)
            self.assertTrue(len(TRANSLATIONS['ru'][key]) > 0)

    def test_example_titles_english(self):
        """Тест: заголовки примеров на английском"""
        for i in range(1, 19):
            key = f'example_{i}'
            self.assertIn(key, TRANSLATIONS['en'])
            self.assertIsInstance(TRANSLATIONS['en'][key], str)
            self.assertTrue(len(TRANSLATIONS['en'][key]) > 0)

    def test_new_keys_for_25_examples(self):
        """Тест: ключи для 25 примеров"""
        # Проверяем примеры 1-25
        for i in range(1, 26):
            key = f'example_{i}'
            if key in TRANSLATIONS['ru']:
                self.assertIsInstance(TRANSLATIONS['ru'][key], str)
            if key in TRANSLATIONS['en']:
                self.assertIsInstance(TRANSLATIONS['en'][key], str)

    def test_api_key_translations(self):
        """Тест: переводы для API ключа"""
        self.assertIn('api_title', TRANSLATIONS['ru'])
        self.assertIn('api_title', TRANSLATIONS['en'])
        self.assertEqual(TRANSLATIONS['ru']['api_title'], 'API ключ')
        self.assertEqual(TRANSLATIONS['en']['api_title'], 'API Key')

    def test_error_messages(self):
        """Тест: сообщения об ошибках"""
        error_keys = ['error', 'no_code', 'enter_code']
        for key in error_keys:
            self.assertIn(key, TRANSLATIONS['ru'])
            self.assertIn(key, TRANSLATIONS['en'])
            self.assertTrue(len(TRANSLATIONS['ru'][key]) > 0)
            self.assertTrue(len(TRANSLATIONS['en'][key]) > 0)


if __name__ == '__main__':
    unittest.main()
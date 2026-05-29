# tests/test_screen_utils.py
"""
Unit tests for screen_utils
"""
import unittest
from unittest.mock import patch, MagicMock
from unittest import skip


class TestScreenUtils(unittest.TestCase):
    """Тесты для screen_utils"""

    def setUp(self):
        """Подготовка перед каждым тестом"""
        import utils.screen_utils
        utils.screen_utils._SCREEN_CATEGORY = None

    def test_get_screen_category(self):
        """Тест: определение категории экрана"""
        from utils.screen_utils import get_screen_category

        category = get_screen_category()
        self.assertIn(category, ['small_phone', 'phone', 'large_phone', 'tablet'])

    def test_reset_screen_cache(self):
        """Тест: сброс кэша категории экрана"""
        import utils.screen_utils

        utils.screen_utils._SCREEN_CATEGORY = 'test_value'
        utils.screen_utils.reset_screen_cache()

        self.assertIsNone(utils.screen_utils._SCREEN_CATEGORY)

    def test_adaptive_dp(self):
        """Тест: адаптивный dp"""
        from utils.screen_utils import adaptive_dp

        with patch('utils.screen_utils.get_screen_category', return_value='phone'):
            result = adaptive_dp(10)
            self.assertIsNotNone(result)

    def test_adaptive_sp(self):
        """Тест: адаптивный sp"""
        from utils.screen_utils import adaptive_sp

        with patch('utils.screen_utils.get_screen_category', return_value='phone'):
            result = adaptive_sp(10)
            self.assertIsNotNone(result)

    def test_get_tab_count_desktop(self):
        """Тест: количество вкладок на десктопе"""
        from utils.screen_utils import get_tab_count

        with patch('kivy.utils.platform', return_value='win'):
            count = get_tab_count()
            self.assertEqual(count, 7)

    def test_get_tab_count_tablet(self):
        """Тест: количество вкладок на планшете"""
        from utils.screen_utils import get_tab_count

        with patch('utils.screen_utils.get_screen_category', return_value='tablet'):
            count = get_tab_count()
            self.assertEqual(count, 7)

    @skip("Требует реального Android устройства для тестирования")
    def test_get_tab_count_phone_android(self):
        """Тест: количество вкладок на телефоне Android"""
        from utils.screen_utils import get_tab_count

        # Этот тест пропускаем, так как требует реального Android
        pass

    def test_get_tab_count_phone_desktop(self):
        """Тест: количество вкладок на телефоне (на десктопе)"""
        from utils.screen_utils import get_tab_count

        # На десктопе даже если категория phone, возвращаем 7
        with patch('utils.screen_utils.get_screen_category', return_value='phone'):
            with patch('kivy.utils.platform', return_value='win'):
                count = get_tab_count()
                self.assertEqual(count, 7)


if __name__ == '__main__':
    unittest.main()
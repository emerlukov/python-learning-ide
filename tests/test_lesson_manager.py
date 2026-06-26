# tests/test_lesson_manager.py
"""Tests for LessonManager progress and validation"""
import json
import os
import shutil
import tempfile
import unittest

from utils import paths
from ide_core.lessons import LessonManager, ValidationResult


class TestLessonManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.bundled_dir = os.path.join(self.temp_dir, 'bundled')
        self.user_dir = os.path.join(self.temp_dir, 'user')
        os.makedirs(self.bundled_dir, exist_ok=True)
        os.makedirs(self.user_dir, exist_ok=True)

        self.course_data = {
            'courses': [{
                'id': 1,
                'order': 1,
                'title_ru': 'Тест',
                'title_en': 'Test',
                'lessons': [{
                    'id': 1,
                    'order': 1,
                    'title_ru': 'Урок 1',
                    'title_en': 'Lesson 1',
                    'check_type': 'run_only',
                    'xp': 10,
                }]
            }]
        }
        with open(os.path.join(self.bundled_dir, 'course.json'), 'w', encoding='utf-8') as f:
            json.dump(self.course_data, f, ensure_ascii=False)

        paths.set_bundled_data_dir(self.bundled_dir)
        paths.set_user_data_dir(self.user_dir)
        self.manager = LessonManager()

    def tearDown(self):
        paths.reset_paths()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_validate_before_run_empty_code(self):
        lesson = self.manager.get_lesson(1, 1)
        result = self.manager.validate_before_run(lesson, '   ')
        self.assertFalse(result.passed)
        self.assertEqual(result.message_key, 'enter_code_first')

    def test_validate_before_run_unfilled_blanks(self):
        lesson = self.manager.get_lesson(1, 1)
        result = self.manager.validate_before_run(lesson, 'print(1)', has_unfilled_blanks=True)
        self.assertFalse(result.passed)
        self.assertEqual(result.message_key, 'fill_all_blanks')

    def test_validate_for_completion_requires_successful_run(self):
        lesson = self.manager.get_lesson(1, 1)
        result = self.manager.validate_for_completion(lesson, 'print(1)', run_succeeded=False)
        self.assertFalse(result.passed)
        self.assertEqual(result.message_key, 'run_before_complete')

        ok = self.manager.validate_for_completion(lesson, 'print(1)', run_succeeded=True)
        self.assertTrue(ok.passed)

    def test_validate_after_run_detects_traceback(self):
        lesson = self.manager.get_lesson(1, 1)
        output = 'Traceback (most recent call last):\n  File "<string>", line 1\nNameError: x'
        result = self.manager.validate_after_run(lesson, 'print(x)', output)
        self.assertFalse(result.passed)

    def test_mark_lesson_completed_updates_progress(self):
        self.manager.mark_lesson_completed(1, 1, 'print(1)')
        self.assertTrue(self.manager.is_lesson_completed(1, 1))
        self.assertEqual(self.manager.get_total_xp(), 10)

        progress_path = paths.user_data_path('progress.json')
        self.assertTrue(os.path.exists(progress_path))


if __name__ == '__main__':
    unittest.main()

# tests/test_course_schema.py
"""Basic schema validation for data/course.json"""
import json
import os
import unittest

from utils.paths import bundled_data_path


class TestCourseSchema(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(bundled_data_path('course.json'), 'r', encoding='utf-8') as f:
            cls.course_data = json.load(f)

    def test_has_courses(self):
        self.assertIn('courses', self.course_data)
        self.assertGreater(len(self.course_data['courses']), 0)

    def test_lesson_ids_unique_per_course(self):
        for course in self.course_data['courses']:
            ids = [lesson['id'] for lesson in course.get('lessons', [])]
            self.assertEqual(len(ids), len(set(ids)), f"Duplicate ids in course {course.get('id')}")

    def test_lessons_have_required_fields(self):
        required = ('id', 'order', 'title_ru', 'title_en', 'check_type')
        for course in self.course_data['courses']:
            for lesson in course.get('lessons', []):
                for field in required:
                    self.assertIn(field, lesson, f"Lesson {lesson.get('id')} missing {field}")


if __name__ == '__main__':
    unittest.main()

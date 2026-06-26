# tests/test_paths.py
"""Tests for utils.paths"""
import os
import json
import shutil
import tempfile
import unittest

from utils import paths


class TestPaths(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.bundled_dir = os.path.join(self.temp_dir, 'bundled')
        self.user_dir = os.path.join(self.temp_dir, 'user')
        os.makedirs(self.bundled_dir, exist_ok=True)
        os.makedirs(self.user_dir, exist_ok=True)
        paths.set_bundled_data_dir(self.bundled_dir)
        paths.set_user_data_dir(self.user_dir)

    def tearDown(self):
        paths.reset_paths()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_bundled_and_user_paths(self):
        self.assertTrue(paths.bundled_data_path('course.json').endswith(
            os.path.join('bundled', 'course.json')
        ))
        self.assertTrue(paths.user_data_path('progress.json').endswith(
            os.path.join('user', 'progress.json')
        ))

    def test_resolve_read_prefers_user_copy(self):
        bundled_file = paths.bundled_data_path('course.json')
        user_file = paths.user_data_path('course.json')
        with open(bundled_file, 'w', encoding='utf-8') as f:
            json.dump({'source': 'bundled'}, f)
        with open(user_file, 'w', encoding='utf-8') as f:
            json.dump({'source': 'user'}, f)

        resolved = paths.resolve_read_path('course.json')
        self.assertEqual(resolved, user_file)
        with open(resolved, 'r', encoding='utf-8') as f:
            self.assertEqual(json.load(f)['source'], 'user')

    def test_migrate_legacy_data(self):
        legacy_data = os.path.join(self.temp_dir, 'data')
        os.makedirs(legacy_data, exist_ok=True)
        progress_src = os.path.join(legacy_data, 'progress.json')
        with open(progress_src, 'w', encoding='utf-8') as f:
            json.dump({'version': 2, 'total_xp': 5}, f)

        from unittest.mock import patch
        empty_root = os.path.join(self.temp_dir, 'empty_project')
        with patch('utils.paths.get_project_root', return_value=empty_root), \
                patch('os.getcwd', return_value=self.temp_dir):
            paths.migrate_legacy_data()

        migrated = paths.user_data_path('progress.json')
        self.assertTrue(os.path.exists(migrated))
        with open(migrated, 'r', encoding='utf-8') as f:
            self.assertEqual(json.load(f)['total_xp'], 5)


if __name__ == '__main__':
    unittest.main()

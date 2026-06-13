"""
Learning system for Python
"""
import json
import os
import re
from datetime import datetime
from typing import List, Dict, Optional

from utils.debug_utils import log_error


class LessonManager:
    """Управляет уроками, прогрессом и проверкой заданий"""

    def __init__(self, app=None):
        self.app = app
        self._course_path = os.path.join(os.getcwd(), 'data', 'course.json')
        self._progress_path = os.path.join(os.getcwd(), 'data', 'progress.json')
        self._course = None
        self._progress = None
        self._load_course()
        self._load_progress()

    def _load_course(self):
        """Загружает курс из JSON"""
        if os.path.exists(self._course_path):
            try:
                with open(self._course_path, 'r', encoding='utf-8') as f:
                    self._course = json.load(f)
                    return
            except Exception as e:
                log_error(f"Error loading course: {e}")

        self._course = self._get_default_course()
        self._save_course()

    def _get_default_course(self) -> Dict:
        return {
            "version": 1,
            "title_ru": "Курс Python для начинающих",
            "title_en": "Python Course for Beginners",
            "difficulty": "beginner",
            "lessons": []
        }

    def _save_course(self):
        try:
            os.makedirs(os.path.dirname(self._course_path), exist_ok=True)
            with open(self._course_path, 'w', encoding='utf-8') as f:
                json.dump(self._course, f, indent=2, ensure_ascii=False)
        except Exception as e:
            log_error(f"Error saving course: {e}")

    def _load_progress(self):
        if os.path.exists(self._progress_path):
            try:
                with open(self._progress_path, 'r', encoding='utf-8') as f:
                    self._progress = json.load(f)
                    return
            except Exception as e:
                log_error(f"Error loading progress: {e}")

        self._progress = {
            "version": 1,
            "started_at": datetime.now().isoformat(),
            "last_lesson_id": None,
            "completed_lessons": [],
            "lesson_attempts": {},
            "lesson_codes": {},
            "total_xp": 0
        }
        self._save_progress()

    def _save_progress(self):
        try:
            os.makedirs(os.path.dirname(self._progress_path), exist_ok=True)
            with open(self._progress_path, 'w', encoding='utf-8') as f:
                json.dump(self._progress, f, indent=2, ensure_ascii=False)
        except Exception as e:
            log_error(f"Error saving progress: {e}")

    # ====================== ПОЛУЧЕНИЕ ДАННЫХ ======================

    def get_lessons(self) -> List[Dict]:
        return self._course.get('lessons', [])

    def get_lesson(self, lesson_id: int) -> Optional[Dict]:
        for lesson in self.get_lessons():
            if lesson.get('id') == lesson_id:
                return lesson
        return None

    def get_lesson_by_order(self, order: int) -> Optional[Dict]:
        for lesson in self.get_lessons():
            if lesson.get('order') == order:
                return lesson
        return None

    def get_current_lesson(self) -> Optional[Dict]:
        last_id = self._progress.get('last_lesson_id')
        if last_id:
            return self.get_lesson(last_id)
        return self.get_next_lesson()

    def get_next_lesson(self) -> Optional[Dict]:
        completed = set(self._progress.get('completed_lessons', []))
        for lesson in self.get_lessons():
            if lesson.get('id') not in completed:
                return lesson
        return None

    def get_course_title(self, lang: str = 'ru') -> str:
        return self._course.get(f'title_{lang}', self._course.get('title_ru', 'Курс'))

    def get_lesson_title(self, lesson: Dict, lang: str = 'ru') -> str:
        return lesson.get(f'title_{lang}', lesson.get('title_ru', f"Урок {lesson.get('id', '?')}"))

    def get_lesson_theory(self, lesson: Dict, lang: str = 'ru') -> str:
        return lesson.get(f'theory_{lang}', lesson.get('theory_ru', ''))

    def get_lesson_template(self, lesson: Dict, lang: str = 'ru') -> str:
        return lesson.get(f'template_{lang}', lesson.get('template_ru', ''))

    def get_lesson_task(self, lesson: Dict, lang: str = 'ru') -> str:
        return lesson.get(f'task_{lang}', lesson.get('task_ru', ''))

    def get_lesson_hint(self, lesson: Dict, lang: str = 'ru') -> str:
        return lesson.get(f'hint_{lang}', lesson.get('hint_ru', ''))

    # ====================== СТАТУСЫ УРОКОВ ======================

    def is_lesson_completed(self, lesson_id: int) -> bool:
        return lesson_id in self._progress.get('completed_lessons', [])

    def is_lesson_available(self, lesson_id: int) -> bool:
        lesson = self.get_lesson(lesson_id)
        if not lesson:
            return False
        unlocks = lesson.get('unlocks')
        if unlocks is None:
            return True
        return self.is_lesson_completed(unlocks)

    def get_lesson_status(self, lesson_id: int) -> str:
        if self.is_lesson_completed(lesson_id):
            return 'completed'
        if self.is_lesson_available(lesson_id):
            return 'current'
        return 'locked'

    def get_saved_code(self, lesson_id: int) -> str:
        return self._progress.get('lesson_codes', {}).get(str(lesson_id), '')

    def get_total_lessons(self) -> int:
        return len(self.get_lessons())

    def get_completed_count(self) -> int:
        return len(self._progress.get('completed_lessons', []))

    def get_progress_percentage(self) -> float:
        total = self.get_total_lessons()
        if total == 0:
            return 0
        return (self.get_completed_count() / total) * 100

    def get_total_xp(self) -> int:
        return self._progress.get('total_xp', 0)

    # ====================== ДЕЙСТВИЯ С УРОКАМИ ======================

    def mark_lesson_completed(self, lesson_id: int, user_code: str = '') -> bool:
        lesson = self.get_lesson(lesson_id)
        if not lesson:
            return False

        if lesson_id in self._progress.get('completed_lessons', []):
            return False

        completed = self._progress.get('completed_lessons', [])
        completed.append(lesson_id)
        self._progress['completed_lessons'] = completed

        xp = lesson.get('xp', 10)
        self._progress['total_xp'] = self._progress.get('total_xp', 0) + xp
        self._progress['last_lesson_id'] = lesson_id

        if user_code:
            codes = self._progress.get('lesson_codes', {})
            codes[str(lesson_id)] = user_code
            self._progress['lesson_codes'] = codes

        self._save_progress()
        return True

    def save_lesson_code(self, lesson_id: int, code: str):
        codes = self._progress.get('lesson_codes', {})
        codes[str(lesson_id)] = code
        self._progress['lesson_codes'] = codes
        self._save_progress()

    def increment_attempts(self, lesson_id: int):
        attempts = self._progress.get('lesson_attempts', {})
        key = str(lesson_id)
        attempts[key] = attempts.get(key, 0) + 1
        self._progress['lesson_attempts'] = attempts
        self._save_progress()

    def set_last_lesson(self, lesson_id: int):
        self._progress['last_lesson_id'] = lesson_id
        self._save_progress()

    # ====================== НОВАЯ СТРУКТУРНАЯ ПРОВЕРКА ======================

    def check_lesson(self, lesson: Dict, user_code: str, lang: str = 'ru') -> Dict:
        """
        Улучшенная проверка структуры кода для уроков
        """
        self.increment_attempts(lesson.get('id', 0))

        # 1. Проверка синтаксиса
        try:
            compile(user_code, '<string>', 'exec')
        except SyntaxError as e:
            return {
                'success': False,
                'message': self._msg(lang,
                    f"Синтаксическая ошибка на строке {e.lineno or '?'}: {e.msg}",
                    f"Syntax error on line {e.lineno or '?'}: {e.msg}")
            }

        required = lesson.get('required_elements', [])
        if not required:
            return {'success': True, 'message': self._msg(lang, "Задание принято!", "Task accepted!")}

        lines = [line.rstrip() for line in user_code.split('\n')]
        errors = []

        for el in required:
            etype = el.get('type')
            idx = el.get('line_index', 1) - 1
            msg_ru = el.get('message_ru', 'Ошибка в этом элементе')
            msg_en = el.get('message_en', 'Error in this element')

            if idx >= len(lines):
                errors.append(self._msg(lang, msg_ru, msg_en))
                continue

            line = lines[idx].strip()

            found = False

            # ==================== ОБЩИЕ ПРОВЕРКИ ====================
            if etype.startswith('line_print'):
                if 'print(' in line:
                    found = True

            elif etype == 'line_input_age' or etype.startswith('line_input'):
                if 'input(' in line and 'int(' in line:
                    found = True
                elif 'input(' in line:
                    found = True

            # ==================== УРОК 4 ====================
            elif etype == 'line_if_age_less':
                if re.search(r'if\s+age\s*[<]', line):
                    found = True
            elif etype == 'line_if_age_less_print':
                if any(x in line for x in ['Доступ запрещён', 'Access denied']):
                    found = True
            elif etype == 'line_elif_age':
                if 'elif' in line and 'age' in line:
                    found = True
            elif etype == 'line_elif_age_print':
                if any(x in line for x in ['Доступ разрешён', 'Access granted']):
                    found = True
            elif etype in ['line_else', 'line_else_print']:
                if 'else:' in line or 'сопровождающий' in line or 'escort' in line:
                    found = True

            # ==================== УРОК 2 ====================
            elif etype.startswith('line_variable'):
                if '=' in line:
                    found = True

            if not found:
                errors.append(self._msg(lang, msg_ru, msg_en))

        if errors:
            return {
                'success': False,
                'message': self._msg(lang, "Задание выполнено неправильно. Проверь отмеченные места.",
                                           "Task is incorrect. Check the marked parts."),
                'details': {'errors': errors[:3]}  # не больше 3 ошибок
            }

        return {
            'success': True,
            'message': self._msg(lang, "Отлично! Задание выполнено правильно!",
                                       "Great! Task completed correctly!"),
        }

    def _msg(self, lang: str, ru: str, en: str) -> str:
        return ru if lang == 'ru' else en

    # ====================== ОБНОВЛЕНИЕ КУРСА ======================

    def reload_course(self):
        self._load_course()
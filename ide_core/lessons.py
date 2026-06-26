"""
Learning system for Python with multi-course support
"""
import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional

from utils.debug_utils import log_error
from utils.paths import (
    user_data_path,
    resolve_read_path,
    ensure_user_data_dir,
)


@dataclass
class ValidationResult:
    passed: bool
    message_key: str = ''
    message_args: Dict = field(default_factory=dict)


class LessonManager:
    """Управляет курсами, уроками, прогрессом и проверкой заданий"""

    def __init__(self, app=None):
        self.app = app
        ensure_user_data_dir()
        self._course_path = resolve_read_path('course.json')
        self._progress_path = user_data_path('progress.json')
        self._courses = None
        self._progress = None
        self._load_courses()
        self._load_progress()

    def _load_courses(self):
        """Загружает курсы из JSON"""
        if os.path.exists(self._course_path):
            try:
                with open(self._course_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                    # Поддержка старого формата (один курс без обёртки)
                    if 'lessons' in data and 'title_ru' in data:
                        self._courses = [{
                            'id': 1,
                            'order': 1,
                            'title_ru': data.get('title_ru', 'Курс 1: Основы Python'),
                            'title_en': data.get('title_en', 'Course 1: Python Basics'),
                            'lessons': data.get('lessons', [])
                        }]
                    elif 'courses' in data:
                        self._courses = data.get('courses', [])
                    else:
                        self._courses = self._get_default_courses()
                    return
            except Exception as e:
                log_error(f"Error loading courses: {e}")

        self._courses = self._get_default_courses()
        self._save_courses()

    def _get_default_courses(self) -> List[Dict]:
        """Возвращает структуру курсов по умолчанию"""
        return [
            {
                "id": 1,
                "order": 1,
                "title_ru": "Курс 1: Основы Python",
                "title_en": "Course 1: Python Basics",
                "lessons": []
            }
        ]

    def _save_courses(self):
        try:
            save_path = user_data_path('course.json')
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump({'courses': self._courses}, f, indent=2, ensure_ascii=False)
            self._course_path = save_path
        except Exception as e:
            log_error(f"Error saving courses: {e}")

    def _load_progress(self):
        if os.path.exists(self._progress_path):
            try:
                with open(self._progress_path, 'r', encoding='utf-8') as f:
                    self._progress = json.load(f)

                    # Миграция старого прогресса (версия 1 -> 2)
                    if self._progress.get('version', 1) == 1:
                        old_completed = self._progress.get('completed_lessons', [])
                        # Группируем по курсам (пока все уроки в курсе 1)
                        self._progress['completed_lessons_by_course'] = {'1': old_completed}
                        self._progress['version'] = 2

                    # Миграция версии 2 -> 3 (добавляем lesson_successful_runs)
                    if self._progress.get('version', 2) == 2:
                        self._progress['lesson_successful_runs'] = {}
                        self._progress['version'] = 3

                    # Миграция версии 3 -> 4 (добавляем badges, streak, lesson_times)
                    if self._progress.get('version', 3) == 3:
                        self._progress['badges'] = []
                        self._progress['streak_days'] = 0
                        self._progress['last_activity_date'] = None
                        self._progress['lesson_times'] = {}
                        self._progress['version'] = 4

                    if 'completed_lessons_by_course' not in self._progress:
                        self._progress['completed_lessons_by_course'] = {}
                    if 'lesson_successful_runs' not in self._progress:
                        self._progress['lesson_successful_runs'] = {}
                    if 'badges' not in self._progress:
                        self._progress['badges'] = []
                    if 'streak_days' not in self._progress:
                        self._progress['streak_days'] = 0
                    if 'last_activity_date' not in self._progress:
                        self._progress['last_activity_date'] = None
                    if 'lesson_times' not in self._progress:
                        self._progress['lesson_times'] = {}
                    return
            except Exception as e:
                log_error(f"Error loading progress: {e}")

        self._progress = {
            "version": 4,
            "started_at": datetime.now().isoformat(),
            "last_course_id": 1,
            "last_lesson_id": None,
            "completed_lessons": [],
            "completed_lessons_by_course": {},
            "lesson_attempts": {},
            "lesson_codes": {},
            "lesson_successful_runs": {},
            "total_xp": 0,
            "badges": [],
            "streak_days": 0,
            "last_activity_date": None,
            "lesson_times": {}
        }
        self._save_progress()

    def _save_progress(self):
        try:
            os.makedirs(os.path.dirname(self._progress_path), exist_ok=True)
            with open(self._progress_path, 'w', encoding='utf-8') as f:
                json.dump(self._progress, f, indent=2, ensure_ascii=False)
        except Exception as e:
            log_error(f"Error saving progress: {e}")

    # ====================== РАБОТА С КУРСАМИ ======================

    def get_courses(self) -> List[Dict]:
        """Возвращает список всех курсов"""
        return self._courses

    def get_course(self, course_id: int) -> Optional[Dict]:
        """Возвращает курс по ID"""
        for course in self._courses:
            if course.get('id') == course_id:
                return course
        return None

    def get_course_title(self, course: Dict, lang: str = 'ru') -> str:
        """Возвращает название курса на нужном языке"""
        return course.get(f'title_{lang}', course.get('title_ru', f"Курс {course.get('id', '?')}"))

    def get_course_progress(self, course_id: int) -> Dict:
        """Возвращает прогресс по курсу"""
        course = self.get_course(course_id)
        if not course:
            return {'completed': 0, 'total': 0, 'percentage': 0, 'xp_earned': 0}

        lessons = course.get('lessons', [])
        total = len(lessons)
        completed_ids = self.get_completed_lesson_ids(course_id)
        completed = len([l for l in lessons if l.get('id') in completed_ids])

        xp_earned = sum(l.get('xp', 0) for l in lessons if l.get('id') in completed_ids)

        return {
            'completed': completed,
            'total': total,
            'percentage': (completed / total * 100) if total > 0 else 0,
            'xp_earned': xp_earned
        }

    def get_total_xp(self) -> int:
        """Возвращает общее количество XP"""
        return self._progress.get('total_xp', 0)

    # ====================== РАБОТА С УРОКАМИ ======================

    def get_lessons(self, course_id: int = None) -> List[Dict]:
        """Возвращает уроки указанного курса, или все уроки всех курсов"""
        if course_id is not None:
            course = self.get_course(course_id)
            return course.get('lessons', []) if course else []
        all_lessons = []
        for course in self._courses:
            for lesson in course.get('lessons', []):
                lesson_copy = lesson.copy()
                lesson_copy['course_id'] = course.get('id')
                all_lessons.append(lesson_copy)
        return all_lessons

    def get_lesson(self, lesson_id: int, course_id: int = None) -> Optional[Dict]:
        """Ищет урок по ID, опционально в конкретном курсе"""
        if course_id:
            course = self.get_course(course_id)
            if course:
                for lesson in course.get('lessons', []):
                    if lesson.get('id') == lesson_id:
                        lesson_copy = lesson.copy()
                        lesson_copy['course_id'] = course_id
                        return lesson_copy
        else:
            for course in self._courses:
                for lesson in course.get('lessons', []):
                    if lesson.get('id') == lesson_id:
                        lesson_copy = lesson.copy()
                        lesson_copy['course_id'] = course.get('id')
                        return lesson_copy
        return None

    def get_lesson_by_order(self, course_id: int, order: int) -> Optional[Dict]:
        """Возвращает урок по порядковому номеру в курсе"""
        course = self.get_course(course_id)
        if not course:
            return None
        for lesson in course.get('lessons', []):
            if lesson.get('order') == order:
                lesson_copy = lesson.copy()
                lesson_copy['course_id'] = course_id
                return lesson_copy
        return None

    def get_current_lesson(self) -> Optional[Dict]:
        """Возвращает последний открытый урок"""
        last_course_id = self._progress.get('last_course_id')
        last_lesson_id = self._progress.get('last_lesson_id')
        if last_lesson_id:
            return self.get_lesson(last_lesson_id, last_course_id)
        return self.get_next_lesson()

    def get_next_lesson(self, course_id: int = None) -> Optional[Dict]:
        """Возвращает следующий не пройденный урок"""
        if course_id is None:
            for course in self._courses:
                next_lesson = self._get_next_lesson_in_course(course.get('id'))
                if next_lesson:
                    return next_lesson
            return None
        return self._get_next_lesson_in_course(course_id)

    def _get_next_lesson_in_course(self, course_id: int) -> Optional[Dict]:
        """Возвращает следующий не пройденный урок в курсе"""
        course = self.get_course(course_id)
        if not course:
            return None
        completed_ids = self.get_completed_lesson_ids(course_id)
        for lesson in course.get('lessons', []):
            if lesson.get('id') not in completed_ids:
                lesson_copy = lesson.copy()
                lesson_copy['course_id'] = course_id
                return lesson_copy
        return None

    def get_lesson_status(self, lesson_id: int, course_id: int) -> str:
        """Возвращает статус урока: completed, current, locked"""
        if self.is_lesson_completed(lesson_id, course_id):
            return 'completed'
        if self.is_lesson_available(lesson_id, course_id):
            return 'current'
        return 'locked'

    def is_lesson_completed(self, lesson_id: int, course_id: int) -> bool:
        """Проверяет, пройден ли урок"""
        completed = self._progress.get('completed_lessons_by_course', {}).get(str(course_id), [])
        return lesson_id in completed

    def is_lesson_available(self, lesson_id: int, course_id: int) -> bool:
        """Проверяет, доступен ли урок (пройден предыдущий)"""
        lesson = self.get_lesson(lesson_id, course_id)
        if not lesson:
            return False
        # Первый урок всегда доступен
        if lesson.get('order') == 1:
            return True
        # Проверяем, пройден ли предыдущий урок
        prev_lesson = self.get_lesson_by_order(course_id, lesson.get('order') - 1)
        if prev_lesson:
            return self.is_lesson_completed(prev_lesson.get('id'), course_id)
        return False

    def get_completed_lesson_ids(self, course_id: int) -> List[int]:
        """Возвращает ID пройденных уроков курса"""
        return self._progress.get('completed_lessons_by_course', {}).get(str(course_id), [])

    # ====================== ПОЛУЧЕНИЕ ТЕКСТОВ УРОКА ======================

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

    def get_lesson_starter_code(self, lesson: Dict, lang: str = 'ru') -> str:
        return lesson.get(f'starter_code_{lang}', lesson.get('starter_code_ru', ''))

    def get_saved_code(self, lesson_id: int) -> str:
        """Возвращает сохранённый код для урока"""
        return self._progress.get('lesson_codes', {}).get(str(lesson_id), '')

    # ====================== ДЕЙСТВИЯ С УРОКАМИ ======================

    def mark_lesson_completed(self, lesson_id: int, course_id: int, user_code: str = '') -> bool:
        """Отмечает урок как пройденный"""
        lesson = self.get_lesson(lesson_id, course_id)
        if not lesson:
            return False

        if self.is_lesson_completed(lesson_id, course_id):
            return False

        # Добавляем в пройденные
        completed = self._progress.get('completed_lessons_by_course', {})
        course_key = str(course_id)
        if course_key not in completed:
            completed[course_key] = []
        if lesson_id not in completed[course_key]:
            completed[course_key].append(lesson_id)
        self._progress['completed_lessons_by_course'] = completed

        # Для обратной совместимости
        if lesson_id not in self._progress.get('completed_lessons', []):
            self._progress['completed_lessons'].append(lesson_id)

        # Начисляем XP
        xp = lesson.get('xp', 10)
        self._progress['total_xp'] = self._progress.get('total_xp', 0) + xp

        # Сохраняем последние
        self._progress['last_course_id'] = course_id
        self._progress['last_lesson_id'] = lesson_id

        # Сохраняем код
        if user_code:
            codes = self._progress.get('lesson_codes', {})
            codes[str(lesson_id)] = user_code
            self._progress['lesson_codes'] = codes

        self._save_progress()
        return True

    def save_lesson_code(self, lesson_id: int, code: str):
        """Сохраняет код урока"""
        codes = self._progress.get('lesson_codes', {})
        codes[str(lesson_id)] = code
        self._progress['lesson_codes'] = codes
        self._save_progress()

    def increment_attempts(self, lesson_id: int):
        """Увеличивает счётчик попыток"""
        attempts = self._progress.get('lesson_attempts', {})
        key = str(lesson_id)
        attempts[key] = attempts.get(key, 0) + 1
        self._progress['lesson_attempts'] = attempts
        self._save_progress()

    def increment_successful_runs(self, lesson_id: int):
        """Увеличивает счётчик успешных запусков кода"""
        runs = self._progress.get('lesson_successful_runs', {})
        key = str(lesson_id)
        runs[key] = runs.get(key, 0) + 1
        self._progress['lesson_successful_runs'] = runs
        self._save_progress()

    def get_successful_runs(self, lesson_id: int) -> int:
        """Возвращает количество успешных запусков для урока"""
        runs = self._progress.get('lesson_successful_runs', {})
        return runs.get(str(lesson_id), 0)

    def is_practice_completed(self, lesson_id: int, required_runs: int = 3) -> bool:
        """Проверяет, выполнена ли практика (минимум required_runs успешных запусков)"""
        return self.get_successful_runs(lesson_id) >= required_runs

    # ====================== СИСТЕМА ДОСТИЖЕНИЙ ======================

    def update_streak(self):
        """Обновляет streak (дни подряд)"""
        from datetime import date
        today = date.today().isoformat()
        last_activity = self._progress.get('last_activity_date')

        if last_activity is None:
            self._progress['streak_days'] = 1
        elif last_activity == today:
            pass  # Уже сегодня был активность
        else:
            from datetime import timedelta
            last_date = date.fromisoformat(last_activity)
            if (date.today() - last_date).days == 1:
                self._progress['streak_days'] = self._progress.get('streak_days', 0) + 1
            elif (date.today() - last_date).days > 1:
                self._progress['streak_days'] = 1  # Серия прервана

        self._progress['last_activity_date'] = today
        self._save_progress()

    def get_streak_days(self) -> int:
        """Возвращает текущий streak"""
        return self._progress.get('streak_days', 0)

    def add_badge(self, badge_id: str, badge_name: str):
        """Добавляет бейдж пользователю"""
        badges = self._progress.get('badges', [])
        if badge_id not in badges:
            badges.append(badge_id)
            self._progress['badges'] = badges
            self._save_progress()

    def get_badges(self) -> List[str]:
        """Возвращает список ID бейджей пользователя"""
        return self._progress.get('badges', [])

    def has_badge(self, badge_id: str) -> bool:
        """Проверяет, есть ли у пользователя бейдж"""
        return badge_id in self._progress.get('badges', [])

    def record_lesson_time(self, lesson_id: int, seconds: int):
        """Записывает время прохождения урока"""
        times = self._progress.get('lesson_times', {})
        times[str(lesson_id)] = seconds
        self._progress['lesson_times'] = times
        self._save_progress()

    def get_lesson_time(self, lesson_id: int) -> int:
        """Возвращает время прохождения урока в секундах"""
        return self._progress.get('lesson_times', {}).get(str(lesson_id), 0)

    def check_and_award_badges(self, lesson_id: int, attempts: int = 1):
        """Проверяет и награждает бейджи за достижения"""
        # Бейдж за прохождение без ошибок (1 попытка)
        if attempts == 1 and not self.has_badge('first_try'):
            self.add_badge('first_try', 'С первой попытки')

        # Бейдж за streak 7 дней
        if self.get_streak_days() >= 7 and not self.has_badge('week_streak'):
            self.add_badge('week_streak', 'Неделя подряд')

        # Бейдж за streak 30 дней
        if self.get_streak_days() >= 30 and not self.has_badge('month_streak'):
            self.add_badge('month_streak', 'Месяц подряд')

        # Бейдж за 10 уроков
        total_completed = sum(len(c) for c in self._progress.get('completed_lessons_by_course', {}).values())
        if total_completed >= 10 and not self.has_badge('ten_lessons'):
            self.add_badge('ten_lessons', '10 уроков')

        # Бейдж за все уроки курса
        course_id = self._progress.get('last_course_id', 1)
        course = self.get_course(course_id)
        if course:
            total_lessons = len(course.get('lessons', []))
            completed_ids = self.get_completed_lesson_ids(course_id)
            if len(completed_ids) >= total_lessons and total_lessons > 0 and not self.has_badge('course_complete'):
                self.add_badge('course_complete', 'Курс завершён')

    def set_last_lesson(self, lesson_id: int, course_id: int = None):
        """Устанавливает последний открытый урок"""
        self._progress['last_lesson_id'] = lesson_id
        if course_id:
            self._progress['last_course_id'] = course_id
        self._save_progress()

    # ====================== ВСПОМОГАТЕЛЬНЫЕ ======================

    def reload_courses(self):
        """Перезагружает курсы из файла"""
        self._course_path = resolve_read_path('course.json')
        self._load_courses()

    # ====================== ПРОВЕРКА ЗАДАНИЙ ======================

    @staticmethod
    def is_successful_execution(output: str) -> bool:
        """True if executor output indicates successful run (no traceback/error)."""
        if not output:
            return True
        if 'Traceback (most recent call last)' in output:
            return False
        lowered = output.lower()
        if output.startswith('Error:') or output.startswith('Ошибка'):
            return False
        if 'syntaxerror' in lowered or 'indentationerror' in lowered:
            return False
        if 'maximum recursion depth exceeded' in lowered:
            return False
        if 'execution timeout exceeded' in lowered or 'превышено время выполнения' in lowered:
            return False
        return True

    def validate_before_run(self, lesson: Dict, user_code: str,
                            has_unfilled_blanks: bool = False) -> ValidationResult:
        """Pre-run checks: empty code, unfilled template blanks."""
        if not user_code.strip():
            return ValidationResult(False, 'enter_code_first')
        if has_unfilled_blanks:
            return ValidationResult(False, 'fill_all_blanks')
        return ValidationResult(True)

    def validate_for_completion(self, lesson: Dict, user_code: str,
                                run_succeeded: bool = False) -> ValidationResult:
        """Checks whether the lesson can be marked as completed."""
        check_type = lesson.get('check_type', 'run_only')
        if check_type == 'run_only' and not run_succeeded:
            return ValidationResult(False, 'complete_practice_first')

        pre = self.validate_before_run(lesson, user_code)
        if not pre.passed:
            return pre

        return ValidationResult(True, 'lesson_ready_to_complete')

    def validate_after_run(self, lesson: Dict, user_code: str,
                           output: str) -> ValidationResult:
        """Post-run validation based on lesson check_type."""
        if not self.is_successful_execution(output):
            return ValidationResult(False, 'lesson_run_failed')

        check_type = lesson.get('check_type', 'run_only')
        if check_type == 'run_only':
            return ValidationResult(True, 'lesson_check_passed')

        return ValidationResult(True, 'lesson_check_passed')

    def get_total_lessons(self, course_id: int = None) -> int:
        """Возвращает общее количество уроков"""
        if course_id:
            course = self.get_course(course_id)
            return len(course.get('lessons', [])) if course else 0
        return sum(len(c.get('lessons', [])) for c in self._courses)

    def get_completed_count(self, course_id: int = None) -> int:
        """Возвращает количество пройденных уроков"""
        if course_id:
            return len(self.get_completed_lesson_ids(course_id))
        total = 0
        for course in self._courses:
            total += len(self.get_completed_lesson_ids(course.get('id')))
        return total

    def get_progress_percentage(self, course_id: int = None) -> float:
        """Возвращает процент прогресса"""
        total = self.get_total_lessons(course_id)
        if total == 0:
            return 0
        return (self.get_completed_count(course_id) / total) * 100

    def reset_progress(self, course_id: int = None):
        """Сбрасывает прогресс уроков (опционально только для конкретного курса)"""
        if course_id is not None:
            # Сбрасываем только для конкретного курса
            course_key = str(course_id)
            if course_key in self._progress.get('completed_lessons_by_course', {}):
                self._progress['completed_lessons_by_course'][course_key] = []
            
            # Сбрасываем связанные данные для уроков этого курса
            course = self.get_course(course_id)
            if course:
                for lesson in course.get('lessons', []):
                    lesson_id = lesson.get('id')
                    # Удаляем попытки
                    if str(lesson_id) in self._progress.get('lesson_attempts', {}):
                        del self._progress['lesson_attempts'][str(lesson_id)]
                    # Удаляем успешные запуски
                    if str(lesson_id) in self._progress.get('lesson_successful_runs', {}):
                        del self._progress['lesson_successful_runs'][str(lesson_id)]
                    # Удаляем сохранённый код
                    if str(lesson_id) in self._progress.get('lesson_codes', {}):
                        del self._progress['lesson_codes'][str(lesson_id)]
                    # Удаляем время прохождения
                    if str(lesson_id) in self._progress.get('lesson_times', {}):
                        del self._progress['lesson_times'][str(lesson_id)]
        else:
            # Полный сброс всего прогресса
            self._progress['completed_lessons'] = []
            self._progress['completed_lessons_by_course'] = {}
            self._progress['lesson_attempts'] = {}
            self._progress['lesson_successful_runs'] = {}
            self._progress['lesson_codes'] = {}
            self._progress['total_xp'] = 0
            self._progress['badges'] = []
            self._progress['streak_days'] = 0
            self._progress['last_activity_date'] = None
            self._progress['lesson_times'] = {}
            self._progress['last_lesson_id'] = None

        self._save_progress()
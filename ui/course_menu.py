"""
Course menu window with courses and lessons list
"""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.progressbar import ProgressBar
from kivy.uix.behaviors import ButtonBehavior
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.app import App

from kivymd.uix.label import MDIcon

from ide_core.themes import ThemeManager
from ide_core.lessons import LessonManager
from utils.vibration_manager import VibrationManager


class ClickableRow(ButtonBehavior, BoxLayout):
    """Кликабельная строка"""
    pass


class CourseMenu(BoxLayout):
    """Меню курсов со списком курсов и уроков"""

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.lesson_manager = LessonManager(app)
        self.orientation = 'vertical'
        self.padding = dp(10)
        self.spacing = dp(10)
        self.current_course_id = None
        self.current_module_id = None
        self.showing_lessons = False

        theme = ThemeManager.get_theme()
        with self.canvas.before:
            self.bg_color = Color(*theme.get('popup_bg', (0.188, 0.204, 0.251, 1)))
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

        self._create_ui()
        Clock.schedule_once(lambda dt: self._wrap_buttons(), 0.1)

    def _update_bg(self, instance, value):
        if hasattr(self, 'bg_rect'):
            self.bg_rect.pos = instance.pos
            self.bg_rect.size = instance.size

    def _create_ui(self):
        theme = ThemeManager.get_theme()
        tr = self.app.tr

        # ========== ВЕРХНЯЯ ПАНЕЛЬ ==========
        self.header_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(40), spacing=dp(10))

        self.back_btn = Button(
            text='←',
            font_name='DejaVuSans',
            size_hint_x=None,
            width=dp(40),
            background_color=theme.get('widget_bg', (0.141, 0.145, 0.149, 1)),
            background_normal='', background_down='',
            color=theme['text_color'],
            font_size=dp(16),
            bold=True,
            opacity=0,
            disabled=True
        )
        self.back_btn.bind(on_release=self._go_back)

        self.title_label = Label(
            text=tr.get('courses', 'Courses'),
            font_size=dp(18),
            font_name='SourceBold',
            color=theme['text_color'],
            halign='center',
            size_hint_x=0.7
        )
        self.title_label.bind(width=lambda inst, val: setattr(inst, 'text_size', (val, None)))

        self.close_btn = Button(
            text='X',
            font_name='DejaVuSans',
            size_hint_x=None,
            width=dp(40),
            background_color=theme.get('btn_danger_bg', (0.5, 0.2, 0.2, 1)),
            background_normal='', background_down='',
            color=(1, 1, 1, 1),
            font_size=dp(16),
            bold=True
        )
        self.close_btn.bind(on_release=self._close)

        self.header_layout.add_widget(self.back_btn)
        self.header_layout.add_widget(self.title_label)
        self.header_layout.add_widget(self.close_btn)
        self.add_widget(self.header_layout)

        # ========== ПРОГРЕСС-ПАНЕЛЬ ==========
        self.progress_layout = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(60), spacing=dp(5))

        self.progress_label = Label(
            text="",
            font_size=dp(12),
            color=theme['text_color'],
            size_hint_y=None,
            height=dp(20)
        )
        self.progress_bar = ProgressBar(max=100, value=0, size_hint_y=None, height=dp(15))
        self.xp_label = Label(
            text=f"XP: {self.lesson_manager.get_total_xp()}",
            font_size=dp(10),
            color=theme.get('stats_text', (0.6, 0.63, 0.65, 1)),
            size_hint_y=None,
            height=dp(20)
        )

        self.progress_layout.add_widget(self.progress_label)
        self.progress_layout.add_widget(self.progress_bar)
        self.progress_layout.add_widget(self.xp_label)
        self.add_widget(self.progress_layout)

        # ========== СПИСОК ==========
        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False, do_scroll_y=True)
        self.items_container = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=dp(5),
            padding=[dp(5), dp(5), dp(5), dp(5)]
        )
        self.items_container.bind(minimum_height=self.items_container.setter('height'))
        scroll.add_widget(self.items_container)
        self.add_widget(scroll)

        # ========== КНОПКА НАЧАТЬ/ПРОДОЛЖИТЬ ==========
        self.start_continue_btn = Button(
            text=tr.get('start_course', 'Start'),
            font_name='SourceBold',
            size_hint_y=None,
            height=dp(45),
            background_color=theme.get('btn_success_bg', (0.2, 0.5, 0.2, 1)),
            background_normal='', background_down='',
            color=(1, 1, 1, 1),
            font_size=dp(14)
        )
        self.start_continue_btn.no_vibration_wrap = True
        self.start_continue_btn.bind(on_release=self._on_continue)
        self.add_widget(self.start_continue_btn)

        self._show_courses()

    def _show_courses(self):
        """Показывает список курсов"""
        self.showing_lessons = False
        self.current_course_id = None

        self.back_btn.opacity = 0
        self.back_btn.disabled = True
        
        # Используем заголовок из metadata если есть
        metadata_title = self.lesson_manager.get_metadata_title(self.app.current_language)
        self.title_label.text = metadata_title if metadata_title else self.app.tr.get('courses', 'Courses')

        # Общий прогресс по всем курсам
        total_completed = self.lesson_manager.get_completed_count()
        total_lessons = self.lesson_manager.get_total_lessons()
        percentage = (total_completed / total_lessons * 100) if total_lessons > 0 else 0
        self.progress_label.text = f"{self.app.tr.get('progress', 'Progress')}: {total_completed}/{total_lessons} ({percentage:.0f}%)"
        self.progress_bar.value = percentage
        
        # Используем total_xp из metadata если есть
        metadata_total_xp = self.lesson_manager.get_metadata_total_xp()
        current_xp = self.lesson_manager.get_total_xp()
        if metadata_total_xp > 0:
            self.xp_label.text = f"XP: {current_xp}/{metadata_total_xp}"
        else:
            self.xp_label.text = f"XP: {current_xp}"

        self.items_container.clear_widgets()
        
        theme = ThemeManager.get_theme()
        lang = self.app.current_language
        
        # Добавляем описание курса из metadata если есть
        metadata_description = self.lesson_manager.get_metadata_description(lang)
        if metadata_description:
            desc_label = Label(
                text=metadata_description,
                font_size=dp(12),
                color=theme.get('stats_text', (0.6, 0.63, 0.65, 1)),
                halign='left',
                size_hint_y=None,
                height=dp(40)
            )
            desc_label.bind(width=lambda inst, val: setattr(inst, 'text_size', (val, None)))
            self.items_container.add_widget(desc_label)
            
            desc_sep = Label(
                text="_" * 80,
                font_size=dp(8),
                font_name='SourceBold',
                color=theme.get('stats_text', (0.6, 0.63, 0.65, 1)),
                size_hint_y=None,
                height=dp(15)
            )
            self.items_container.add_widget(desc_sep)
            
        courses = self.lesson_manager.get_courses()

        if not courses:
            empty_label = Label(
                text=self.app.tr.get('no_courses', 'No courses available'),
                font_size=dp(13),
                color=ThemeManager.get_theme()['text_color'],
                size_hint_y=None,
                height=dp(50)
            )
            self.items_container.add_widget(empty_label)
            self._update_continue_button()
            return

        theme = ThemeManager.get_theme()
        lang = self.app.current_language

        for course in courses:
            course_id = course.get('id')
            title = self.lesson_manager.get_course_title(course, lang)
            progress = self.lesson_manager.get_course_progress(course_id)

            course_row = ClickableRow(
                orientation='horizontal',
                size_hint_y=None,
                height=dp(55),
                spacing=dp(10),
                padding=[dp(10), dp(5), dp(10), dp(5)]
            )
            course_row.course_id = course_id
            course_row.course = course
            course_row.bind(on_release=self._on_course_click)

            with course_row.canvas.before:
                Color(*theme.get('widget_bg', (0.141, 0.145, 0.149, 1)))
                RoundedRectangle(pos=course_row.pos, size=course_row.size, radius=[dp(8)])
            course_row.bind(pos=self._update_row_bg, size=self._update_row_bg)

            # Иконка курса
            icon = MDIcon(
                icon='book-open-page-variant',
                font_size=dp(22),
                theme_text_color="Custom",
                text_color=theme['text_color'],
                size_hint_x=None,
                width=dp(40)
            )
            course_row.add_widget(icon)

            # Информация о курсе
            info_layout = BoxLayout(orientation='vertical', size_hint_x=1, spacing=dp(2))

            title_label = Label(
                text=title,
                font_size=dp(14),
                font_name='SourceBold',
                color=theme['text_color'],
                halign='left',
                size_hint_y=None,
                height=dp(22)
            )
            title_label.bind(width=lambda inst, val: setattr(inst, 'text_size', (val, None)))
            info_layout.add_widget(title_label)

            if progress['total'] > 0:
                progress_text = f"{self.app.tr.get('progress', 'Progress')}: {progress['completed']}/{progress['total']}"
                if progress['percentage'] == 100:
                    status_icon = "✓"
                    status_color = (0.3, 0.7, 0.3, 1)
                else:
                    status_icon = f"{progress['percentage']:.0f}%"
                    status_color = theme.get('stats_text', (0.6, 0.63, 0.65, 1))
            else:
                progress_text = self.app.tr.get('coming_soon', 'Coming soon')
                status_icon = "○"
                status_color = theme.get('stats_text', (0.6, 0.63, 0.65, 1))

            progress_label = Label(
                text=progress_text,
                font_size=dp(10),
                color=theme.get('stats_text', (0.6, 0.63, 0.65, 1)),
                halign='left',
                size_hint_y=None,
                height=dp(18)
            )
            info_layout.add_widget(progress_label)
            course_row.add_widget(info_layout)

            status_label = Label(
                text=status_icon,
                font_size=dp(14),
                font_name='SourceBold',
                color=status_color,
                size_hint_x=None,
                width=dp(45),
                halign='center'
            )
            course_row.add_widget(status_label)

            study_btn = Button(
                text=self.app.tr.get('study', 'Study'),
                font_name='SourceBold',
                font_size=dp(11),
                size_hint_x=None,
                width=dp(60),
                background_color=theme.get('btn_success_bg', (0.2, 0.5, 0.2, 1)) if progress['completed'] < progress[
                    'total'] and progress['total'] > 0 else theme.get('stats_text', (0.6, 0.63, 0.65, 1)),
                background_normal='', background_down='',
                color=(1, 1, 1, 1),
                disabled=(progress['total'] == 0)
            )
            study_btn.course_id = course_id
            study_btn.bind(on_release=self._open_course)
            course_row.add_widget(study_btn)

            self.items_container.add_widget(course_row)

        self._update_continue_button()

    def _show_lessons(self, course_id: int):
        """Показывает уроки выбранного курса"""
        self.showing_lessons = True
        self.current_course_id = course_id

        course = self.lesson_manager.get_course(course_id)
        if not course:
            self._show_courses()
            return

        theme = ThemeManager.get_theme()
        tr = self.app.tr
        lang = self.app.current_language
        course_title = self.lesson_manager.get_course_title(course, lang)

        self.back_btn.opacity = 1
        self.back_btn.disabled = False
        self.title_label.text = course_title

        progress = self.lesson_manager.get_course_progress(course_id)
        self.progress_label.text = f"{tr.get('progress', 'Progress')}: {progress['completed']}/{progress['total']} ({progress['percentage']:.0f}%)"
        self.progress_bar.value = progress['percentage']
        self.xp_label.text = f"XP: {self.lesson_manager.get_total_xp()}"

        self.items_container.clear_widgets()
        lessons = course.get('lessons', [])

        if not lessons:
            empty_label = Label(
                text=tr.get('no_lessons', 'No lessons in this course'),
                font_size=dp(13),
                color=theme['text_color'],
                size_hint_y=None,
                height=dp(50)
            )
            self.items_container.add_widget(empty_label)
            self._update_continue_button()
            return

        for lesson in lessons:
            lesson_id = lesson.get('id')
            title = self.lesson_manager.get_lesson_title(lesson, lang)
            status = self.lesson_manager.get_lesson_status(lesson_id, course_id)
            xp = lesson.get('xp', 10)

            lesson_row = ClickableRow(
                orientation='horizontal',
                size_hint_y=None,
                height=dp(50),
                spacing=dp(10),
                padding=[dp(10), dp(5), dp(10), dp(5)]
            )
            lesson_row.lesson_id = lesson_id
            lesson_row.lesson_status = status
            lesson_row.lesson = lesson
            lesson_row.course_id = course_id
            lesson_row.bind(on_release=self._on_lesson_click)

            with lesson_row.canvas.before:
                Color(*theme.get('widget_bg', (0.141, 0.145, 0.149, 1)))
                RoundedRectangle(pos=lesson_row.pos, size=lesson_row.size, radius=[dp(8)])
            lesson_row.bind(pos=self._update_row_bg, size=self._update_row_bg)

            if status == 'completed':
                status_text = "✓"
                status_color = (0.3, 0.7, 0.3, 1)
            elif status == 'current':
                status_text = "▶"
                status_color = (0.596, 0.486, 1.0, 1)
            else:
                status_text = "🔒"
                status_color = (0.5, 0.5, 0.5, 1)

            status_label = Label(
                text=status_text,
                font_size=dp(16),
                font_name='SourceBold',
                color=status_color,
                size_hint_x=None,
                width=dp(35),
                halign='center'
            )
            lesson_row.add_widget(status_label)

            title_label = Label(
                text=title,
                font_size=dp(13),
                color=theme['text_color'],
                halign='left',
                size_hint_x=1
            )
            title_label.bind(width=lambda inst, val: setattr(inst, 'text_size', (val, None)))
            lesson_row.add_widget(title_label)

            xp_label = Label(
                text=f"{xp} XP",
                font_size=dp(10),
                color=theme.get('stats_text', (0.6, 0.63, 0.65, 1)),
                size_hint_x=None,
                width=dp(50),
                halign='right'
            )
            lesson_row.add_widget(xp_label)

            if status != 'locked':
                study_btn = Button(
                    text=tr.get('study', 'Study'),
                    font_name='SourceBold',
                    font_size=dp(11),
                    size_hint_x=None,
                    width=dp(60),
                    background_color=theme.get('btn_success_bg', (0.2, 0.5, 0.2, 1)),
                    background_normal='', background_down='',
                    color=(1, 1, 1, 1)
                )
                study_btn.lesson_id = lesson_id
                study_btn.course_id = course_id
                study_btn.bind(on_release=self._open_lesson)
                lesson_row.add_widget(study_btn)

            self.items_container.add_widget(lesson_row)

        self._update_continue_button()

    def _get_continue_course_context(self):
        """Возвращает (course_id, completed, total) для кнопки Начать/Продолжить."""
        lm = self.lesson_manager

        if self.current_course_id:
            course_id = self.current_course_id
        else:
            last_id = lm._progress.get('last_course_id')
            if last_id and lm.get_total_lessons(last_id) > 0:
                course_id = last_id
            else:
                course_id = None
                for course in lm.get_courses():
                    cid = course.get('id')
                    if lm.get_total_lessons(cid) > 0:
                        course_id = cid
                        break

        if not course_id:
            return None, 0, 0

        return (
            course_id,
            lm.get_completed_count(course_id),
            lm.get_total_lessons(course_id),
        )

    def _apply_continue_button_state(self, completed: int, total: int):
        """Устанавливает текст и состояние кнопки по прогрессу курса."""
        tr = self.app.tr
        theme = ThemeManager.get_theme()

        if completed == 0:
            self.start_continue_btn.text = tr.get('start_course', 'Start')
            self.start_continue_btn.background_color = theme.get('btn_success_bg', (0.2, 0.5, 0.2, 1))
            self.start_continue_btn.disabled = False
        elif completed < total:
            self.start_continue_btn.text = tr.get('continue_course', 'Continue')
            self.start_continue_btn.background_color = theme.get('btn_success_bg', (0.2, 0.5, 0.2, 1))
            self.start_continue_btn.disabled = False
        else:
            self.start_continue_btn.text = "✓ " + tr.get('course_completed', 'Completed')
            self.start_continue_btn.background_color = theme.get('stats_text', (0.6, 0.63, 0.65, 1))
            self.start_continue_btn.disabled = True

    def _update_continue_button(self):
        """Обновляет текст и состояние кнопки продолжения"""
        tr = self.app.tr
        theme = ThemeManager.get_theme()

        course_id, completed, total = self._get_continue_course_context()

        if total == 0:
            has_available = any(
                self.lesson_manager.get_total_lessons(c.get('id')) > 0
                for c in self.lesson_manager.get_courses()
            )
            if has_available:
                self.start_continue_btn.text = tr.get('start_course', 'Start')
                self.start_continue_btn.background_color = theme.get('btn_success_bg', (0.2, 0.5, 0.2, 1))
                self.start_continue_btn.disabled = False
            else:
                self.start_continue_btn.text = tr.get('no_courses', 'No courses')
                self.start_continue_btn.background_color = theme.get('stats_text', (0.6, 0.63, 0.65, 1))
                self.start_continue_btn.disabled = True
            return

        self._apply_continue_button_state(completed, total)

    def _on_module_click(self, instance):
        """Обработка клика по модулю - показывает уроки модуля"""
        VibrationManager.vibrate(0.02)
        module_lessons = instance.module_lessons
        course_id = instance.course_id
        module_id = instance.module_id
        if module_lessons:
            # Показываем уроки из модуля (фильтруем уроки курса)
            self._show_module_lessons(course_id, module_id, module_lessons)

    def _show_module_lessons(self, course_id: int, module_id: int, lesson_ids):
        """Показывает уроки, относящиеся к модулю"""
        self.showing_lessons = True
        self.current_course_id = course_id
        self.current_module_id = module_id

        theme = ThemeManager.get_theme()
        tr = self.app.tr
        lang = self.app.current_language

        self.back_btn.opacity = 1
        self.back_btn.disabled = False
        
        # Получаем название модуля для заголовка
        modules = self.lesson_manager.get_metadata_modules()
        module_title = ""
        for module in modules:
            if module.get('id') == module_id:
                module_title = module.get(f'title_{lang}', module.get('title_ru', ''))
                break
        
        self.title_label.text = module_title if module_title else tr.get('modules', 'Modules')

        self.items_container.clear_widgets()

        # Получаем все уроки курса и фильтруем по ID модуля
        course = self.lesson_manager.get_course(course_id)
        if not course:
            self._show_courses()
            return

        all_lessons = course.get('lessons', [])
        module_lessons = [l for l in all_lessons if l.get('id') in lesson_ids]

        if not module_lessons:
            empty_label = Label(
                text=tr.get('no_lessons', 'No lessons in this module'),
                font_size=dp(13),
                color=theme['text_color'],
                size_hint_y=None,
                height=dp(50)
            )
            self.items_container.add_widget(empty_label)
            self._update_continue_button()
            return

        for lesson in module_lessons:
            lesson_id = lesson.get('id')
            title = self.lesson_manager.get_lesson_title(lesson, lang)
            status = self.lesson_manager.get_lesson_status(lesson_id, 1)
            xp = lesson.get('xp', 10)

            lesson_row = ClickableRow(
                orientation='horizontal',
                size_hint_y=None,
                height=dp(50),
                spacing=dp(10),
                padding=[dp(10), dp(5), dp(10), dp(5)]
            )
            lesson_row.lesson_id = lesson_id
            lesson_row.lesson_status = status
            lesson_row.lesson = lesson
            lesson_row.course_id = 1
            lesson_row.bind(on_release=self._on_lesson_click)

            with lesson_row.canvas.before:
                Color(*theme.get('widget_bg', (0.141, 0.145, 0.149, 1)))
                RoundedRectangle(pos=lesson_row.pos, size=lesson_row.size, radius=[dp(8)])
            lesson_row.bind(pos=self._update_row_bg, size=self._update_row_bg)

            if status == 'completed':
                status_text = "✓"
                status_color = (0.3, 0.7, 0.3, 1)
            elif status == 'current':
                status_text = "▶"
                status_color = (0.596, 0.486, 1.0, 1)
            else:
                status_text = "🔒"
                status_color = (0.5, 0.5, 0.5, 1)

            status_label = Label(
                text=status_text,
                font_size=dp(16),
                font_name='SourceBold',
                color=status_color,
                size_hint_x=None,
                width=dp(35),
                halign='center'
            )
            lesson_row.add_widget(status_label)

            title_label = Label(
                text=title,
                font_size=dp(13),
                color=theme['text_color'],
                halign='left',
                size_hint_x=1
            )
            title_label.bind(width=lambda inst, val: setattr(inst, 'text_size', (val, None)))
            lesson_row.add_widget(title_label)

            xp_label = Label(
                text=f"{xp} XP",
                font_size=dp(10),
                color=theme.get('stats_text', (0.6, 0.63, 0.65, 1)),
                size_hint_x=None,
                width=dp(50),
                halign='right'
            )
            lesson_row.add_widget(xp_label)

            if status != 'locked':
                study_btn = Button(
                    text=tr.get('study', 'Study'),
                    font_name='SourceBold',
                    font_size=dp(11),
                    size_hint_x=None,
                    width=dp(60),
                    background_color=theme.get('btn_success_bg', (0.2, 0.5, 0.2, 1)),
                    background_normal='', background_down='',
                    color=(1, 1, 1, 1)
                )
                study_btn.lesson_id = lesson_id
                study_btn.course_id = 1
                study_btn.bind(on_release=self._open_lesson)
                lesson_row.add_widget(study_btn)

            self.items_container.add_widget(lesson_row)

        self._update_continue_button()

    def _on_course_click(self, instance):
        VibrationManager.vibrate(0.02)
        course_id = instance.course_id
        self._show_course_modules(course_id)

    def _show_course_modules(self, course_id: int):
        """Показывает модули выбранного курса"""
        self.showing_lessons = False
        self.current_course_id = course_id
        self.current_module_id = None

        course = self.lesson_manager.get_course(course_id)
        if not course:
            self._show_courses()
            return

        theme = ThemeManager.get_theme()
        tr = self.app.tr
        lang = self.app.current_language
        course_title = self.lesson_manager.get_course_title(course, lang)

        self.back_btn.opacity = 1
        self.back_btn.disabled = False
        self.title_label.text = course_title

        progress = self.lesson_manager.get_course_progress(course_id)
        self.progress_label.text = f"{tr.get('progress', 'Progress')}: {progress['completed']}/{progress['total']} ({progress['percentage']:.0f}%)"
        self.progress_bar.value = progress['percentage']
        self.xp_label.text = f"XP: {self.lesson_manager.get_total_xp()}"

        self.items_container.clear_widgets()

        # ✅ ИСПРАВЛЕНО: модули из КУРСА, а не из metadata
        modules = course.get('modules', [])

        if not modules:
            # Если модулей нет, показываем уроки напрямую
            self._show_lessons(course_id)
            return

        for module in modules:
            module_id = module.get('id')
            module_title = module.get(f'title_{lang}', module.get('title_ru', ''))
            module_lessons = module.get('lessons', [])

            # Считаем прогресс по модулю
            module_completed = 0
            for lesson_id in module_lessons:
                if self.lesson_manager.is_lesson_completed(lesson_id, course_id):
                    module_completed += 1

            # Диапазон уроков (например, 1-8)
            lesson_range = ""
            if module_lessons:
                min_lesson = min(module_lessons)
                max_lesson = max(module_lessons)
                lesson_range = f"{min_lesson}-{max_lesson}"

            module_row = ClickableRow(
                orientation='horizontal',
                size_hint_y=None,
                height=dp(45),
                spacing=dp(10),
                padding=[dp(15), dp(5), dp(10), dp(5)]
            )
            module_row.module_id = module_id
            module_row.module_lessons = module_lessons
            module_row.course_id = course_id
            module_row.bind(on_release=self._on_module_click)

            with module_row.canvas.before:
                Color(*theme.get('widget_bg', (0.141, 0.145, 0.149, 1)))
                RoundedRectangle(pos=module_row.pos, size=module_row.size, radius=[dp(6)])
            module_row.bind(pos=self._update_row_bg, size=self._update_row_bg)

            # Иконка модуля
            module_icon = MDIcon(
                icon='folder-outline',
                font_size=dp(18),
                theme_text_color="Custom",
                text_color=theme.get('stats_text', (0.6, 0.63, 0.65, 1)),
                size_hint_x=None,
                width=dp(35)
            )
            module_row.add_widget(module_icon)

            # Информация о модуле
            module_info = BoxLayout(orientation='vertical', size_hint_x=1, spacing=dp(2))

            module_title_label = Label(
                text=module_title,
                font_size=dp(12),
                color=theme['text_color'],
                halign='left',
                size_hint_y=None,
                height=dp(20)
            )
            module_title_label.bind(width=lambda inst, val: setattr(inst, 'text_size', (val, None)))
            module_info.add_widget(module_title_label)

            # Диапазон уроков (например, 1-8)
            lessons_label = Label(
                text=lesson_range if lesson_range else "",
                font_size=dp(9),
                color=theme.get('stats_text', (0.6, 0.63, 0.65, 1)),
                halign='left',
                size_hint_y=None,
                height=dp(16)
            )
            module_info.add_widget(lessons_label)
            module_row.add_widget(module_info)

            # Статус модуля (выполнено/всего)
            if module_completed == len(module_lessons) and len(module_lessons) > 0:
                module_status = "✓"
                module_status_color = (0.3, 0.7, 0.3, 1)
            else:
                module_status = f"{module_completed}/{len(module_lessons)}"
                module_status_color = theme.get('stats_text', (0.6, 0.63, 0.65, 1))

            module_status_label = Label(
                text=module_status,
                font_size=dp(11),
                font_name='SourceBold',
                color=module_status_color,
                size_hint_x=None,
                width=dp(40),
                halign='center'
            )
            module_row.add_widget(module_status_label)

            self.items_container.add_widget(module_row)

        self._update_continue_button()

    def _on_lesson_click(self, instance):
        VibrationManager.vibrate(0.02)

        lesson_id = instance.lesson_id
        status = instance.lesson_status
        course_id = instance.course_id

        if status != 'locked':
            lesson = self.lesson_manager.get_lesson(lesson_id, course_id)
            if lesson:
                self.lesson_manager.set_last_lesson(lesson_id, course_id)
                self._close(None)
                self._show_lesson_dialog(lesson, course_id)

    def _open_course(self, instance):
        VibrationManager.vibrate(0.02)
        course_id = instance.course_id
        if self.lesson_manager.get_total_lessons(course_id) > 0:
            self._show_lessons(course_id)

    def _open_lesson(self, instance):
        VibrationManager.vibrate(0.02)
        lesson_id = instance.lesson_id
        course_id = instance.course_id
        lesson = self.lesson_manager.get_lesson(lesson_id, course_id)

        if lesson:
            self.lesson_manager.set_last_lesson(lesson_id, course_id)
            self._close(None)
            self._show_lesson_dialog(lesson, course_id)

    def _go_back(self, instance):
        VibrationManager.vibrate(0.02)
        if self.showing_lessons and self.current_module_id is not None:
            # Возвращаемся к модулям курса
            self._show_course_modules(self.current_course_id)
        elif not self.showing_lessons and self.current_course_id is not None:
            # Возвращаемся к списку курсов
            self._show_courses()
        else:
            # Уже на уровне курсов
            self._show_courses()

    def _on_continue(self, instance):
        VibrationManager.vibrate(0.02)

        course_id, completed, total = self._get_continue_course_context()

        if total == 0:
            self.app.show_result_popup(
                self.app.tr.get('no_courses', 'No courses available')
            )
            return

        if completed >= total:
            self.app.show_result_popup(
                self.app.tr.get('all_courses_completed_msg', 'All courses completed!')
            )
            return

        if completed == 0:
            lesson = self.lesson_manager.get_lesson_by_order(course_id, 1)
        else:
            lesson = self.lesson_manager.get_next_lesson(course_id)

        if lesson:
            self._open_lesson_by_id(lesson.get('id'), course_id)

    def _open_lesson_by_id(self, lesson_id, course_id):
        lesson = self.lesson_manager.get_lesson(lesson_id, course_id)
        if lesson:
            self.lesson_manager.set_last_lesson(lesson_id, course_id)
            self._close(None)
            self._show_lesson_dialog(lesson, course_id)

    def _show_lesson_dialog(self, lesson, course_id):
        from ui.lesson_view import LessonView

        lesson_view = LessonView(self.app, lesson, self.lesson_manager, course_id=course_id)
        lesson_view.size_hint = (0.92, 0.88)
        lesson_view.pos_hint = {'center_x': 0.5, 'center_y': 0.5}

        if hasattr(self.app, 'root_layout'):
            self.app.root_layout.add_widget(lesson_view)

        # Поднимаем symbol_bar наверх чтобы он был поверх окна урока
        if hasattr(self.app, 'symbol_bar') and self.app.symbol_bar:
            if hasattr(self.app, 'root_layout') and self.app.root_layout:
                self.app.root_layout.remove_widget(self.app.symbol_bar)
                self.app.root_layout.add_widget(self.app.symbol_bar)

    def _update_row_bg(self, instance, value):
        if hasattr(instance, 'canvas'):
            instance.canvas.before.clear()
            theme = ThemeManager.get_theme()
            with instance.canvas.before:
                Color(*theme.get('widget_bg', (0.141, 0.145, 0.149, 1)))
                RoundedRectangle(pos=instance.pos, size=instance.size, radius=[dp(8)])

    def _close(self, instance):
        if self.parent:
            self.parent.remove_widget(self)

    def _wrap_buttons(self):
        if hasattr(self.app, 'wrap_widget_buttons'):
            self.app.wrap_widget_buttons(self)
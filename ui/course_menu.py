# ui/course_menu.py
"""
Course menu window with lessons list and progress
"""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.progressbar import ProgressBar
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.app import App
from kivy.uix.behaviors import ButtonBehavior

from ide_core.themes import ThemeManager
from ide_core.lessons import LessonManager
from widgets.dialogs import ThemedPopup


class ClickableRow(ButtonBehavior, BoxLayout):
    """Кликабельная строка урока"""
    pass


class CourseMenu(BoxLayout):
    """Меню курса со списком уроков и прогрессом"""

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.lesson_manager = LessonManager(app)
        self.orientation = 'vertical'
        self.padding = dp(10)
        self.spacing = dp(10)

        # Фон
        theme = ThemeManager.get_theme()
        with self.canvas.before:
            self.bg_color = Color(*theme.get('popup_bg', (0.188, 0.204, 0.251, 1)))
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

        self._create_ui()

    def _update_bg(self, instance, value):
        """Обновляет фон при изменении размера/позиции"""
        if hasattr(self, 'bg_rect'):
            self.bg_rect.pos = instance.pos
            self.bg_rect.size = instance.size

    def _create_ui(self):
        """Создаёт интерфейс меню курса"""
        theme = ThemeManager.get_theme()
        tr = self.app.tr
        lang = self.app.current_language

        # ========== ЗАГОЛОВОК ==========
        title_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(40), spacing=dp(10))

        title_label = Label(
            text=self.lesson_manager.get_course_title(lang),
            font_size=dp(18),
            font_name='SourceBold',
            color=theme['text_color'],
            halign='center',
            size_hint_x=0.8
        )
        title_label.bind(width=lambda inst, val: setattr(inst, 'text_size', (val, None)))

        close_btn = Button(
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
        close_btn.bind(on_release=self._close)

        title_layout.add_widget(title_label)
        title_layout.add_widget(close_btn)
        self.add_widget(title_layout)

        # ========== ПРОГРЕСС ==========
        progress_layout = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(60), spacing=dp(5))

        completed = self.lesson_manager.get_completed_count()
        total = self.lesson_manager.get_total_lessons()
        percentage = self.lesson_manager.get_progress_percentage()

        progress_label = Label(
            text=f"{tr.get('progress', 'Progress')}: {completed}/{total} ({percentage:.0f}%)",
            font_size=dp(12),
            color=theme['text_color'],
            size_hint_y=None,
            height=dp(20)
        )
        progress_layout.add_widget(progress_label)

        self.progress_bar = ProgressBar(
            max=100,
            value=percentage,
            size_hint_y=None,
            height=dp(15)
        )
        progress_layout.add_widget(self.progress_bar)

        xp_label = Label(
            text=f"XP: {self.lesson_manager.get_total_xp()}",
            font_size=dp(10),
            color=theme.get('stats_text', (0.6, 0.63, 0.65, 1)),
            size_hint_y=None,
            height=dp(20)
        )
        progress_layout.add_widget(xp_label)

        self.add_widget(progress_layout)

        # ========== СПИСОК УРОКОВ ==========
        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False, do_scroll_y=True)
        self.lessons_container = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=dp(5),
            padding=[dp(5), dp(5), dp(5), dp(5)]
        )
        self.lessons_container.bind(minimum_height=self.lessons_container.setter('height'))

        self._build_lessons_list()

        scroll.add_widget(self.lessons_container)
        self.add_widget(scroll)

        # ========== КНОПКА НАЧАТЬ / ПРОДОЛЖИТЬ ==========
        completed_count = self.lesson_manager.get_completed_count()

        if completed_count == 0:
            btn_text = tr.get('start_course', 'Start Course')
            btn_color = theme.get('btn_success_bg', (0.2, 0.5, 0.2, 1))
        else:
            btn_text = tr.get('continue_course', 'Continue Learning')
            btn_color = theme.get('btn_success_bg', (0.2, 0.5, 0.2, 1))

        self.start_continue_btn = Button(
            text=btn_text,
            font_name='SourceBold',
            size_hint_y=None,
            height=dp(45),
            background_color=btn_color,
            background_normal='', background_down='',
            color=(1, 1, 1, 1),
            font_size=dp(14)
        )
        self.start_continue_btn.bind(on_release=self._on_continue)
        self.add_widget(self.start_continue_btn)

    def _build_lessons_list(self):
        """Строит список уроков"""
        theme = ThemeManager.get_theme()
        tr = self.app.tr
        lang = self.app.current_language

        lessons = self.lesson_manager.get_lessons()

        for lesson in lessons:
            lesson_id = lesson.get('id')
            title = self.lesson_manager.get_lesson_title(lesson, lang)
            status = self.lesson_manager.get_lesson_status(lesson_id)
            xp = lesson.get('xp', 10)

            # Кликабельная строка урока
            lesson_row = ClickableRow(
                orientation='horizontal',
                size_hint_y=None,
                height=dp(50),
                spacing=dp(10),
                padding=[dp(10), dp(5), dp(10), dp(5)]
            )
            # Сохраняем данные урока в атрибутах строки
            lesson_row.lesson_id = lesson_id
            lesson_row.lesson_status = status
            lesson_row.lesson = lesson
            lesson_row.bind(on_release=self._on_row_click)

            # Фон строки с закруглёнными углами
            with lesson_row.canvas.before:
                Color(*theme.get('widget_bg', (0.141, 0.145, 0.149, 1)))
                RoundedRectangle(pos=lesson_row.pos, size=lesson_row.size, radius=[dp(8)])
            lesson_row.bind(pos=self._update_row_bg, size=self._update_row_bg)

            # Статус (иконка/номер)
            if status == 'completed':
                status_text = "✓"
                status_color = (0.3, 0.7, 0.3, 1)
            elif status == 'current':
                status_text = "▶"
                status_color = (0.596, 0.486, 1.0, 1)
            elif status == 'locked':
                status_text = "✗"
                status_color = (0.5, 0.5, 0.5, 1)
            else:  # available
                status_text = str(lesson.get('order', lesson_id))
                status_color = theme['text_color']

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

            # Название урока
            title_label = Label(
                text=title,
                font_size=dp(13),
                color=theme['text_color'],
                halign='left',
                size_hint_x=1
            )
            title_label.bind(width=lambda inst, val: setattr(inst, 'text_size', (val, None)))
            lesson_row.add_widget(title_label)

            # XP
            xp_label = Label(
                text=f"{xp} XP",
                font_size=dp(10),
                color=theme.get('stats_text', (0.6, 0.63, 0.65, 1)),
                size_hint_x=None,
                width=dp(50),
                halign='right'
            )
            lesson_row.add_widget(xp_label)

            # Кнопка "Изучить" (только если урок доступен)
            if status != 'locked':
                study_btn = Button(
                    text=tr.get('study', 'Study'),
                    font_name='SourceBold',
                    font_size=dp(11),
                    size_hint_x=None,
                    width=dp(60),
                    background_color=theme.get('btn_success_bg',
                                               (0.2, 0.5, 0.2, 1)) if status == 'current' else theme.get('widget_bg',
                                                                                                         (0.141, 0.145,
                                                                                                          0.149, 1)),
                    background_normal='', background_down='',
                    color=(1, 1, 1, 1) if status == 'current' else theme['text_color']
                )
                study_btn.lesson_id = lesson_id
                study_btn.bind(on_release=self._open_lesson)
                lesson_row.add_widget(study_btn)

            self.lessons_container.add_widget(lesson_row)

    def _update_row_bg(self, instance, value):
        """Обновляет фон строки урока"""
        if hasattr(instance, 'canvas'):
            # Перерисовываем фон
            instance.canvas.before.clear()
            theme = ThemeManager.get_theme()
            with instance.canvas.before:
                Color(*theme.get('widget_bg', (0.141, 0.145, 0.149, 1)))
                RoundedRectangle(pos=instance.pos, size=instance.size, radius=[dp(8)])

    def _on_row_click(self, instance):
        """Обрабатывает клик по строке урока"""
        lesson_id = instance.lesson_id
        status = instance.lesson_status

        if status != 'locked':
            lesson = self.lesson_manager.get_lesson(lesson_id)
            if lesson:
                self.lesson_manager.set_last_lesson(lesson_id)
                self._close(None)
                self._show_lesson_dialog(lesson)

    def _open_lesson(self, instance):
        """Открывает выбранный урок (по кнопке Study)"""
        lesson_id = instance.lesson_id
        lesson = self.lesson_manager.get_lesson(lesson_id)

        if lesson:
            # Сохраняем как последний открытый урок
            self.lesson_manager.set_last_lesson(lesson_id)
            # Закрываем меню курса
            self._close(None)
            # Открываем урок
            self._show_lesson_dialog(lesson)

    def _on_continue(self, instance):
        """Начинает или продолжает обучение"""
        completed_count = self.lesson_manager.get_completed_count()

        if completed_count == 0:
            # Ни одного урока не пройдено → начинаем с первого урока
            first_lesson = self.lesson_manager.get_lesson_by_order(1)
            if first_lesson:
                self._open_lesson_by_id(first_lesson.get('id'))
        else:
            # Есть пройденные уроки → продолжаем со следующего не пройденного
            next_lesson = self.lesson_manager.get_next_lesson()
            if next_lesson:
                self._open_lesson_by_id(next_lesson.get('id'))
            else:
                # Все уроки пройдены
                self._close(None)
                self.app.show_result_popup(
                    self.app.tr.get('course_completed_msg', 'Congratulations! You have completed the course!')
                )

    def _open_lesson_by_id(self, lesson_id):
        """Открывает урок по ID"""
        lesson = self.lesson_manager.get_lesson(lesson_id)
        if lesson:
            self.lesson_manager.set_last_lesson(lesson_id)
            self._close(None)
            self._show_lesson_dialog(lesson)

    def _show_lesson_dialog(self, lesson):
        """Показывает диалог с уроком"""
        from ui.lesson_view import LessonView

        lesson_view = LessonView(self.app, lesson, self.lesson_manager)
        lesson_view.size_hint = (0.92, 0.88)
        lesson_view.pos_hint = {'center_x': 0.5, 'center_y': 0.5}

        if hasattr(self.app, 'root_layout'):
            self.app.root_layout.add_widget(lesson_view)

    def _close(self, instance):
        """Закрывает меню курса"""
        if self.parent:
            self.parent.remove_widget(self)
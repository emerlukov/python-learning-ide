# ui/lesson_view.py
"""
Lesson view dialog with theory, practice, task and hint tabs

ОПТИМИЗАЦИИ (v2):
  1. Ленивая загрузка вкладок — контент строится только при первом открытии вкладки.
  2. Переключение уроков через placeholder + Clock.schedule_once — UI не блокируется.
  3. Дебаунс сохранения кода — запись на диск не на каждый символ, а с задержкой 1.5 с.
  4. _force_defocus_tree ограничена глубиной и работает через итеративный стек.
  5. _wrap_buttons отложен до 0.5 с (вместо 0.1 с).
"""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.graphics import Color, Rectangle, Line
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.app import App
from kivy.core.clipboard import Clipboard
from kivy.core.window import Window

from ide_core.themes import ThemeManager
from ide_core.lessons import LessonManager
from widgets.editor import LineNumberTextInput
from widgets.dialogs import ThemedPopup
from widgets import InteractiveCodeWidget
from utils.vibration_manager import VibrationManager


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------

def _force_defocus_tree(widget, max_depth=6):
    """
    Итеративно снимает фокус и маркеры выделения со всех TextInput.
    Ограничена глубиной max_depth чтобы не тормозить на глубоких деревьях.
    """
    stack = [(widget, 0)]
    while stack:
        w, depth = stack.pop()
        if depth > max_depth:
            continue
        if isinstance(w, TextInput):
            if w.focus:
                w.focus = False
            w.cancel_selection()
            try:
                for handle_name in ('_handle_left', '_handle_right', '_handle_middle'):
                    h = getattr(w, handle_name, None)
                    if h is not None:
                        h.opacity = 0
            except Exception:
                pass
        for child in w.children:
            stack.append((child, depth + 1))


# ---------------------------------------------------------------------------
# ScrollView-классы (без изменений логики)
# ---------------------------------------------------------------------------

class PassthroughScrollView(ScrollView):
    """
    Внешний ScrollView вкладок (Теория, Задание).
    - Вертикальный свайп в любом месте → листает вкладку.
    - Тап не на TextInput → снимает выделение.
    - touch события НЕ перехватываются вне своей области.
    """

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return False
        hit = self._hit_text_input(touch.pos)
        if not hit:
            _force_defocus_tree(self)
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if not self.collide_point(*touch.pos) and touch.grab_current is not self:
            return False
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if not self.collide_point(*touch.pos) and touch.grab_current is not self:
            return False
        return super().on_touch_up(touch)

    def _hit_text_input(self, pos):
        # Итеративный поиск вместо рекурсивного
        stack = list(self.children)
        while stack:
            w = stack.pop()
            if isinstance(w, TextInput) and w.collide_point(*pos):
                return w
            stack.extend(w.children)
        return None


class TemplateScrollView(ScrollView):
    """
    ScrollView для блоков шаблонов в задании.
    Определяем направление свайпа по первым dp(8) пикселям.
    """
    THRESHOLD = dp(8)

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            _force_defocus_tree(self)
            return False
        touch.ud['tsv_ox'] = touch.x
        touch.ud['tsv_oy'] = touch.y
        touch.ud['tsv_dir'] = None
        touch.ud['tsv_inner_started'] = False
        touch.grab(self)
        return True

    def on_touch_move(self, touch):
        if touch.grab_current is not self:
            return False

        direction = touch.ud.get('tsv_dir')
        dx = touch.x - touch.ud['tsv_ox']
        dy = touch.y - touch.ud['tsv_oy']

        if direction is None:
            if abs(dx) > self.THRESHOLD or abs(dy) > self.THRESHOLD:
                touch.ud['tsv_dir'] = 'v' if abs(dy) >= abs(dx) else 'h'
            return True

        if direction == 'v':
            touch.ungrab(self)
            return False

        if self.do_scroll_x and self.content_width > self.width:
            sw = self.content_width - self.width
            if sw > 0:
                self.scroll_x = max(0.0, min(1.0, self.scroll_x - dx / sw))
                touch.ud['tsv_ox'] = touch.x
                touch.ud['tsv_oy'] = touch.y
        elif self.do_scroll_y and self.content_height > self.height:
            sh = self.content_height - self.height
            if sh > 0:
                self.scroll_y = max(0.0, min(1.0, self.scroll_y + dy / sh))
                touch.ud['tsv_ox'] = touch.x
                touch.ud['tsv_oy'] = touch.y
        return True

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            direction = touch.ud.get('tsv_dir')
            if direction is None:
                super().on_touch_down(touch)
                super().on_touch_up(touch)
            return True
        if not self.collide_point(*touch.pos):
            return False
        return super().on_touch_up(touch)

    @property
    def content_width(self):
        if self.children:
            return self.children[0].width
        return self.width

    @property
    def content_height(self):
        if self.children:
            return self.children[0].height
        return self.height


# ---------------------------------------------------------------------------
# Основной класс
# ---------------------------------------------------------------------------

class LessonView(BoxLayout):
    """Диалог просмотра урока с табами"""

    _BASE_CENTER_Y = 0.5
    _BASE_SIZE_HINT_Y = 0.88

    def __init__(self, app, lesson, lesson_manager, course_id=None, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.lesson = lesson
        self.lesson_manager = lesson_manager
        self.course_id = course_id or lesson.get('course_id')
        self.orientation = 'vertical'
        self.padding = dp(5)
        self.spacing = dp(5)

        # Состояние
        self.user_code = ""
        self._keyboard_height = 0

        # --- ОПТИМИЗАЦИЯ: дебаунс сохранения ---
        self._save_event = None

        # --- ОПТИМИЗАЦИЯ: отслеживаем, какие вкладки уже построены ---
        self._tabs_built = set()

        # Фон
        theme = ThemeManager.get_theme()
        with self.canvas.before:
            self.bg_color = Color(*theme.get('popup_bg', (0.188, 0.204, 0.251, 1)))
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

        self._create_ui()

        # Откладываем wrap_buttons — не мешает первому рендеру
        Clock.schedule_once(lambda dt: self._wrap_buttons(), 0.5)

        self._win_height = Window.height
        Window.bind(on_resize=self._on_window_resize)

    # ------------------------------------------------------------------
    # Фон
    # ------------------------------------------------------------------

    def _update_bg(self, instance, value):
        if hasattr(self, 'bg_rect'):
            self.bg_rect.pos = instance.pos
            self.bg_rect.size = instance.size

    # ------------------------------------------------------------------
    # Построение UI (скелет — только заголовок, табы-заглушки, кнопки)
    # ------------------------------------------------------------------

    def _create_ui(self):
        """Создаёт скелет интерфейса урока. Контент вкладок строится лениво."""
        theme = ThemeManager.get_theme()
        tr = self.app.tr
        lang = self.app.current_language
        lesson = self.lesson

        lesson_id = lesson.get('id', 0)
        lesson_order = lesson.get('order', lesson_id)
        title = self.lesson_manager.get_lesson_title(lesson, lang)

        # ========== ВЕРХНЯЯ ПАНЕЛЬ ==========
        header_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(40), spacing=dp(10))

        title_label = Label(
            text=f"{tr.get('lesson', 'Lesson')} {lesson_order}: {title}",
            font_size=dp(16),
            font_name='SourceBold',
            color=theme['text_color'],
            halign='left',
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

        header_layout.add_widget(title_label)
        header_layout.add_widget(close_btn)
        self.add_widget(header_layout)

        # ========== ТАБЫ ==========
        self.tab_panel = TabbedPanel(
            size_hint=(1, 1),
            do_default_tab=False,
            tab_width=dp(100),
            tab_height=dp(35),
        )

        # Создаём только заголовки вкладок — контент добавим лениво
        self.theory_tab = TabbedPanelItem(text=tr.get('theory', 'Theory'))
        self.task_tab = TabbedPanelItem(text=tr.get('task', 'Task'))
        self.practice_tab = TabbedPanelItem(text=tr.get('practice', 'Practice'))
        self.hint_tab = TabbedPanelItem(text=tr.get('hint', 'Hint'))

        self.tab_panel.add_widget(self.theory_tab)
        self.tab_panel.add_widget(self.task_tab)
        self.tab_panel.add_widget(self.practice_tab)
        self.tab_panel.add_widget(self.hint_tab)

        self._apply_tab_theme()
        self.add_widget(self.tab_panel)

        # ========== НИЖНЯЯ ПАНЕЛЬ С КНОПКАМИ ==========
        buttons_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(45), spacing=dp(5))

        self.run_btn = Button(
            text=tr.get('run', 'Run'),
            font_name='SourceBold',
            background_color=theme.get('run_btn_bg', (0.85, 0.88, 0.90, 1)),
            background_normal='', background_down='',
            color=theme.get('run_btn_text', (0.18, 0.18, 0.19, 1)),
            font_size=dp(16),
            size_hint_x=0.2
        )
        self.run_btn.bind(on_release=self._run_code)

        self.prev_btn = Button(
            text='←',
            font_name='DejaVuSans',
            size_hint_x=0.1,
            background_color=theme.get('widget_bg', (0.141, 0.145, 0.149, 1)),
            background_normal='', background_down='',
            color=theme['text_color'],
            font_size=dp(18),
            bold=True,
            disabled=True
        )
        self.prev_btn.no_vibration_wrap = True
        self.prev_btn.bind(on_release=self._go_to_previous_lesson)

        self.next_btn = Button(
            text='→',
            font_name='DejaVuSans',
            size_hint_x=0.1,
            background_color=theme.get('widget_bg', (0.141, 0.145, 0.149, 1)),
            background_normal='', background_down='',
            color=theme['text_color'],
            font_size=dp(18),
            bold=True,
            disabled=True
        )
        self.next_btn.no_vibration_wrap = True
        self.next_btn.bind(on_release=self._go_to_next_lesson)

        is_completed = self.lesson_manager.is_lesson_completed(lesson_id, self.course_id)
        self.complete_btn = Button(
            text="✓ " + (
                tr.get('completed', 'Completed') if is_completed else tr.get('mark_completed', 'Mark Completed')),
            font_name='SourceBold',
            background_color=theme.get('stats_text', (0.6, 0.63, 0.65, 1)) if is_completed else theme.get(
                'btn_success_bg', (0.2, 0.5, 0.2, 1)),
            background_normal='', background_down='',
            color=theme['text_color'] if is_completed else (1, 1, 1, 1),
            font_size=dp(12),
            disabled=is_completed,
            size_hint_x=0.3
        )
        self.complete_btn.bind(on_release=self._mark_completed)

        buttons_layout.add_widget(self.run_btn)
        buttons_layout.add_widget(self.prev_btn)
        buttons_layout.add_widget(self.next_btn)
        buttons_layout.add_widget(self.complete_btn)
        self.add_widget(buttons_layout)

        self._update_navigation_buttons()

        # Строим первую вкладку сразу (она видима), остальные — лениво
        self._build_tab('theory')

        # Устанавливаем активную вкладку
        Clock.schedule_once(lambda dt: self._set_default_tab(), 0)

    def _set_default_tab(self):
        """Устанавливает активную вкладку после рендера"""
        self.tab_panel.switch_to(self.theory_tab)

    # ------------------------------------------------------------------
    # Ленивое построение вкладок
    # ------------------------------------------------------------------

    def _build_tab(self, tab_key):
        """Строит содержимое вкладки, если ещё не построено."""
        if tab_key in self._tabs_built:
            return
        self._tabs_built.add(tab_key)

        builders = {
            'theory':   self._create_theory_tab,
            'task':     self._create_task_tab,
            'practice': self._create_practice_tab,
            'hint':     self._create_hint_tab,
        }
        builder = builders.get(tab_key)
        if builder:
            builder()

    def _on_tab_changed(self, instance, value):
        """Вызывается при смене вкладки — строит контент лениво."""
        VibrationManager.vibrate(0.015)
        self._update_active_tab_color()

        theme = ThemeManager.get_theme()
        separator_color = theme.get('separator_color', (0.5, 0.5, 0.5, 0.3))
        Clock.schedule_once(lambda dt: self._draw_tab_separators(separator_color), 0.05)

        # Определяем ключ выбранной вкладки
        tab_map = {
            id(self.theory_tab):   'theory',
            id(self.task_tab):     'task',
            id(self.practice_tab): 'practice',
            id(self.hint_tab):     'hint',
        }
        key = tab_map.get(id(value))
        if key and key not in self._tabs_built:
            # Строим в следующем кадре — UI успевает перерисоваться
            Clock.schedule_once(lambda dt: self._build_tab(key), 0)

    # ------------------------------------------------------------------
    # Навигация между уроками
    # ------------------------------------------------------------------

    def _update_navigation_buttons(self):
        """Обновляет состояние кнопок навигации"""
        current_id = self.lesson.get('id', 0)

        course = self.lesson_manager.get_course(self.course_id)
        if not course:
            self.prev_btn.disabled = True
            self.next_btn.disabled = True
            return

        lessons = course.get('lessons', [])
        sorted_lessons = sorted(lessons, key=lambda x: x.get('order', 0))
        completed_ids = self.lesson_manager.get_completed_lesson_ids(self.course_id)

        current_index = next(
            (i for i, l in enumerate(sorted_lessons) if l.get('id') == current_id), -1
        )

        if current_index == -1:
            self.prev_btn.disabled = True
            self.next_btn.disabled = True
            return

        is_current_completed = current_id in completed_ids

        # Кнопка "назад" — ближайший пройденный перед текущим
        prev_completed = next(
            (sorted_lessons[i] for i in range(current_index - 1, -1, -1)
             if sorted_lessons[i].get('id') in completed_ids),
            None
        )
        self.prev_btn.disabled = (prev_completed is None)
        self.prev_btn.lesson_to_switch = prev_completed

        # Кнопка "вперёд" — следующий урок (если текущий пройден)
        next_lesson = sorted_lessons[current_index + 1] if current_index < len(sorted_lessons) - 1 else None
        self.next_btn.disabled = (next_lesson is None or not is_current_completed)
        self.next_btn.lesson_to_switch = next_lesson

    def _go_to_previous_lesson(self, instance):
        target = getattr(instance, 'lesson_to_switch', None)
        if target:
            self._switch_to_lesson(target)

    def _go_to_next_lesson(self, instance):
        target = getattr(instance, 'lesson_to_switch', None)
        if target:
            self._switch_to_lesson(target)

    def _switch_to_lesson(self, lesson):
        """
        ОПТИМИЗАЦИЯ: переключает урок через placeholder, чтобы не блокировать UI.
        Старый LessonView удаляется сразу, новый строится в следующем кадре.
        """
        VibrationManager.vibrate(0.02)
        self._update_code_from_editor()

        parent = self.parent
        if not parent:
            return

        # Сохраняем параметры расположения до удаления
        saved_size_hint = self.size_hint
        saved_pos_hint = dict(self.pos_hint)

        # Показываем placeholder с фоном из темы немедленно
        theme = ThemeManager.get_theme()
        placeholder = BoxLayout(orientation='vertical')
        placeholder.size_hint = saved_size_hint
        placeholder.pos_hint = saved_pos_hint
        with placeholder.canvas.before:
            Color(*theme.get('popup_bg', (0.188, 0.204, 0.251, 1)))
            _ph_rect = Rectangle(pos=placeholder.pos, size=placeholder.size)

        def _update_ph_rect(inst, val):
            _ph_rect.pos = inst.pos
            _ph_rect.size = inst.size

        placeholder.bind(pos=_update_ph_rect, size=_update_ph_rect)
        placeholder.add_widget(Label(
            text=self.app.tr.get('loading...', 'Loading...'),
            color=theme.get('stats_text', (0.6, 0.63, 0.65, 1)),
            font_name='SourceBold',
            font_size=dp(16)
        ))

        # Отписываемся от событий окна до удаления
        Window.unbind(on_resize=self._on_window_resize)

        parent.remove_widget(self)
        parent.add_widget(placeholder)

        def _do_create(dt):
            from ui.lesson_view import LessonView
            new_view = LessonView(
                self.app, lesson, self.lesson_manager, course_id=self.course_id
            )
            new_view.size_hint = saved_size_hint
            new_view.pos_hint = saved_pos_hint
            if placeholder.parent:
                placeholder.parent.remove_widget(placeholder)
            parent.add_widget(new_view)

        Clock.schedule_once(_do_create, 0)

    # ------------------------------------------------------------------
    # Тема вкладок
    # ------------------------------------------------------------------

    def _apply_tab_theme(self):
        """Применяет цвета из темы к вкладкам и подписывается на смену вкладки"""
        theme = ThemeManager.get_theme()

        tab_bg = theme.get('tab_inactive_bg', theme.get('widget_bg', (0.141, 0.145, 0.149, 1)))
        tab_active_bg = theme.get('tab_active_bg', theme.get('editor_bg', (0.188, 0.204, 0.251, 1)))
        tab_text = theme.get('tab_close_btn_text', theme.get('text_color', (0.85, 0.88, 0.90, 1)))
        tab_panel_bg = theme.get('tab_bar_bg', theme.get('action_bar_bg', (0.18, 0.18, 0.19, 1)))

        spacing = dp(4)
        self.tab_panel.tab_width = dp(100)
        self.tab_panel.tab_height = dp(35)

        if hasattr(self.tab_panel, '_tab_header'):
            self.tab_panel._tab_header.spacing = spacing

        for i, tab in enumerate(self.tab_panel.tab_list):
            tab.background_normal = ''
            tab.background_down = ''
            tab.color = tab_text
            tab.background_color = tab_bg
            if i < len(self.tab_panel.tab_list) - 1:
                tab.padding = [dp(5), dp(2), dp(9), dp(2)]
            else:
                tab.padding = [dp(5), dp(2), dp(5), dp(2)]

        if self.tab_panel.current_tab:
            self.tab_panel.current_tab.background_color = tab_active_bg

        self.tab_panel.canvas.before.clear()
        with self.tab_panel.canvas.before:
            Color(*tab_panel_bg)
            self.tab_panel_bg_rect = Rectangle(pos=self.tab_panel.pos, size=self.tab_panel.size)
        self.tab_panel.bind(pos=self._update_tab_bg, size=self._update_tab_bg)

        if hasattr(self.tab_panel, '_tab_header'):
            header = self.tab_panel._tab_header
            header.canvas.before.clear()
            with header.canvas.before:
                Color(*tab_panel_bg)
                header.bg_rect = Rectangle(pos=header.pos, size=header.size)
            header.bind(pos=self._update_header_bg, size=self._update_header_bg)

            for tab in self.tab_panel.tab_list:
                tab.background_normal = ''
                tab.background_down = ''
                tab.background_color = tab_bg

        self.tab_panel.bind(current_tab=self._on_tab_changed)

    def _draw_tab_separators(self, separator_color):
        tab_list = self.tab_panel.tab_list
        if not tab_list:
            return
        for i, tab in enumerate(tab_list):
            if hasattr(tab, '_separator_line'):
                try:
                    tab.canvas.before.remove(tab._separator_line)
                except Exception:
                    pass
            if i < len(tab_list) - 1:
                with tab.canvas.before:
                    Color(*separator_color)
                    tab._separator_line = Line(points=[
                        tab.right, tab.y,
                        tab.right, tab.y + tab.height
                    ], width=dp(1))

    def _update_tab_bg(self, instance, value):
        if hasattr(self, 'tab_panel_bg_rect'):
            self.tab_panel_bg_rect.pos = instance.pos
            self.tab_panel_bg_rect.size = instance.size

    def _update_content_bg(self, instance, value):
        if hasattr(instance, 'bg_rect'):
            instance.bg_rect.pos = instance.pos
            instance.bg_rect.size = instance.size

    def _update_scroll_bg(self, instance, value):
        if hasattr(instance, 'bg_rect'):
            instance.bg_rect.pos = instance.pos
            instance.bg_rect.size = instance.size

    def _update_active_tab_color(self):
        theme = ThemeManager.get_theme()
        tab_active_bg = theme.get('tab_active_bg', theme.get('editor_bg', (0.188, 0.204, 0.251, 1)))
        tab_bg = theme.get('tab_inactive_bg', theme.get('widget_bg', (0.141, 0.145, 0.149, 1)))
        tab_text = theme.get('tab_close_btn_text', theme.get('text_color', (0.85, 0.88, 0.90, 1)))
        tab_active_text = theme.get('text_color', (0.85, 0.88, 0.90, 1))

        for tab in self.tab_panel.tab_list:
            if tab == self.tab_panel.current_tab:
                tab.background_color = tab_active_bg
                tab.color = tab_active_text
            else:
                tab.background_color = tab_bg
                tab.color = tab_text

    def _update_header_bg(self, instance, value):
        if hasattr(instance, 'bg_rect'):
            instance.bg_rect.pos = instance.pos
            instance.bg_rect.size = instance.size

    # ------------------------------------------------------------------
    # Построители вкладок
    # ------------------------------------------------------------------

    def _create_theory_tab(self):
        """Создаёт содержимое вкладки Теория"""
        from widgets.markdown_label import MarkdownLabel

        theme = ThemeManager.get_theme()
        lang = self.app.current_language
        theory_text = self.lesson_manager.get_lesson_theory(self.lesson, lang)

        scroll = PassthroughScrollView(size_hint=(1, 1))
        content = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=dp(3),
            padding=[dp(3), dp(3), dp(3), dp(3)]
        )
        content.bind(minimum_height=content.setter('height'))

        with content.canvas.before:
            Color(*theme.get('editor_bg', (0.188, 0.204, 0.251, 1)))
            content.bg_rect = Rectangle(pos=content.pos, size=content.size)
        content.bind(pos=self._update_content_bg, size=self._update_content_bg)

        with scroll.canvas.before:
            Color(*theme.get('editor_bg', (0.188, 0.204, 0.251, 1)))
            scroll.bg_rect = Rectangle(pos=scroll.pos, size=scroll.size)
        scroll.bind(pos=self._update_scroll_bg, size=self._update_scroll_bg)

        theory_markdown = MarkdownLabel(text=theory_text, font_size=dp(12))
        theory_markdown._update_background()
        content.add_widget(theory_markdown)

        spacer = Label(size_hint_y=None, height=dp(10))
        content.add_widget(spacer)

        scroll.add_widget(content)
        self.theory_tab.add_widget(scroll)

    def _create_practice_tab(self):
        """Создаёт содержимое вкладки Практика"""
        theme = ThemeManager.get_theme()
        lang = self.app.current_language
        lesson = self.lesson

        template = self.lesson_manager.get_lesson_template(lesson, lang)

        if template:
            self.practice_editor = InteractiveCodeWidget(
                template=template,
                font_size=dp(13),
                size_hint=(1, 1),
            )
            Clock.schedule_once(lambda dt: self._update_code_from_editor(), 0.1)
            self.practice_tab.add_widget(self.practice_editor)
        else:
            from kivy.uix.codeinput import CodeInput
            from pygments.lexers import PythonLexer

            style_name = ThemeManager.get_syntax_style()
            self.practice_editor = CodeInput(
                lexer=PythonLexer(),
                style=style_name,
                size_hint=(1, 1),
                font_size=dp(13),
                background_color=theme.get('editor_bg', (0.188, 0.204, 0.251, 1)),
                foreground_color=theme.get('editor_text', (0.95, 0.95, 0.95, 1)),
                cursor_color=theme.get('editor_cursor', (1, 1, 1, 1)),
                tab_width=4
            )
            lesson_id = lesson.get('id', 0)
            starter_code = self.lesson_manager.get_lesson_starter_code(lesson, lang)
            saved_code = self.lesson_manager.get_saved_code(lesson_id)
            if saved_code:
                self.practice_editor.text = saved_code
                self.user_code = saved_code
            elif starter_code:
                self.practice_editor.text = starter_code
                self.user_code = starter_code

            self.practice_tab.add_widget(self.practice_editor)

        # Привязываем слушатель изменений.
        # InteractiveCodeWidget не имеет свойства 'text' — биндим только CodeInput.
        # Для InteractiveCodeWidget изменения кода отслеживаются через _update_code_from_editor.
        if not template and hasattr(self.practice_editor, 'bind'):
            try:
                self.practice_editor.bind(text=self._on_code_change)
            except (KeyError, Exception):
                pass

    def _create_task_tab(self):
        """Создаёт содержимое вкладки Задание"""
        from widgets.markdown_label import MarkdownLabel

        theme = ThemeManager.get_theme()
        lang = self.app.current_language
        lesson = self.lesson

        task_text = self.lesson_manager.get_lesson_task(lesson, lang)

        ready_codes = lesson.get(f'ready_codes_{lang}', [])
        if not ready_codes:
            ready_code = lesson.get(f'ready_code_{lang}', '')
            if ready_code:
                ready_codes = [ready_code]
            else:
                ready_codes = [lesson.get('ready_code_en', '# Template not available')]

        scroll = PassthroughScrollView(size_hint=(1, 1))
        content = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=dp(3),
            padding=[dp(3), dp(3), dp(3), dp(3)]
        )
        content.bind(minimum_height=content.setter('height'))

        with content.canvas.before:
            Color(*theme.get('editor_bg', (0.188, 0.204, 0.251, 1)))
            content.bg_rect = Rectangle(pos=content.pos, size=content.size)
        content.bind(pos=self._update_content_bg, size=self._update_content_bg)

        with scroll.canvas.before:
            Color(*theme.get('editor_bg', (0.188, 0.204, 0.251, 1)))
            scroll.bg_rect = Rectangle(pos=scroll.pos, size=scroll.size)
        scroll.bind(pos=self._update_scroll_bg, size=self._update_scroll_bg)

        # Текст задания
        task_markdown = MarkdownLabel(text=task_text, font_size=dp(12))
        task_markdown._update_background()
        content.add_widget(task_markdown)

        # Разделитель
        sep_label = Label(
            text="_" * 100,
            font_size=dp(10),
            font_name='SourceBold',
            color=theme.get('stats_text', (0.6, 0.63, 0.65, 1)),
            size_hint_y=None,
            height=dp(20)
        )
        content.add_widget(sep_label)

        # Заголовок шаблонов
        templates_title = Label(
            text=self.app.tr.get('templates', 'Templates') + ":",
            font_size=dp(12),
            font_name='SourceBold',
            color=theme.get('stats_text', (0.6, 0.63, 0.65, 1)),
            halign='left',
            size_hint_y=None,
            height=dp(25)
        )
        content.add_widget(templates_title)

        # Блоки шаблонов
        def add_copy_block(parent, title_text, code_text):
            if not code_text or not code_text.strip():
                return

            title = Label(
                text=title_text,
                font_size=dp(12),
                font_name='SourceBold',
                color=theme.get('stats_text', (0.6, 0.63, 0.65, 1)),
                halign='left',
                size_hint_y=None,
                height=dp(20)
            )
            parent.add_widget(title)

            code_scroll = TemplateScrollView(
                size_hint_y=None,
                height=dp(250),
                do_scroll_x=False,
                do_scroll_y=True,
                bar_width=dp(4)
            )

            code_input = TextInput(
                text=code_text,
                readonly=True,
                font_size=dp(12),
                font_name='JetBrainsMono',
                background_color=theme.get('lesson_input_bg', (0.25, 0.30, 0.40, 1)),
                foreground_color=theme.get('lesson_input_text', (0.95, 0.95, 0.95, 1)),
                size_hint_y=None,
                height=max(dp(250), len(code_text.split('\n')) * dp(20) + dp(20)),
                padding=(dp(8), dp(8)),
                cursor_blink=False,
                selection_color=(0, 0, 0, 0),
                cursor_color=(0, 0, 0, 0),
                use_handles=False,
                use_bubble=False,
                multiline=True,
                do_wrap=False,
            )

            def _disable_selection(*args):
                if code_input.focus:
                    code_input.focus = False
                code_input.cancel_selection()
                try:
                    for h in ('_handle_left', '_handle_right', '_handle_middle'):
                        handle = getattr(code_input, h, None)
                        if handle:
                            handle.opacity = 0
                except Exception:
                    pass

            code_input.bind(focus=_disable_selection)
            code_input.bind(on_touch_down=lambda *a: _disable_selection())

            code_scroll.add_widget(code_input)
            parent.add_widget(code_scroll)

            copy_btn = Button(
                text=self.app.tr.get('copy_to_clipboard', 'Copy to clipboard'),
                font_name='SourceBold',
                size_hint_y=None,
                height=dp(30),
                background_color=theme.get('btn_success_bg', (0.2, 0.5, 0.2, 1)),
                background_normal='', background_down='',
                color=(1, 1, 1, 1),
                font_size=dp(11)
            )
            copy_btn.template_text = code_text

            def copy_template(btn):
                VibrationManager.vibrate(0.02)
                Clipboard.copy(btn.template_text)
                self.app.show_result_popup(self.app.tr.get('result_copied', 'Copied to clipboard'))

            copy_btn.bind(on_release=copy_template)
            parent.add_widget(copy_btn)
            parent.add_widget(Label(size_hint_y=None, height=dp(8)))

        for idx, code in enumerate(ready_codes, 1):
            add_copy_block(content, f"{self.app.tr.get('template', 'Template')} {idx}:", code)

        tip_label = Label(
            text=self.app.tr.get('template_tip',
                                 'Tip: Copy any template above and paste it into the main editor. Then you can modify it as you like!'),
            font_size=dp(10),
            font_name='SourceBold',
            color=theme.get('stats_text', (0.6, 0.63, 0.65, 1)),
            halign='left',
            size_hint_y=None,
            height=dp(50)
        )
        tip_label.bind(width=lambda inst, val: setattr(inst, 'text_size', (val, None)))
        content.add_widget(tip_label)

        scroll.add_widget(content)
        self.task_tab.add_widget(scroll)

    def _create_hint_tab(self):
        """Создаёт содержимое вкладки Подсказка"""
        theme = ThemeManager.get_theme()
        lang = self.app.current_language
        hint_text = self.lesson_manager.get_lesson_hint(self.lesson, lang)

        scroll = PassthroughScrollView(size_hint=(1, 1))
        content = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(10), padding=dp(10))
        content.bind(minimum_height=content.setter('height'))

        with content.canvas.before:
            Color(*theme.get('editor_bg', (0.188, 0.204, 0.251, 1)))
            content.bg_rect = Rectangle(pos=content.pos, size=content.size)
        content.bind(pos=self._update_content_bg, size=self._update_content_bg)

        with scroll.canvas.before:
            Color(*theme.get('editor_bg', (0.188, 0.204, 0.251, 1)))
            scroll.bg_rect = Rectangle(pos=scroll.pos, size=scroll.size)
        scroll.bind(pos=self._update_scroll_bg, size=self._update_scroll_bg)

        hint_label = Label(
            text=hint_text if hint_text else self.app.tr.get('no_hint', 'No hint available'),
            font_size=dp(13),
            font_name='SourceBold',
            color=theme.get('stats_text', (0.6, 0.63, 0.65, 1)),
            halign='left',
            valign='top',
            size_hint_y=None
        )
        hint_label.bind(width=lambda inst, val: setattr(inst, 'text_size', (val, None)))
        hint_label.bind(texture_size=lambda inst, sz: setattr(inst, 'height', sz[1] + dp(20)))
        content.add_widget(hint_label)

        scroll.add_widget(content)
        self.hint_tab.add_widget(scroll)

    # ------------------------------------------------------------------
    # Работа с кодом
    # ------------------------------------------------------------------

    def _update_code_from_editor(self):
        """Принудительно обновляет код из редактора"""
        if hasattr(self, 'practice_editor') and hasattr(self.practice_editor, 'get_user_code'):
            self.user_code = self.practice_editor.get_user_code()
            self.lesson_manager.save_lesson_code(self.lesson.get('id', 0), self.user_code)

    def _on_code_change(self, instance, value):
        """
        ОПТИМИЗАЦИЯ: дебаунс — сохраняем на диск через 1.5 с после последнего изменения,
        а не при каждом нажатии клавиши.
        """
        if hasattr(self, 'practice_editor') and hasattr(self.practice_editor, 'get_user_code'):
            self.user_code = self.practice_editor.get_user_code()
        else:
            self.user_code = value

        if self._save_event:
            self._save_event.cancel()
        self._save_event = Clock.schedule_once(
            lambda dt: self.lesson_manager.save_lesson_code(
                self.lesson.get('id', 0), self.user_code
            ),
            1.5
        )

    def _run_code(self, instance):
        """Запускает код из редактора"""
        self._update_code_from_editor()

        if not self.user_code.strip():
            self.app.show_result_popup(self.app.tr.get('enter_code_first', 'Enter code first'))
            return

        if hasattr(self.app, 'code_executor'):
            def result_callback(result):
                self.app._show_result(result)

            self.app.code_executor.run(
                self.user_code,
                self.app.input_handler.handle_input,
                result_callback
            )
        else:
            self.app.show_result_popup("Executor not available")

    # ------------------------------------------------------------------
    # Завершение урока
    # ------------------------------------------------------------------

    def _mark_completed(self, instance):
        self._show_completion_dialog()

    def _show_completion_dialog(self):
        theme = ThemeManager.get_theme()
        tr = self.app.tr

        content = BoxLayout(orientation='vertical', padding=dp(15), spacing=dp(15))

        msg_label = Label(
            text=tr.get('confirm_complete_lesson', 'Mark this lesson as completed?'),
            font_size=dp(14),
            color=theme['text_color'],
            halign='center',
            size_hint_y=None,
            height=dp(50)
        )
        content.add_widget(msg_label)

        btn_layout = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(10))

        def on_confirm(btn):
            popup.dismiss()
            self._actual_mark_completed()

        def on_cancel(btn):
            popup.dismiss()

        confirm_btn = Button(
            text=tr.get('yes', 'Yes'),
            font_name='SourceBold',
            background_color=theme.get('btn_success_bg', (0.2, 0.5, 0.2, 1)),
            background_normal='', background_down='',
            color=(1, 1, 1, 1),
            on_release=on_confirm
        )

        cancel_btn = Button(
            text=tr.get('later', 'Later'),
            font_name='SourceBold',
            background_color=theme['widget_bg'],
            background_normal='', background_down='',
            color=theme['text_color'],
            on_release=on_cancel
        )

        btn_layout.add_widget(cancel_btn)
        btn_layout.add_widget(confirm_btn)
        content.add_widget(btn_layout)

        popup = ThemedPopup(
            title=tr.get('mark_completed', 'Mark as Completed'),
            title_color=theme.get('popup_title', theme['text_color']),
            title_bg=theme.get('popup_title_bg', theme['widget_bg']),
            popup_bg=theme.get('popup_bg', theme.get('widget_bg', (0.188, 0.204, 0.251, 1))),
            separator_color=theme.get('popup_separator', (0.25, 0.25, 0.25, 1)),
            content=content,
            size_hint=(0.7, 0.3),
            auto_dismiss=False
        )
        popup.open()

    def _actual_mark_completed(self):
        lesson_id = self.lesson.get('id', 0)
        success = self.lesson_manager.mark_lesson_completed(lesson_id, self.course_id, self.user_code)

        if success:
            self.complete_btn.disabled = True
            self.complete_btn.text = "✓ " + self.app.tr.get('completed', 'Completed')
            theme = ThemeManager.get_theme()
            self.complete_btn.background_color = theme.get('stats_text', (0.6, 0.63, 0.65, 1))

            self.app.show_result_popup(
                f"{self.app.tr.get('lesson_completed', 'Lesson completed!')} +{self.lesson.get('xp', 10)} XP"
            )
            self._offer_next_lesson()
        else:
            self.app.show_result_popup(
                self.app.tr.get('already_completed', 'Lesson already completed')
            )

    def _offer_next_lesson(self):
        theme = ThemeManager.get_theme()
        tr = self.app.tr

        next_lesson = self.lesson_manager.get_next_lesson(self.course_id)
        if not next_lesson:
            self.app.show_result_popup(tr.get('course_completed_msg', 'Congratulations! You completed the course!'))
            self._close(None)
            return

        content = BoxLayout(orientation='vertical', padding=dp(15), spacing=dp(15))

        msg_label = Label(
            text=tr.get('next_lesson_offer', 'Do you want to continue to the next lesson?'),
            font_size=dp(13),
            color=theme['text_color'],
            halign='center',
            size_hint_y=None,
            height=dp(60)
        )
        content.add_widget(msg_label)

        btn_layout = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(10))

        def on_continue(btn):
            popup.dismiss()
            self._close(None)
            self._open_next_lesson(next_lesson)

        def on_later(btn):
            popup.dismiss()
            self._close(None)

        continue_btn = Button(
            text=tr.get('continue', 'Continue'),
            font_name='SourceBold',
            background_color=theme.get('btn_success_bg', (0.2, 0.5, 0.2, 1)),
            background_normal='', background_down='',
            color=(1, 1, 1, 1),
            on_release=on_continue
        )

        later_btn = Button(
            text=tr.get('later', 'Later'),
            font_name='SourceBold',
            background_color=theme['widget_bg'],
            background_normal='', background_down='',
            color=theme['text_color'],
            on_release=on_later
        )

        btn_layout.add_widget(later_btn)
        btn_layout.add_widget(continue_btn)
        content.add_widget(btn_layout)

        popup = ThemedPopup(
            title=tr.get('lesson_completed', 'Lesson Completed!'),
            title_color=theme.get('popup_title', theme['text_color']),
            title_bg=theme.get('popup_title_bg', theme['widget_bg']),
            popup_bg=theme.get('popup_bg', theme.get('widget_bg', (0.188, 0.204, 0.251, 1))),
            separator_color=theme.get('popup_separator', (0.25, 0.25, 0.25, 1)),
            content=content,
            size_hint=(0.8, 0.35),
            auto_dismiss=False
        )
        popup.open()

    def _open_next_lesson(self, lesson):
        from ui.lesson_view import LessonView

        new_view = LessonView(self.app, lesson, self.lesson_manager, course_id=self.course_id)
        new_view.size_hint = (0.92, LessonView._BASE_SIZE_HINT_Y)
        new_view.pos_hint = {'center_x': 0.5, 'center_y': LessonView._BASE_CENTER_Y}

        if hasattr(self.app, 'root_layout'):
            self.app.root_layout.add_widget(new_view)

    # ------------------------------------------------------------------
    # Клавиатура / окно
    # ------------------------------------------------------------------

    def _on_window_resize(self, window, width, height):
        """
        На Android при показе клавиатуры Window.height уменьшается.
        Пересчитываем позицию окна урока чтобы оно не уходило под клавиатуру.
        """
        if not self.parent:
            return

        parent_h = self.parent.height
        if parent_h <= 0:
            return

        visible_h = height

        if visible_h < self._win_height * 0.85:
            kb_h = self._win_height - visible_h
            kb_fraction = kb_h / parent_h

            new_size_hint_y = (visible_h / parent_h) - 0.02
            new_size_hint_y = max(new_size_hint_y, 0.35)

            bottom_edge = kb_fraction + 0.01
            new_center_y = bottom_edge + new_size_hint_y / 2.0
            new_center_y = min(new_center_y, 0.98 - new_size_hint_y / 2.0)

            self.size_hint_y = new_size_hint_y
            self.pos_hint = {'center_x': 0.5, 'center_y': new_center_y}
        else:
            self._win_height = height
            self.size_hint_y = self._BASE_SIZE_HINT_Y
            self.pos_hint = {'center_x': 0.5, 'center_y': self._BASE_CENTER_Y}

    # ------------------------------------------------------------------
    # Закрытие / вибрация
    # ------------------------------------------------------------------

    def _close(self, instance):
        """Закрывает диалог урока"""
        # Отменяем отложенное сохранение если есть
        if self._save_event:
            self._save_event.cancel()
            self._save_event = None
        Window.unbind(on_resize=self._on_window_resize)
        if self.parent:
            self.parent.remove_widget(self)

    def _wrap_buttons(self):
        """Обёртывает все кнопки урока для вибрации"""
        if hasattr(self.app, 'wrap_widget_buttons'):
            self.app.wrap_widget_buttons(self)

"""
Live code analyzer for Python with real-time error detection
"""

import re
import ast
import keyword
import threading
from typing import List, Dict, Set, Tuple, Optional

from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.graphics import Color, Rectangle, Line
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView


class CodeAnalyzer:
    """Анализирует Python код и находит ошибки"""

    # Встроенные функции Python
    BUILTINS: Set[str] = {
        'abs', 'all', 'any', 'bin', 'bool', 'chr', 'dict', 'dir', 'enumerate',
        'filter', 'float', 'format', 'int', 'len', 'list', 'map', 'max',
        'min', 'print', 'range', 'round', 'set', 'sorted', 'str', 'sum',
        'tuple', 'type', 'zip', 'open', 'id', 'hex', 'oct', 'ord',
        'isinstance', 'issubclass', 'callable', 'hasattr', 'getattr', 'setattr'
    }

    def __init__(self):
        self.reset()

    def reset(self):
        """Сбрасывает состояние анализатора"""
        self.errors = []
        self.warnings = []
        self.infos = []
        self._defined_names = set()
        self._imported_names = set()
        self._class_names = set()
        self._function_names = set()
        self._used_names = set()

    def analyze(self, code: str) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """
        Анализирует код и возвращает ошибки, предупреждения и подсказки
        """
        self.reset()

        if not code or not code.strip():
            return [], [], []

        lines = code.split('\n')

        # 1. Синтаксический анализ через AST
        try:
            tree = ast.parse(code)
            self._analyze_ast(tree)
        except SyntaxError as e:
            self._add_syntax_error(e, lines)
        except Exception as e:
            self._add_error(0, f"Ошибка анализа: {str(e)}", "critical")

        # 2. Анализ каждой строки
        self._analyze_lines(lines)

        # 3. Проверка неопределённых переменных
        self._check_undefined_variables()

        # 4. Дополнительные проверки
        self._check_common_mistakes(lines)

        return self.errors, self.warnings, self.infos

    def _analyze_ast(self, tree: ast.AST):
        """Рекурсивный анализ AST"""
        for node in ast.walk(tree):
            # Определение имён
            if isinstance(node, ast.FunctionDef):
                self._function_names.add(node.name)
            elif isinstance(node, ast.ClassDef):
                self._class_names.add(node.name)
            elif isinstance(node, ast.Name):
                if isinstance(node.ctx, ast.Store):
                    self._defined_names.add(node.id)
                elif isinstance(node.ctx, ast.Load):
                    self._used_names.add(node.id)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    self._imported_names.add(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    self._imported_names.add(alias.name)

    def _analyze_lines(self, lines: List[str]):
        """Анализирует каждую строку на ошибки"""
        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            if not stripped or stripped.startswith('#'):
                continue

            # Пропущенные двоеточия
            if (stripped.startswith(
                    ('def ', 'class ', 'if ', 'elif ', 'else', 'for ', 'while ', 'with ', 'try:', 'except',
                     'finally:')) and
                    not stripped.endswith(':') and
                    not stripped.endswith('\\') and
                    ':' not in stripped):
                self._add_error(i, "Пропущено двоеточие ':' в конце строки", "error")

            # Неправильные отступы после def/class/etc
            if i > 1 and stripped and not stripped.startswith(
                    ('def ', 'class ', 'if ', 'elif ', 'else', 'for ', 'while ', 'with ', 'try:', 'except', 'finally:',
                     '#', '@')):
                prev_line = lines[i - 2].strip() if i >= 2 else ""
                if prev_line.endswith(':') and not line.startswith((' ', '\t')):
                    self._add_warning(i, f"Возможно, нужен отступ после '{prev_line}'", "info")

    def _check_undefined_variables(self):
        """Проверяет использование неопределённых переменных"""
        for name in self._used_names:
            # Игнорируем встроенные имена
            if name in self.BUILTINS or name in keyword.kwlist:
                continue
            # Игнорируем импортированные имена
            if name in self._imported_names:
                continue
            # Игнорируем параметры функций (сложно определить через AST)
            if name in ('self', 'cls'):
                continue

            if name not in self._defined_names:
                self._add_warning(0, f"Возможно, переменная '{name}' не определена", "warning")

    def _check_common_mistakes(self, lines: List[str]):
        """Проверяет распространённые ошибки"""
        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # = vs ==
            if ' = ' in line and ('if' in line or 'while' in line):
                self._add_warning(i, "Возможно, вы хотели использовать '==' вместо '=' в условии", "warning")

            # Пропущенные пробелы после запятой
            if ', ' not in line and ',' in line and not line.endswith(',') and not '"' in line and not "'" in line:
                self._add_info(i, "Рекомендуется ставить пробел после запятой", "style")

            # Слишком длинная строка
            if len(line) > 79:
                self._add_info(i, f"Строка слишком длинная ({len(line)} > 79 символов)", "style")

            # Пустая строка с пробелами
            if line.strip() == '' and len(line) > 0:
                self._add_info(i, "Лишние пробелы в пустой строке", "style")

    def _add_syntax_error(self, error: SyntaxError, lines: List[str]):
        """Добавляет синтаксическую ошибку"""
        line_no = error.lineno or 0
        msg = str(error).split('\n')[0]

        # Улучшаем сообщения об ошибках
        if "unexpected indent" in msg:
            msg = "Неожиданный отступ - проверьте количество пробелов"
        elif "expected an indented block" in msg:
            msg = "Ожидается блок с отступом (добавьте 4 пробела)"
        elif "invalid syntax" in msg and line_no > 0:
            line = lines[line_no - 1] if line_no <= len(lines) else ""
            if line.strip().endswith(':'):
                msg = f"Пропущено тело после '{line.strip()}'"
            elif '(' in line and ')' not in line:
                msg = "Не закрыта скобка '('"
            elif '[' in line and ']' not in line:
                msg = "Не закрыта квадратная скобка '['"
            elif '{' in line and '}' not in line:
                msg = "Не закрыта фигурная скобка '{'"

        self._add_error(line_no, msg, "error")

    def _add_error(self, line: int, message: str, severity: str = "error"):
        self.errors.append({
            'line': line,
            'message': message,
            'severity': severity
        })

    def _add_warning(self, line: int, message: str, severity: str = "warning"):
        self.warnings.append({
            'line': line,
            'message': message,
            'severity': severity
        })

    def _add_info(self, line: int, message: str, severity: str = "info"):
        self.infos.append({
            'line': line,
            'message': message,
            'severity': severity
        })


class ErrorAnnotationWidget(Widget):
    """Виджет для отображения ошибок прямо в редакторе"""

    def __init__(self, text_input, **kwargs):
        super().__init__(**kwargs)
        self.text_input = text_input
        self.analyzer = CodeAnalyzer()
        self.errors = []
        self.warnings = []
        self.infos = []
        self._update_scheduled = False
        self._underline_cache = {}

        # Привязываемся к изменению текста
        self.text_input.bind(text=self._on_text_change)
        self.text_input.bind(pos=self._update_display)
        self.text_input.bind(size=self._update_display)

    def _on_text_change(self, instance, value):
        """Запускает анализ при изменении текста"""
        if not self._update_scheduled:
            self._update_scheduled = True
            Clock.schedule_once(self._analyze_code, 0.5)  # Задержка для производительности

    def _analyze_code(self, dt):
        """Анализирует код в отдельном потоке"""
        self._update_scheduled = False

        def analyze():
            code = self.text_input.text
            errors, warnings, infos = self.analyzer.analyze(code)

            Clock.schedule_once(lambda dt: self._update_errors(errors, warnings, infos))

        threading.Thread(target=analyze, daemon=True).start()

    def _update_errors(self, errors, warnings, infos):
        """Обновляет отображение ошибок"""
        self.errors = errors
        self.warnings = warnings
        self.infos = infos
        self._update_display()

    def _update_display(self, *args):
        """Перерисовывает подчёркивания ошибок"""
        # Очищаем старые
        for line_widget in self._underline_cache.values():
            if line_widget and hasattr(line_widget, 'canvas'):
                line_widget.canvas.after.clear()

        self._underline_cache.clear()

        if not self.text_input or not self.text_input.text:
            return

        lines = self.text_input.text.split('\n')
        line_height = self._get_line_height()
        text_width = self.text_input.width

        # Группируем ошибки по строкам
        errors_by_line = {}
        for err in self.errors:
            if err['line'] > 0:
                errors_by_line.setdefault(err['line'], []).append(err)
        for warn in self.warnings:
            if warn['line'] > 0:
                errors_by_line.setdefault(warn['line'], []).append(warn)

        # Рисуем подчёркивания для каждой строки с ошибкой
        for line_num, issues in errors_by_line.items():
            if line_num > len(lines):
                continue

            # Определяем цвет по типу ошибки
            has_error = any(i.get('severity') == 'error' for i in issues)
            has_warning = any(i.get('severity') == 'warning' for i in issues)

            if has_error:
                color = (0.9, 0.2, 0.2, 0.8)  # Красный для ошибок
                width = dp(2)
            elif has_warning:
                color = (0.9, 0.7, 0.1, 0.8)  # Жёлтый для предупреждений
                width = dp(1.5)
            else:
                color = (0.4, 0.6, 0.9, 0.8)  # Синий для подсказок
                width = dp(1)

            # Вычисляем позицию строки
            y = self.text_input.y + self.text_input.height - (line_num) * line_height

            # Создаём подчёркивание
            with self.text_input.canvas.after:
                Color(*color)
                line = Line(
                    points=[self.text_input.x + dp(5), y - dp(2),
                            self.text_input.x + text_width - dp(5), y - dp(2)],
                    width=width
                )
                self._underline_cache[line_num] = line

    def _get_line_height(self) -> float:
        """Возвращает высоту строки в пикселях"""
        if hasattr(self.text_input, 'line_height'):
            return self.text_input.line_height
        return dp(20)  # Значение по умолчанию


class ErrorInfoPanel(BoxLayout):
    """Панель с информацией об ошибках в реальном времени"""

    def __init__(self, text_input, **kwargs):
        super().__init__(**kwargs)
        self.text_input = text_input
        self.orientation = 'vertical'
        self.size_hint_y = None
        self.height = 0
        self.visible = False

        self._create_ui()

        # Привязываемся к изменениям (через аннотацию)
        self.error_annotation = ErrorAnnotationWidget(text_input)

    def _create_ui(self):
        """Создаёт интерфейс панели"""
        # Заголовок
        self.header = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(24))

        self.title_label = Label(
            text="🔍 Анализ кода",
            font_size=dp(12),
            font_name='SourceBold',
            halign='left',
            size_hint_x=0.8
        )

        self.close_btn = Button(
            text="✕",
            font_size=dp(12),
            size_hint_x=0.2,
            background_color=(0.5, 0.2, 0.2, 1),
            background_normal=''
        )
        self.close_btn.bind(on_release=self.hide)

        self.header.add_widget(self.title_label)
        self.header.add_widget(self.close_btn)
        self.add_widget(self.header)

        # Скроллируемая область для ошибок
        self.scroll = ScrollView(size_hint=(1, 1))
        self.errors_container = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=dp(2)
        )
        self.errors_container.bind(minimum_height=self.errors_container.setter('height'))
        self.scroll.add_widget(self.errors_container)
        self.add_widget(self.scroll)

        # Обновляем цвета при смене темы
        self._update_theme()

    def _update_theme(self):
        """Обновляет цвета панели"""
        try:
            from ide_core.themes import ThemeManager
            theme = ThemeManager.get_theme()
            self.title_label.color = theme['text_color']
        except:
            pass

    def update_errors(self, errors, warnings, infos):
        """Обновляет список ошибок на панели"""
        self.errors_container.clear_widgets()

        all_issues = []

        for err in errors:
            all_issues.append({
                'line': err.get('line', 0),
                'message': err.get('message', ''),
                'type': 'error',
                'icon': '❌'
            })

        for warn in warnings:
            all_issues.append({
                'line': warn.get('line', 0),
                'message': warn.get('message', ''),
                'type': 'warning',
                'icon': '⚠️'
            })

        for info in infos:
            all_issues.append({
                'line': info.get('line', 0),
                'message': info.get('message', ''),
                'type': 'info',
                'icon': 'ℹ️'
            })

        if not all_issues:
            # Показываем сообщение "Нет ошибок"
            ok_label = Label(
                text="✓ Код выглядит хорошо!",
                font_size=dp(10),
                color=(0.3, 0.7, 0.3, 1),
                size_hint_y=None,
                height=dp(25)
            )
            self.errors_container.add_widget(ok_label)
        else:
            # Показываем все проблемы
            for issue in all_issues:
                self._add_issue_row(issue)

        # Показываем панель, если есть проблемы
        if all_issues:
            self.show()

    def _add_issue_row(self, issue: Dict):
        """Добавляет строку с проблемой"""
        try:
            from ide_core.themes import ThemeManager
            theme = ThemeManager.get_theme()
        except:
            theme = {'text_color': (0.85, 0.88, 0.90, 1)}

        row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(22), spacing=dp(5))

        # Иконка
        icon = Label(
            text=issue['icon'],
            font_size=dp(10),
            size_hint_x=0.1,
            color=theme.get('text_color', (0.85, 0.88, 0.90, 1))
        )

        # Текст ошибки
        text = f"Строка {issue['line']}: {issue['message']}" if issue['line'] > 0 else issue['message']
        if len(text) > 50:
            text = text[:47] + "..."

        msg_label = Label(
            text=text,
            font_size=dp(9),
            size_hint_x=0.7,
            color=theme.get('text_color', (0.85, 0.88, 0.90, 1)),
            halign='left'
        )
        msg_label.bind(size=lambda s, sz: setattr(msg_label, 'text_size', (sz[0], None)))

        # Кнопка перехода к строке
        goto_btn = Button(
            text="→",
            font_size=dp(9),
            size_hint_x=0.2,
            background_color=theme.get('widget_bg', (0.141, 0.145, 0.149, 1)),
            background_normal=''
        )
        if issue['line'] > 0:
            goto_btn.bind(on_release=lambda x, ln=issue['line']: self._goto_line(ln))

        row.add_widget(icon)
        row.add_widget(msg_label)
        row.add_widget(goto_btn)

        app = App.get_running_app()
        if app and hasattr(app, 'wrap_widget_buttons'):
            app.wrap_widget_buttons(row)

        self.errors_container.add_widget(row)

    def _goto_line(self, line_num: int):
        """Переходит к указанной строке"""
        if not self.text_input:
            return

        # Вычисляем позицию курсора
        lines = self.text_input.text.split('\n')
        char_pos = 0
        for i in range(line_num - 1):
            if i < len(lines):
                char_pos += len(lines[i]) + 1

        try:
            self.text_input.cursor = self.text_input.get_cursor_from_index(char_pos)
            self.text_input.focus = True

            # Прокручиваем к видимой области
            parent = self.text_input.parent
            while parent:
                if hasattr(parent, 'scroll_y'):
                    total_lines = len(lines)
                    target_y = 1.0 - (line_num / total_lines)
                    parent.scroll_y = max(0.0, min(1.0, target_y))
                    break
                parent = parent.parent
        except:
            pass

    def show(self):
        """Показывает панель"""
        if not self.visible:
            self.visible = True
            self.height = dp(120)

    def hide(self, *args):
        """Скрывает панель"""
        if self.visible:
            self.visible = False
            self.height = 0
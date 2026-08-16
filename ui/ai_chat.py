"""
Окно чата с ИИ-тьютором.

Современный мессенджер-стиль:
  * пузыри сообщений с «хвостиками» по сторонам и временем отправки;
  * плавный автоскролл вниз + кнопка «к последнему сообщению»;
  * индикатор набора текста, стриминг ответа;
  * поле ввода, растущее по мере набора (1..5 строк);
  * Enter — отправить, Shift+Enter — новая строка;
  * копирование текста сообщения;
  * чат строго прилипает к верхней границе экранной клавиатуры.
"""

from datetime import datetime

from kivy.animation import Animation
from kivy.clock import Clock
from kivy.core.clipboard import Clipboard
from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.properties import NumericProperty
from kivy.utils import platform

try:
    from utils.crash_logger import log_error as crash_log_error
except ImportError:
    crash_log_error = None
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget

from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDIconButton
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel

try:
    from ide_core.themes import DARK_THEME, LIGHT_THEME, ThemeManager
except Exception:  # pragma: no cover - автономный запуск
    ThemeManager = None
    DARK_THEME = {
        "popup_bg": (0.09, 0.09, 0.12, 1),
        "window_bg": (0.07, 0.07, 0.09, 1),
        "widget_bg": (0.16, 0.16, 0.20, 1),
        "text_color": (0.93, 0.93, 0.96, 1),
        "run_btn_bg": (0.596, 0.486, 1.0, 1),
        "btn_danger_bg": (0.85, 0.30, 0.35, 1),
    }
    LIGHT_THEME = {
        "popup_bg": (0.97, 0.97, 0.98, 1),
        "window_bg": (1, 1, 1, 1),
        "widget_bg": (0.90, 0.90, 0.93, 1),
        "text_color": (0.10, 0.10, 0.14, 1),
        "run_btn_bg": (0.44, 0.35, 0.92, 1),
        "btn_danger_bg": (0.85, 0.30, 0.35, 1),
    }

MarkdownLabel = None
for _md_path in (
    "widgets.markdown_label",
    "ui.widgets.markdown_label",
    "ui.markdown_label",
    "markdown_label",
):
    try:
        MarkdownLabel = __import__(_md_path, fromlist=["MarkdownLabel"]).MarkdownLabel
        break
    except Exception:
        continue


if MarkdownLabel is not None:

    class BubbleMarkdownLabel(MarkdownLabel):
        """MarkdownLabel без собственного фона — фон рисует пузырь."""

        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.padding = [0, 0, 0, 0]
            self.spacing = dp(2)

        def _update_background(self, *args):
            self.canvas.before.clear()

        def set_text(self, text):
            super().set_text(text)
            Clock.schedule_once(self._fix_code_blocks, 0)
            Clock.schedule_once(self._fix_code_blocks, 0.15)

        def _fix_code_blocks(self, *args):
            """Код-блок должен показывать все строки с первой, а не скроллиться."""
            for ti in _iter_text_inputs(self):
                ti.cursor = (0, 0)
                ti.scroll_y = 0
                ti.scroll_x = 0

else:  # pragma: no cover - автономный запуск
    BubbleMarkdownLabel = None


def _iter_text_inputs(widget):
    for child in widget.children:
        if isinstance(child, TextInput):
            yield child
        else:
            for sub in _iter_text_inputs(child):
                yield sub


MAX_BUBBLE_RATIO = 0.82          # максимальная ширина пузыря от ширины чата
MAX_MD_BUBBLE_RATIO = 0.97       # markdown-ответ занимает почти всю ширину
INPUT_MIN_HEIGHT = dp(44)
INPUT_MAX_HEIGHT = dp(132)
BUBBLE_RADIUS = dp(16)
BUBBLE_TAIL_RADIUS = dp(4)


def _mix(color, other, k):
    """Линейная интерполяция цветов."""
    return tuple(c + (o - c) * k for c, o in zip(color[:4], other[:4]))


def _now():
    return datetime.now().strftime("%H:%M")


class ChatTextInput(TextInput):
    """TextInput с отправкой по Enter и переносом по Shift+Enter."""

    def __init__(self, on_submit=None, **kwargs):
        super().__init__(**kwargs)
        self.on_submit = on_submit

    def keyboard_on_key_down(self, window, keycode, text, modifiers):
        if keycode[1] in ("enter", "numpadenter") and "shift" not in (modifiers or []):
            if self.on_submit:
                self.on_submit()
            return True
        return super().keyboard_on_key_down(window, keycode, text, modifiers)


class MessageRow(BoxLayout):
    """Строка сообщения: пузырь + распорка, прижимающая его к нужному краю."""

    def __init__(self, theme, text, side="left", markdown=False, **kwargs):
        try:
            super().__init__(
                orientation="horizontal",
                size_hint_y=None,
                spacing=dp(6),
                **kwargs,
            )
            self.theme = theme
            self.side = side
            self.markdown = markdown and BubbleMarkdownLabel is not None

            # Защита от некорректных данных
            if text is None:
                text = ""
            if not isinstance(text, str):
                text = str(text)

            is_user = side == "right"
            base = theme["widget_bg"]
            accent = theme.get("run_btn_bg", (0.596, 0.486, 1.0, 1))
            bubble_bg = _mix(base, accent, 0.55) if is_user else base
            text_color = (1, 1, 1, 1) if is_user else theme["text_color"]

            radius = (
                [BUBBLE_RADIUS, BUBBLE_RADIUS, BUBBLE_TAIL_RADIUS, BUBBLE_RADIUS]
                if is_user
                else [BUBBLE_RADIUS, BUBBLE_RADIUS, BUBBLE_RADIUS, BUBBLE_TAIL_RADIUS]
            )

            self.bubble = MDCard(
                orientation="vertical",
                size_hint=(None, None),
                padding=[dp(12), dp(8), dp(12), dp(6)],
                spacing=dp(2),
                radius=radius,
                md_bg_color=bubble_bg,
                elevation=0,
                ripple_behavior=False,
            )

            self._raw_text = text
            self._pending_text = None
            self._render_ev = None

            if markdown and BubbleMarkdownLabel is not None:
                try:
                    self.label = BubbleMarkdownLabel(text=text, font_size=sp(15))
                    self.label.bind(height=lambda *_: self._resize())
                except Exception as e:
                    print(f"[AI Chat] BubbleMarkdownLabel creation error: {e}")
                    # Fallback to regular label
                    self.label = Label(
                        text=text,
                        markup=False,
                        size_hint=(None, None),
                        halign="left",
                        valign="top",
                        color=text_color,
                        font_size=sp(15),
                        line_height=1.15,
                    )
                    self.label.bind(texture_size=lambda *_: self._resize())
            else:
                self.label = Label(
                    text=text,
                    markup=False,
                    size_hint=(None, None),
                    halign="left",
                    valign="top",
                    color=text_color,
                    font_size=sp(15),
                    line_height=1.15,
                )
                self.label.bind(texture_size=lambda *_: self._resize())

            self.meta = Label(
                text=_now(),
                size_hint=(1, None),
                height=dp(13),
                halign="right",
                valign="middle",
                font_size=sp(10),
                color=_mix(text_color, (0.5, 0.5, 0.5, 1), 0.45),
            )
            self.meta.bind(size=lambda inst, val: setattr(inst, "text_size", val))

            self.bubble.add_widget(self.label)
            self.bubble.add_widget(self.meta)

            spacer = Widget(size_hint_x=1)
            if is_user:
                self.add_widget(spacer)
                self.add_widget(self.bubble)
            else:
                self.add_widget(self.bubble)
                self.add_widget(spacer)

            self._long_press_ev = None
            self._bubble_bg = bubble_bg

            self.bind(width=lambda *_: self._resize())
            Clock.schedule_once(lambda dt: self._resize(), 0)
        except Exception as e:
            print(f"[AI Chat] MessageRow __init__ error: {e}")
            # Создаем минимальный виджет в случае ошибки
            self.label = Label(text="Error")
            self.add_widget(self.label)

    # -- копирование ------------------------------------------------------
    def on_touch_down(self, touch):
        if self.bubble.collide_point(*touch.pos):
            if touch.button == "right":
                self.copy_to_clipboard()
                return True
            self._long_press_ev = Clock.schedule_once(
                lambda dt: self.copy_to_clipboard(), 0.45
            )
        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        self._cancel_long_press()
        return super().on_touch_up(touch)

    def on_touch_move(self, touch):
        self._cancel_long_press()
        return super().on_touch_move(touch)

    def _cancel_long_press(self):
        if self._long_press_ev is not None:
            self._long_press_ev.cancel()
            self._long_press_ev = None

    def copy_to_clipboard(self, *args):
        self._long_press_ev = None
        if not self._raw_text:
            return
        try:
            Clipboard.copy(self._raw_text)
        except Exception as e:
            print(f"[AI Chat] clipboard error: {e}")
            return
        flash = _mix(self._bubble_bg, (1, 1, 1, 1), 0.25)
        self.bubble.md_bg_color = flash
        Animation(md_bg_color=self._bubble_bg, d=0.35).start(self.bubble)

    # -- публичный API ----------------------------------------------------
    def set_text(self, text):
        """Markdown перерисовывается пачками, иначе стриминг тормозит."""
        try:
            # Защита от некорректных данных
            if text is None:
                text = ""
            if not isinstance(text, str):
                text = str(text)

            self._raw_text = text
            if not self.markdown:
                try:
                    self.label.text = text
                    self._resize()
                except Exception as e:
                    print(f"[AI Chat] set_text label error: {e}")
                return

            self._pending_text = text
            if self._render_ev is None:
                self._render_ev = Clock.schedule_once(self._render_pending, 0.12)
        except Exception as e:
            print(f"[AI Chat] set_text error: {e}")

    def flush_text(self):
        if self._render_ev is not None:
            self._render_ev.cancel()
            self._render_ev = None
        self._render_pending()

    def get_text(self):
        return self._raw_text

    def _render_pending(self, *args):
        try:
            self._render_ev = None
            if self._pending_text is None:
                return
            text, self._pending_text = self._pending_text, None
            try:
                self.label.set_text(text)
                self._resize()
            except Exception as e:
                print(f"[AI Chat] _render_pending error: {e}")
        except Exception as e:
            print(f"[AI Chat] _render_pending wrapper error: {e}")
            self._render_ev = None

    # -- внутреннее -------------------------------------------------------
    def _resize(self, *args):
        try:
            if self.width <= 1:
                return
            ratio = MAX_MD_BUBBLE_RATIO if self.markdown else MAX_BUBBLE_RATIO
            max_w = max(dp(120), self.width * ratio)
            inner_w = max_w - dp(24)

            if isinstance(self.label, Label):
                try:
                    self.label.text_size = (inner_w, None)
                    self.label.texture_update()
                    text_w = min(inner_w, self.label.texture_size[0])
                    text_w = max(text_w, dp(60))
                    self.label.width = text_w
                    self.label.height = self.label.texture_size[1]
                    bubble_w = text_w + dp(24)
                except Exception as e:
                    print(f"[AI Chat] _resize Label error: {e}")
                    # Fallback размеры
                    self.label.width = inner_w
                    bubble_w = max_w
            else:
                try:
                    self.label.width = inner_w
                    bubble_w = max_w
                except Exception as e:
                    print(f"[AI Chat] _resize MarkdownLabel error: {e}")
                    bubble_w = max_w

            content_h = max(getattr(self.label, "height", 0) or 0, dp(20))
            try:
                self.bubble.width = bubble_w
                self.bubble.height = content_h + self.meta.height + dp(18)
                self.height = self.bubble.height
            except Exception as e:
                print(f"[AI Chat] _resize bubble error: {e}")
                # Fallback высота
                self.height = dp(60)
        except Exception as e:
            print(f"[AI Chat] _resize error: {e}")
            # Минимальная высота в случае ошибки
            try:
                self.height = dp(60)
            except:
                pass


class TypingRow(BoxLayout):
    """Анимированный индикатор «печатает…»."""

    def __init__(self, theme, **kwargs):
        try:
            super().__init__(orientation="horizontal", size_hint_y=None, height=dp(38), **kwargs)
        except Exception as e:
            print(f"[AI Chat] TypingRow super().__init__ error: {e}")
            if crash_log_error:
                try:
                    crash_log_error(f"TypingRow init error: {e}")
                except:
                    pass
            raise

            # Защита от некорректных данных темы
            safe_theme = theme if isinstance(theme, dict) else {}
            widget_bg = safe_theme.get("widget_bg", (0.16, 0.16, 0.20, 1))
            text_color = safe_theme.get("text_color", (0.93, 0.93, 0.96, 1))

            # Адаптивные размеры для Android
            bubble_width = dp(64)
            bubble_height = dp(34)
            if platform == 'android':
                # На Android используем немного большие размеры для надежности
                bubble_width = dp(72)
                bubble_height = dp(38)

            self.bubble = MDCard(
                size_hint=(None, None),
                size=(bubble_width, bubble_height),
                padding=dp(8),
                radius=[BUBBLE_RADIUS, BUBBLE_RADIUS, BUBBLE_RADIUS, BUBBLE_TAIL_RADIUS],
                md_bg_color=widget_bg,
                elevation=0,
            )

            # Используем AnchorLayout для правильного центрирования точек внутри пузыря
            from kivy.uix.anchorlayout import AnchorLayout

            bubble_content = AnchorLayout(
                size_hint=(1, 1),
                anchor_x='center',
                anchor_y='center'
            )

            # Используем более простые символы для Android 15
            # Unicode символы могут вызывать проблемы на некоторых версиях Android
            if platform == 'android':
                dot_char = "."  # Простая точка вместо Unicode
            else:
                dot_char = "•"  # Unicode точка для десктопа

            self.dots = Label(
                text=f"{dot_char}  {dot_char}  {dot_char}",
                color=_mix(text_color, (0.5, 0.5, 0.5, 1), 0.3),
                font_size=sp(18),
                markup=False,  # Отключаем markup для безопасности
                size_hint=(None, None),
                text_size=(None, None),
                halign='center',
                valign='middle'
            )

            # Добавляем точки в AnchorLayout, а затем в пузырь
            bubble_content.add_widget(self.dots)
            self.bubble.add_widget(bubble_content)

            self.add_widget(self.bubble)
            self.add_widget(Widget(size_hint_x=1))

            self._step = 0
            self._dot_char = dot_char
            self._ev = None
            self._running = False

            # Безопасный запуск анимации
            try:
                # На Android используем более длинный интервал для стабильности
                interval = 0.5 if platform == 'android' else 0.35
                self._ev = Clock.schedule_interval(self._tick, interval)
                self._running = True
            except Exception as e:
                print(f"[AI Chat] TypingRow animation start error: {e}")
                self._ev = None
                self._running = False

        except Exception as e:
            print(f"[AI Chat] TypingRow __init__ error: {e}")
            # Создаем минимальный виджет в случае ошибки
            self._ev = None
            self._running = False
            try:
                error_label = Label(text="...", font_size=sp(16))
                self.add_widget(error_label)
            except:
                pass

    def _tick(self, dt):
        try:
            if not self._running:
                return

            self._step = (self._step + 1) % 3

            # Безопасное обновление текста
            try:
                if hasattr(self, 'dots') and self.dots is not None:
                    dot_char = getattr(self, '_dot_char', '•')
                    self.dots.text = (f"{dot_char}  ", f"{dot_char}  {dot_char}  ", f"{dot_char}  {dot_char}  {dot_char}")[self._step]
            except Exception as e:
                print(f"[AI Chat] TypingRow text update error: {e}")
                # В случае ошибки останавливаем анимацию
                self.stop()

        except Exception as e:
            print(f"[AI Chat] TypingRow _tick error: {e}")
            self.stop()

    def stop(self):
        try:
            if self._ev:
                self._ev.cancel()
                self._ev = None
            self._running = False
        except Exception as e:
            print(f"[AI Chat] TypingRow stop error: {e}")
            self._ev = None
            self._running = False


class AiChatScreen(MDBoxLayout):
    """Экран чата. Прилипает к клавиатуре через свойство keyboard_height."""

    keyboard_height = NumericProperty(0)

    def __init__(self, agent, locale="ru", get_context_callback=None, **kwargs):
        super().__init__(**kwargs)
        self.agent = agent
        self.locale = locale
        self.get_context = get_context_callback or (lambda: "")
        self.modal = None
        self._is_generating = False
        self._current_row = None
        self._typing = None
        self._stick_to_bottom = True

        self._update_theme()

        self.orientation = "vertical"
        self.spacing = 0
        self.padding = 0
        self.md_bg_color = self.theme["popup_bg"]

        self._build_header()
        self._build_messages()
        self._build_composer()

        self.bind(keyboard_height=self._apply_keyboard_height)
        Clock.schedule_once(lambda dt: self._load_history(), 0.05)

    # ------------------------------------------------------------------ UI
    def _build_header(self):
        header = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(56),
            padding=[dp(16), 0, dp(8), 0],
            spacing=dp(8),
            md_bg_color=_mix(self.theme["popup_bg"], self.theme["widget_bg"], 0.6),
        )
        title = MDLabel(
            text="ИИ-тьютор" if self.locale == "ru" else "AI Tutor",
            font_style="H6",
            theme_text_color="Custom",
            text_color=self.theme["text_color"],
            shorten=True,
        )
        self.subtitle = MDLabel(
            text="онлайн" if self.locale == "ru" else "online",
            font_style="Caption",
            theme_text_color="Custom",
            size_hint_x=None,
            width=dp(90),
            halign="right",
            text_color=_mix(self.theme["text_color"], (0.5, 0.5, 0.5, 1), 0.4),
        )
        close_btn = MDIconButton(
            icon="close",
            theme_text_color="Custom",
            text_color=self.theme["text_color"],
            on_release=self.close_modal,
        )
        header.add_widget(title)
        header.add_widget(self.subtitle)
        header.add_widget(close_btn)
        self.add_widget(header)

    def _build_messages(self):
        holder = FloatLayout(size_hint_y=1)

        self.scroll = ScrollView(
            do_scroll_x=False,
            do_scroll_y=True,
            bar_width=dp(2),
            scroll_type=["bars", "content"],
            size_hint=(1, 1),
            pos_hint={"x": 0, "y": 0},
        )
        self.messages_box = BoxLayout(
            orientation="vertical",
            spacing=dp(8),
            size_hint_y=None,
            padding=[dp(12), dp(12), dp(12), dp(12)],
        )
        self.messages_box.bind(minimum_height=self.messages_box.setter("height"))
        self.messages_box.bind(height=lambda *_: self._maybe_autoscroll())
        self.scroll.bind(scroll_y=self._on_scroll)
        self.scroll.add_widget(self.messages_box)
        holder.add_widget(self.scroll)

        self.jump_btn = MDIconButton(
            icon="chevron-down",
            theme_text_color="Custom",
            text_color=self.theme["text_color"],
            md_bg_color=_mix(self.theme["widget_bg"], (0, 0, 0, 1), 0.15),
            icon_size=sp(16),
            size_hint=(None, None),
            size=(dp(28), dp(28)),
            pos_hint={"right": 0.99, "y": 0.01},
            opacity=0,
            disabled=True,
            on_release=lambda *_: self.scroll_to_bottom(force=True),
        )
        holder.add_widget(self.jump_btn)
        self.add_widget(holder)

    def _build_composer(self):
        self.composer = MDBoxLayout(
            orientation="vertical",
            size_hint_y=None,
            height=dp(96),
            padding=[dp(10), dp(6), dp(10), dp(8)],
            spacing=dp(6),
            md_bg_color=_mix(self.theme["popup_bg"], self.theme["widget_bg"], 0.45),
        )

        # Быстрые действия
        actions = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(32),
            spacing=dp(4),
        )
        for icon, action, tip in (
            ("delete-outline", "clear", "Очистить"),
            ("alert-circle-outline", "error", "Объяснить ошибку"),
            ("code-tags", "review", "Разбор кода"),
        ):
            actions.add_widget(
                MDIconButton(
                    icon=icon,
                    size_hint=(None, None),
                    size=(dp(32), dp(32)),
                    theme_text_color="Custom",
                    text_color=_mix(self.theme["text_color"], (0.5, 0.5, 0.5, 1), 0.3),
                    on_release=lambda _w, a=action: self._quick(a),
                )
            )
        actions.add_widget(Widget())
        self.composer.add_widget(actions)

        row = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=INPUT_MIN_HEIGHT,
            spacing=dp(8),
        )

        field = MDCard(
            size_hint=(1, None),
            height=INPUT_MIN_HEIGHT,
            radius=[dp(22)],
            md_bg_color=self.theme["widget_bg"],
            elevation=0,
            padding=[dp(6), dp(2), dp(6), dp(2)],
        )
        self.text_input = ChatTextInput(
            on_submit=self._send,
            hint_text="Сообщение…" if self.locale == "ru" else "Message…",
            multiline=True,
            size_hint_y=None,
            height=INPUT_MIN_HEIGHT - dp(4),
            foreground_color=self.theme["text_color"],
            hint_text_color=_mix(self.theme["text_color"], (0.5, 0.5, 0.5, 1), 0.5),
            background_color=(0, 0, 0, 0),
            cursor_color=self.theme.get("run_btn_bg", (0.6, 0.5, 1, 1)),
            padding=[dp(10), dp(10), dp(10), dp(10)],
            font_size=sp(15),
            input_type="text",
            use_bubble=True,
            use_handles=True,
            selection_color=(0.3, 0.6, 1.0, 0.35),
        )
        self.text_input.bind(minimum_height=lambda *_: self._grow_input())
        self.text_input.bind(text=lambda *_: self._grow_input())
        field.add_widget(self.text_input)
        self.field = field

        self.send_btn = MDIconButton(
            icon="send",
            size_hint=(None, None),
            size=(dp(44), dp(44)),
            icon_size=sp(20),
            theme_text_color="Custom",
            text_color=(1, 1, 1, 1),
            md_bg_color=self.theme.get("run_btn_bg", (0.596, 0.486, 1.0, 1)),
            on_release=self._on_send_pressed,
        )

        send_holder = AnchorLayout(
            anchor_y="bottom",
            anchor_x="center",
            size_hint=(None, 1),
            width=dp(44),
        )
        send_holder.add_widget(self.send_btn)

        row.add_widget(field)
        row.add_widget(send_holder)
        self.input_row = row
        self.composer.add_widget(row)
        self.add_widget(self.composer)

    # ------------------------------------------------------- клавиатура
    def _apply_keyboard_height(self, *args):
        """Поднимает чат ровно на высоту клавиатуры (впритык, без зазора)."""
        try:
            # Защита от некорректных значений
            safe_height = max(0, float(self.keyboard_height or 0))
            # Ограничиваем максимальную высоту для безопасности на Android
            if platform == 'android':
                safe_height = min(safe_height, Window.height * 0.7)  # Не более 70% высоты экрана

            self.padding = [0, 0, 0, safe_height]
            Clock.schedule_once(lambda dt: self.scroll_to_bottom(force=True), 0)
        except Exception as e:
            print(f"[AI Chat] _apply_keyboard_height error: {e}")
            # В случае ошибки сбрасываем padding
            self.padding = [0, 0, 0, 0]

    def set_keyboard_height(self, height, animated=True):
        try:
            # Безопасное преобразование высоты
            safe_height = max(0, float(height or 0))

            # Дополнительная защита на Android
            if platform == 'android':
                # Ограничиваем максимальную высоту
                safe_height = min(safe_height, Window.height * 0.7)
                # Фильтруем слишком маленькие изменения (шум)
                if abs(safe_height - self.keyboard_height) < dp(2) and self.keyboard_height > 0:
                    return

            Animation.cancel_all(self, "keyboard_height")
            if animated and abs(safe_height - self.keyboard_height) > dp(1):
                Animation(keyboard_height=safe_height, d=0.16, t="out_quad").start(self)
            else:
                self.keyboard_height = safe_height
        except Exception as e:
            print(f"[AI Chat] set_keyboard_height error: {e}")
            # В случае ошибки оставляем текущее значение

    # ------------------------------------------------------------ скролл
    def _on_scroll(self, *args):
        if self.messages_box.height <= self.scroll.height:
            self._stick_to_bottom = True
        else:
            self._stick_to_bottom = self.scroll.scroll_y <= 0.02
        self._update_jump_btn()

    def _update_jump_btn(self):
        visible = not self._stick_to_bottom
        self.jump_btn.disabled = not visible
        Animation.cancel_all(self.jump_btn, "opacity")
        Animation(opacity=1 if visible else 0, d=0.15).start(self.jump_btn)

    def _maybe_autoscroll(self):
        if self._stick_to_bottom:
            self.scroll_to_bottom()

    def scroll_to_bottom(self, force=False, animated=True):
        try:
            if not force and not self._stick_to_bottom:
                return

            def _do(dt):
                try:
                    self._stick_to_bottom = True
                    if hasattr(self, 'scroll') and self.scroll is not None:
                        Animation.cancel_all(self.scroll, "scroll_y")
                        if animated:
                            Animation(scroll_y=0, d=0.18, t="out_quad").start(self.scroll)
                        else:
                            self.scroll.scroll_y = 0
                    self._update_jump_btn()
                except Exception as e:
                    print(f"[AI Chat] scroll_to_bottom _do error: {e}")

            Clock.schedule_once(_do, 0)
        except Exception as e:
            print(f"[AI Chat] scroll_to_bottom error: {e}")

    # ------------------------------------------------------------- ввод
    def _grow_input(self):
        try:
            # Защита от некорректных значений minimum_height
            min_h = getattr(self.text_input, 'minimum_height', INPUT_MIN_HEIGHT) or INPUT_MIN_HEIGHT
            needed = min_h + dp(4)

            # Ограничиваем высоту для безопасности
            height = max(INPUT_MIN_HEIGHT, min(INPUT_MAX_HEIGHT, needed))

            # Дополнительная защита на Android от слишком больших значений
            if platform == 'android':
                max_safe_height = Window.height * 0.4  # Не более 40% высоты экрана
                height = min(height, max_safe_height)

            self.text_input.height = max(dp(20), height - dp(4))  # Минимальная защита
            self.field.height = height
            self.input_row.height = height
            self.composer.height = height + dp(32) + dp(20)
        except Exception as e:
            print(f"[AI Chat] _grow_input error: {e}")
            # В случае ошибки устанавливаем безопасные значения по умолчанию
            try:
                self.text_input.height = INPUT_MIN_HEIGHT - dp(4)
                self.field.height = INPUT_MIN_HEIGHT
                self.input_row.height = INPUT_MIN_HEIGHT
                self.composer.height = INPUT_MIN_HEIGHT + dp(32) + dp(20)
            except:
                pass

    def _on_send_pressed(self, *args):
        if self._is_generating:
            self._stop_generation()
        else:
            self._send()

    def _set_generating(self, value):
        self._is_generating = value
        self.send_btn.icon = "stop" if value else "send"
        self.send_btn.md_bg_color = (
            self.theme.get("btn_danger_bg", (0.85, 0.3, 0.35, 1))
            if value
            else self.theme.get("run_btn_bg", (0.596, 0.486, 1.0, 1))
        )
        self.subtitle.text = (
            ("печатает…" if self.locale == "ru" else "typing…")
            if value
            else ("онлайн" if self.locale == "ru" else "online")
        )

    # --------------------------------------------------------- сообщения
    def _add_row(self, text, side, markdown=False):
        try:
            # Защита от некорректных данных
            if text is None:
                text = ""
            if not isinstance(text, str):
                text = str(text)

            row = MessageRow(self.theme, text, side=side, markdown=markdown)
            self.messages_box.add_widget(row)
            self.scroll_to_bottom()
            return row
        except Exception as e:
            print(f"[AI Chat] _add_row error: {e}")
            # Возвращаем None в случае ошибки
            return None

    def _add_user(self, text):
        try:
            self._update_theme()
            return self._add_row(text, side="right")
        except Exception as e:
            print(f"[AI Chat] _add_user error: {e}")
            return None

    def _add_bot(self, text):
        try:
            self._update_theme()
            return self._add_row(text, side="left", markdown=True)
        except Exception as e:
            print(f"[AI Chat] _add_bot error: {e}")
            return None

    def _show_typing(self):
        try:
            if self._typing:
                return

            # Проверяем, что messages_box доступен
            if not hasattr(self, 'messages_box') or self.messages_box is None:
                print("[AI Chat] messages_box not available for typing indicator")
                return

            # Создаем индикатор с защитой от ошибок
            try:
                self._typing = TypingRow(self.theme)
                self.messages_box.add_widget(self._typing)
                # Скроллим вниз с защитой
                try:
                    self.scroll_to_bottom()
                except Exception as scroll_error:
                    print(f"[AI Chat] Scroll to bottom error in _show_typing: {scroll_error}")
            except Exception as e:
                print(f"[AI Chat] TypingRow creation error: {e}")
                self._typing = None

        except Exception as e:
            print(f"[AI Chat] _show_typing error: {e}")
            self._typing = None

    def _hide_typing(self):
        try:
            if self._typing:
                # Сначала останавливаем анимацию
                try:
                    self._typing.stop()
                except Exception as stop_error:
                    print(f"[AI Chat] TypingRow stop error: {stop_error}")

                # Затем удаляем виджет
                if hasattr(self, 'messages_box') and self.messages_box is not None:
                    try:
                        self.messages_box.remove_widget(self._typing)
                    except Exception as remove_error:
                        print(f"[AI Chat] TypingRow remove error: {remove_error}")

                self._typing = None
        except Exception as e:
            print(f"[AI Chat] _hide_typing error: {e}")
            self._typing = None

    def _load_history(self):
        try:
            history = []
            try:
                if hasattr(self, 'agent') and self.agent is not None and hasattr(self.agent, '_lock'):
                    with self.agent._lock:
                        history = self.agent.history.copy() if hasattr(self.agent, 'history') else []
            except Exception as e:
                print(f"[AI Chat] Error loading history: {e}")
                history = []

            if not history:
                self._add_bot(
                    "Привет! Я ИИ-тьютор по Python. Задавай вопросы о коде, ошибках или уроках!"
                    if self.locale == "ru"
                    else "Hi! I'm an AI Python tutor. Ask about code, errors or lessons!"
                )
            else:
                for msg in history:
                    try:
                        if isinstance(msg, dict):
                            if msg.get("role") == "user":
                                self._add_user(msg.get("content", ""))
                            elif msg.get("role") == "assistant":
                                self._add_bot(msg.get("content", ""))
                    except Exception as e:
                        print(f"[AI Chat] Error processing history message: {e}")

            self.scroll_to_bottom(force=True, animated=False)
        except Exception as e:
            print(f"[AI Chat] _load_history error: {e}")
            # Показываем приветствие в случае ошибки
            try:
                self._add_bot(
                    "Привет! Я ИИ-тьютор по Python. Задавай вопросы о коде, ошибках или уроках!"
                    if self.locale == "ru"
                    else "Hi! I'm an AI Python tutor. Ask about code, errors or lessons!"
                )
            except:
                pass

    # -------------------------------------------------------------- тема
    def _update_theme(self):
        try:
            if ThemeManager:
                theme = ThemeManager.get_theme()
                self.theme = LIGHT_THEME if theme and theme.get("name") == "light" else DARK_THEME
            else:
                self.theme = DARK_THEME
        except Exception:
            self.theme = DARK_THEME

    def close_modal(self, *args):
        if self.modal:
            self.modal.dismiss()

    def copy_last_answer(self, *args):
        for child in self.messages_box.children:
            if isinstance(child, MessageRow) and child.side == "left":
                Clipboard.copy(child.get_text())
                return

    # ------------------------------------------------------------ логика
    def _send(self, *args):
        try:
            # Безопасное получение текста на Android
            if not hasattr(self, 'text_input') or self.text_input is None:
                print("[AI Chat] text_input not available")
                return

            text = ""
            try:
                text = self.text_input.text.strip() if self.text_input.text else ""
            except Exception as e:
                print(f"[AI Chat] Error reading text_input: {e}")
                return

            if not text or self._is_generating:
                return

            # Безопасная очистка поля ввода
            try:
                self.text_input.text = ""
                self._grow_input()
            except Exception as e:
                print(f"[AI Chat] Error clearing text_input: {e}")

            # Безопасное добавление сообщения пользователя
            try:
                self._add_user(text)
            except Exception as e:
                print(f"[AI Chat] Error adding user message: {e}")
                return

            self._set_generating(True)
            self._show_typing()

            def stream_callback(chunk):
                try:
                    if not self._is_generating:
                        return

                    # Защита от некорректных данных
                    if chunk is None:
                        chunk = ""
                    if not isinstance(chunk, str):
                        chunk = str(chunk)

                    def apply(dt):
                        try:
                            if not self._is_generating:
                                return
                            self._hide_typing()
                            if self._current_row is None:
                                self._current_row = self._add_bot(chunk)
                            else:
                                current_text = self._current_row.get_text() or ""
                                self._current_row.set_text(current_text + chunk)
                            self.scroll_to_bottom()
                        except Exception as e:
                            print(f"[AI Chat] Stream apply error: {e}")
                            # В случае ошибки останавливаем генерацию
                            self._set_generating(False)
                            self._current_row = None

                    Clock.schedule_once(apply, 0)
                except Exception as e:
                    print(f"[AI Chat] Stream callback error: {e}")

            def ok(answer):
                def apply(dt):
                    try:
                        self._hide_typing()
                        if self._current_row is None:
                            self._add_bot(answer)
                        else:
                            self._current_row.set_text(answer)
                            self._current_row.flush_text()
                        self._current_row = None
                        self._set_generating(False)
                        self.scroll_to_bottom()
                    except Exception as e:
                        print(f"[AI Chat] OK callback error: {e}")
                        self._current_row = None
                        self._set_generating(False)

                Clock.schedule_once(apply, 0)

            def err(e):
                def apply(dt):
                    try:
                        self._hide_typing()
                        self._current_row = None
                        self._set_generating(False)
                        error_msg = f"⚠️ Ошибка: {e}" if e else "⚠️ Неизвестная ошибка"
                        self._add_bot(error_msg)
                    except Exception as e2:
                        print(f"[AI Chat] Error callback error: {e2}")
                        self._current_row = None
                        self._set_generating(False)

                Clock.schedule_once(apply, 0)

            # Безопасный вызов агента
            try:
                if not hasattr(self, 'agent') or self.agent is None:
                    raise Exception("Agent not available")

                context = ""
                try:
                    context = self.get_context() if self.get_context else ""
                except Exception as e:
                    print(f"[AI Chat] Error getting context: {e}")
                    context = ""

                self.agent.ask(
                    text,
                    context=context,
                    locale=self.locale,
                    on_success=ok,
                    on_error=err,
                    stream=True,
                    stream_callback=stream_callback,
                )
            except Exception as e:
                print(f"[AI Chat] Agent.ask error: {e}")
                # В случае ошибки с агентом сразу показываем ошибку
                err(e)

        except Exception as e:
            print(f"[AI Chat] _send error: {e}")
            # Логируем ошибку в файл крашей
            if crash_log_error:
                try:
                    crash_log_error(f"AI Chat send error: {e}", {
                        'text_length': len(text) if 'text' in locals() else 0,
                        'is_generating': self._is_generating,
                        'locale': self.locale
                    })
                except:
                    pass
            self._set_generating(False)
            self._current_row = None
            try:
                self._hide_typing()
            except:
                pass

    def _stop_generation(self, *args):
        try:
            if not self._is_generating:
                return
            self._set_generating(False)
            self._hide_typing()
            try:
                if hasattr(self, 'agent') and self.agent is not None:
                    self.agent.stop_generation()
            except Exception as e:
                print(f"[AI Chat] stop_generation error: {e}")
            self._current_row = None
        except Exception as e:
            print(f"[AI Chat] _stop_generation error: {e}")
            self._current_row = None
            self._set_generating(False)

    def _quick(self, action):
        try:
            if action == "clear":
                try:
                    if hasattr(self, 'agent') and self.agent is not None:
                        self.agent.clear_history()
                    self.messages_box.clear_widgets()
                    self._typing = None
                    if hasattr(self, 'text_input') and self.text_input is not None:
                        self.text_input.text = ""
                        self._grow_input()
                    self._add_bot("Чат очищен." if self.locale == "ru" else "Chat cleared.")
                except Exception as e:
                    print(f"[AI Chat] Clear action error: {e}")
                return

            context = ""
            try:
                context = self.get_context() if self.get_context else ""
            except Exception as e:
                print(f"[AI Chat] Error getting context in _quick: {e}")
                context = ""

            self._show_typing()
            self._set_generating(True)

            def ok(answer):
                def apply(dt):
                    try:
                        self._hide_typing()
                        self._set_generating(False)
                        self._add_bot(answer)
                    except Exception as e:
                        print(f"[AI Chat] Quick OK callback error: {e}")
                        self._set_generating(False)

                Clock.schedule_once(apply, 0)

            def err(e):
                def apply(dt):
                    try:
                        self._hide_typing()
                        self._set_generating(False)
                        error_msg = f"⚠️ Ошибка: {e}" if e else "⚠️ Неизвестная ошибка"
                        self._add_bot(error_msg)
                    except Exception as e2:
                        print(f"[AI Chat] Quick error callback error: {e2}")
                        self._set_generating(False)

                Clock.schedule_once(apply, 0)

            try:
                if action == "error":
                    if hasattr(self, 'agent') and self.agent is not None:
                        self.agent.explain_error(
                            "Последняя ошибка выполнения (если была)",
                            code=context,
                            locale=self.locale,
                            on_success=ok,
                            on_error=err,
                        )
                    else:
                        err("Agent not available")
                elif action == "review":
                    if not context or not context.strip():
                        self._hide_typing()
                        self._set_generating(False)
                        self._add_bot(
                            "Нет кода для проверки." if self.locale == "ru" else "No code to check."
                        )
                        return
                    if hasattr(self, 'agent') and self.agent is not None:
                        self.agent.review_code(context, locale=self.locale, on_success=ok, on_error=err)
                    else:
                        err("Agent not available")
            except Exception as e:
                print(f"[AI Chat] Quick action error: {e}")
                err(e)

        except Exception as e:
            print(f"[AI Chat] _quick error: {e}")
            self._set_generating(False)
            try:
                self._hide_typing()
            except:
                pass


def open_ai_chat(agent, locale="ru", get_context_callback=None):
    """Открывает чат на весь экран; контент прижимается к клавиатуре."""
    chat_screen = AiChatScreen(agent, locale=locale, get_context_callback=get_context_callback)
    chat_screen.name = "ai_chat_screen"

    try:
        if ThemeManager:
            theme = ThemeManager.get_theme()
            bg_color = theme.get("window_bg", (0.08, 0.08, 0.11, 1))
        else:
            bg_color = (0.08, 0.08, 0.11, 1)
    except Exception:
        bg_color = (0.08, 0.08, 0.11, 1)

    modal = ModalView(
        size_hint=(1, 1),
        background_color=bg_color,
        auto_dismiss=False,
        padding=0,
    )
    chat_screen.modal = modal

    # Безопасная работа с клавиатурой на Android
    previous_softinput = None
    keyboard_bound = False

    try:
        if platform == 'android':
            # Сохраняем текущий режим только если он отличается
            previous_softinput = Window.softinput_mode
            # На Android 15 нужно быть осторожным с softinput_mode
            # Используем 'below_target' вместо '' для совместимости
            if previous_softinput != 'below_target':
                Window.softinput_mode = 'below_target'

        def on_keyboard_height(_window, height):
            try:
                # Безопасно обрабатываем изменения высоты клавиатуры
                if height is not None:
                    chat_screen.set_keyboard_height(height)
            except Exception as e:
                print(f"[AI Chat] keyboard_height error: {e}")

        # Привязываем обработчик только если платформа поддерживает keyboard_height
        if hasattr(Window, 'keyboard_height'):
            try:
                Window.bind(keyboard_height=on_keyboard_height)
                keyboard_bound = True
                # Устанавливаем начальную высоту с защитой от ошибок
                initial_height = getattr(Window, 'keyboard_height', 0) or 0
                chat_screen.set_keyboard_height(initial_height, animated=False)
            except Exception as e:
                print(f"[AI Chat] Failed to bind keyboard_height: {e}")
                keyboard_bound = False

    except Exception as e:
        print(f"[AI Chat] Keyboard setup error: {e}")
        previous_softinput = None
        keyboard_bound = False

    modal.add_widget(chat_screen)
    modal.open()

    def on_dismiss(_instance):
        try:
            # Безопасно отвязываем обработчик
            if keyboard_bound:
                try:
                    Window.unbind(keyboard_height=on_keyboard_height)
                except Exception as e:
                    print(f"[AI Chat] Unbind keyboard_height error: {e}")

            # Безопасно восстанавливаем режим клавиатуры
            if platform == 'android' and previous_softinput is not None:
                try:
                    # Восстанавливаем только если значение действительно отличается
                    if Window.softinput_mode != previous_softinput:
                        Window.softinput_mode = previous_softinput
                except Exception as e:
                    print(f"[AI Chat] Restore softinput_mode error: {e}")

            chat_screen._hide_typing()
        except Exception as e:
            print(f"[AI Chat] Dismiss error: {e}")

    modal.bind(on_dismiss=on_dismiss)
    return modal

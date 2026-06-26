"""
Python Learning IDE
Версия: 1.0.0

Полноценная среда разработки Python для Android с богатым функционалом:

=== ОСНОВНЫЕ ВОЗМОЖНОСТИ ===
✓ Редактор кода с подсветкой синтаксиса (Pygments)
✓ Автодополнение кода и список ключевых слов Python
✓ Нумерация строк и направляющие отступов
✓ Множество вкладок для работы с несколькими файлами
✓ Поддержка светлой и тёмной тем оформления
✓ Русский и английский языки интерфейса
✓ Адаптивный UI под разные размеры экранов

=== РАБОТА С ФАЙЛАМИ ===
✓ Файловый менеджер с поддержкой сортировки
✓ Открытие, сохранение, переименование, удаление файлов
✓ Поддержка多种 кодировок (UTF-8, CP1251, Latin-1 и др.)
✓ Асинхронная загрузка/сохранение (UI не блокируется)
✓ Автосохранение и восстановление вкладок

=== РЕДАКТОР И КОД ===
✓ Форматирование кода через autopep8
✓ Поиск и замена текста
✓ Переход к строке
✓ Undo/Redo (отмена/повтор действий)
✓ Копировать/Вырезать/Вставить
✓ Выделить весь код
✓ Очистка всего кода с подтверждением
✓ Видимая табуляция (4 пробела)

=== ВЫПОЛНЕНИЕ КОДА ===
✓ Запуск Python-кода прямо в приложении
✓ Обработка пользовательского ввода (input())
✓ Отображение результата в отдельном окне
✓ Защита от повторного запуска
✓ Обрезание слишком длинного вывода

=== AI АССИСТЕНТ ===
✓ Интеграция с Google Gemini API
✓ Помощь в написании кода
✓ Ответы на вопросы по Python

=== ПРОЧЕЕ ===
✓ Анимированная заставка при запуске
✓ Вибрация при нажатии на кнопки
✓ Выбор шрифта для редактора (JetBrains Mono, Fira Code и др.)
✓ Выбор стиля подсветки синтаксиса (Monokai, Dracula и др.)
✓ Копирование результатов в буфер обмена
✓ История выполнения кода
✓ Полная поддержка Android (через jnius и androidstorage)

=== ИСПРАВЛЕНИЯ И ОПТИМИЗАЦИЯ ===
✓ Прогрев Pygments при старте (нет первого фриза)
✓ Плавный набор текста в редакторе
✓ Оптимизированная работа с большими файлами
✓ Устранены микро-фризы
✓ Исправлено дёрганье клавиатуры
✓ Удалён мусор из кода (refactoring)

Версия 1.0.0 — первый стабильный релиз

"""
# main.py - упрощённая версия

"""
Python Learning IDE
Точка входа в приложение
"""
import sys
import traceback
from kivy.config import Config
from kivy.core.window import Window
from kivy.utils import platform
from kivy.clock import Clock
from utils.android_utils import patched_excepthook

# ====================== НАСТРОЙКИ KIVY ======================
Config.set('graphics', 'maxfps', '30')
Config.set('kivy', 'window_icon', '')
Config.set('kivy', 'window_title', 'Python Learning IDE')
Config.set('kivy', 'exit_on_escape', '0')
Config.set('kivy', 'keyboard_mode', 'system')
Window.softinput_mode = 'below_target'
Window.keyboard_anim_args = {'d': 0, 't': 'linear'}

# Устанавливаем обработчик ошибок
sys.excepthook = patched_excepthook


def main():
    """Запуск приложения"""
    try:
        from app import PythonLearningApp
        app = PythonLearningApp()
        app.run()
    except Exception as e:
        error_msg = f"FATAL ERROR: {e}\n\nTraceback:\n{traceback.format_exc()}"
        print(error_msg)

        # Сохраняем лог на Android
        if platform == 'android':
            try:
                with open('/storage/emulated/0/Download/app_error.log', 'w', encoding='utf-8') as f:
                    f.write(error_msg)
            except:
                pass
        raise


if __name__ == '__main__':
    main()
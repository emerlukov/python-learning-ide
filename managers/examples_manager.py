# managers/examples_manager.py
"""
Manager for loading and managing code examples from JSON file
"""
import os
import json
import threading
from kivy.clock import Clock
from utils.debug_utils import log_error


class ExamplesManager:
    """Управляет загрузкой и кэшированием примеров кода"""

    _instance = None
    _loading = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self._examples_path = os.path.join(os.getcwd(), 'data', 'examples.json')
        self._examples = None
        self._observers = []

        # Маппинг между локализованными названиями и ключами в JSON
        self._title_mapping = {
            # Русские названия
            '1. Hello World': '1. Hello World',
            '2. Переменные': '2. Переменные',
            '3. Ввод': '3. Ввод данных',
            '3. Ввод данных': '3. Ввод данных',
            '4. Условия': '4. Условия',
            '5. Цикл For': '5. Цикл For',
            '6. Цикл While': '6. Цикл While',
            '7. Списки': '7. Списки',
            '8. Генераторы списков': '8. Генераторы списков',
            '9. Словари': '9. Словари',
            '10. Функции': '10. Функции',
            '11. Lambda': '11. Lambda',
            '12. Классы': '12. Классы',
            '13. Наследование': '13. Наследование',
            '14. Ошибки': '14. Ошибки',
            '15. Файлы': '15. Файлы',
            '16. Рекурсия': '16. Рекурсия',
            '17. Генераторы': '17. Генераторы',
            '18. Декораторы': '18. Декораторы',

            # Английские названия
            '1. Hello World': '1. Hello World',
            '2. Variables': '2. Переменные',
            '3. Input': '3. Ввод данных',
            '4. Conditions': '4. Условия',
            '5. For Loop': '5. Цикл For',
            '6. While Loop': '6. Цикл While',
            '7. Lists': '7. Списки',
            '8. List Comprehensions': '8. Генераторы списков',
            '9. Dictionaries': '9. Словари',
            '10. Functions': '10. Функции',
            '11. Lambda': '11. Lambda',
            '12. Classes': '12. Классы',
            '13. Inheritance': '13. Наследование',
            '14. Errors': '14. Ошибки',
            '15. Files': '15. Файлы',
            '16. Recursion': '16. Рекурсия',
            '17. Generators': '17. Генераторы',
            '18. Decorators': '18. Декораторы',

            # ========== НОВЫЕ ПРИМЕРЫ 19-25 ==========

            # Русские названия (19-25)
            '19. Работа с датами': '19. Работа с датами',
            '20. Регулярные выражения': '20. Регулярные выражения',
            '21. Модуль random': '21. Модуль random',
            '22. Работа с JSON': '22. Работа с JSON',
            '23. Модуль os': '23. Модуль os',
            '24. Map, Filter, Reduce': '24. Map, Filter, Reduce',
            '25. Контекстные менеджеры': '25. Контекстные менеджеры',

            # Английские названия (19-25)
            '19. Dates and Time': '19. Работа с датами',
            '20. Regular Expressions': '20. Регулярные выражения',
            '21. Random module': '21. Модуль random',
            '22. Working with JSON': '22. Работа с JSON',
            '23. OS module': '23. Модуль os',
            '24. Map, Filter, Reduce': '24. Map, Filter, Reduce',
            '25. Context Managers': '25. Контекстные менеджеры',
        }

    def load_examples_async(self, callback=None, force_reload=False):
        """Асинхронно загружает примеры из JSON"""
        if self._loading:
            if callback:
                callback(None)
            return

        if force_reload:
            self._examples = None

        if self._examples is not None:
            if callback:
                callback(self._examples)
            return

        def load():
            self._loading = True
            try:
                if os.path.exists(self._examples_path):
                    with open(self._examples_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        self._examples = data.get('examples', {})
                        print(f"[ExamplesManager] Loaded {len(self._examples)} examples")
                        print(f"[ExamplesManager] Keys: {list(self._examples.keys())}")
                else:
                    print(f"[ExamplesManager] Examples file not found: {self._examples_path}")
                    self._examples = self._get_fallback_examples()

                Clock.schedule_once(lambda dt: self._notify_observers(), 0)

                if callback:
                    Clock.schedule_once(lambda dt: callback(self._examples), 0)

            except Exception as e:
                log_error(f"Error loading examples: {e}")
                self._examples = self._get_fallback_examples()
                if callback:
                    Clock.schedule_once(lambda dt: callback(self._examples), 0)
            finally:
                self._loading = False

        threading.Thread(target=load, daemon=True).start()

    def get_example(self, display_title, language='ru'):
        """
        Возвращает пример по отображаемому названию и языку

        Args:
            display_title: Название из спиннера (может быть на русском или английском)
            language: Текущий язык ('ru' или 'en')
        """
        if self._examples is None:
            self.load_examples_async()
            return "# Загрузка примеров...\n# Loading examples..."

        # Получаем ключ для JSON по отображаемому названию
        json_key = self._title_mapping.get(display_title)

        if not json_key:
            print(f"[ExamplesManager] No mapping found for: {display_title}")
            # Пробуем использовать как есть
            json_key = display_title

        print(f"[ExamplesManager] Looking for: {display_title} -> {json_key}")

        example_data = self._examples.get(json_key, {})

        if isinstance(example_data, dict):
            # Пробуем получить на нужном языке
            code = example_data.get(language)
            if code:
                return code
            # Если нет — пробуем английский
            code = example_data.get('en')
            if code:
                return code
            # Если нет — берём первый попавшийся
            for lang, text in example_data.items():
                if isinstance(text, str):
                    return text

        print(f"[ExamplesManager] Example not found for key: {json_key}")
        return f"# Example '{display_title}' not found"

    def get_titles(self):
        """Возвращает список отображаемых названий примеров"""
        # Возвращаем русские названия как основу
        russian_titles = [
            '1. Hello World',
            '2. Переменные',
            '3. Ввод данных',
            '4. Условия',
            '5. Цикл For',
            '6. Цикл While',
            '7. Списки',
            '8. Генераторы списков',
            '9. Словари',
            '10. Функции',
            '11. Lambda',
            '12. Классы',
            '13. Наследование',
            '14. Ошибки',
            '15. Файлы',
            '16. Рекурсия',
            '17. Генераторы',
            '18. Декораторы',
            '19. Работа с датами',
            '20. Регулярные выражения',
            '21. Модуль random',
            '22. Работа с JSON',
            '23. Модуль os',
            '24. Map, Filter, Reduce',
            '25. Контекстные менеджеры',
        ]
        return russian_titles

    def get_localized_titles(self, language='ru'):
        """Возвращает локализованные названия примеров для спиннера"""
        if language == 'ru':
            return [
                '1. Hello World',
                '2. Переменные',
                '3. Ввод данных',
                '4. Условия',
                '5. Цикл For',
                '6. Цикл While',
                '7. Списки',
                '8. Генераторы списков',
                '9. Словари',
                '10. Функции',
                '11. Lambda',
                '12. Классы',
                '13. Наследование',
                '14. Ошибки',
                '15. Файлы',
                '16. Рекурсия',
                '17. Генераторы',
                '18. Декораторы',
                '19. Работа с датами',
                '20. Регулярные выражения',
                '21. Модуль random',
                '22. Работа с JSON',
                '23. Модуль os',
                '24. Map, Filter, Reduce',
                '25. Контекстные менеджеры',
            ]
        else:
            return [
                '1. Hello World',
                '2. Variables',
                '3. Input',
                '4. Conditions',
                '5. For Loop',
                '6. While Loop',
                '7. Lists',
                '8. List Comprehensions',
                '9. Dictionaries',
                '10. Functions',
                '11. Lambda',
                '12. Classes',
                '13. Inheritance',
                '14. Errors',
                '15. Files',
                '16. Recursion',
                '17. Generators',
                '18. Decorators',
                '19. Dates and Time',
                '20. Regular Expressions',
                '21. Random module',
                '22. Working with JSON',
                '23. OS module',
                '24. Map, Filter, Reduce',
                '25. Context Managers',
            ]

    def reload(self):
        """Принудительная перезагрузка примеров"""
        self._examples = None
        self.load_examples_async(force_reload=True)

    def register_observer(self, observer):
        """Регистрирует наблюдателя для обновлений"""
        if observer not in self._observers:
            self._observers.append(observer)

    def unregister_observer(self, observer):
        """Удаляет наблюдателя"""
        if observer in self._observers:
            self._observers.remove(observer)

    def _notify_observers(self):
        """Уведомляет наблюдателей о загрузке примеров"""
        for observer in self._observers:
            if hasattr(observer, 'on_examples_loaded'):
                try:
                    observer.on_examples_loaded(self._examples)
                except Exception as e:
                    log_error(f"Error notifying observer: {e}")

    def _get_fallback_examples(self):
        """Возвращает встроенные примеры на случай, если JSON не загрузился"""
        return {
            '1. Hello World': {
                'ru': 'print("Привет, мир!")',
                'en': 'print("Hello, World!")'
            },
            '2. Переменные': {
                'ru': 'name = "Алиса"\nprint(name)',
                'en': 'name = "Alice"\nprint(name)'
            },
            '3. Ввод данных': {
                'ru': 'name = input("Как тебя зовут? ")\nprint("Привет,", name)',
                'en': 'name = input("What is your name? ")\nprint("Hello,", name)'
            }
        }


# Глобальный экземпляр
examples_manager = ExamplesManager()
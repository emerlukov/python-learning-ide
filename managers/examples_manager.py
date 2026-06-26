# managers/examples_manager.py
"""
Manager for loading and managing code examples from JSON file
"""
import os
import json
import threading
from kivy.clock import Clock
from utils.debug_utils import log_error
from utils.paths import bundled_data_path


class ExamplesManager:
    """Управляет загрузкой и кэшированием примеров кода"""

    _instance = None
    _loading = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self._examples = None
        self._observers = []

        # Маппинг между локализованными названиями и ключами в JSON
        self._title_mapping = {
            # ===== РУССКИЕ НАЗВАНИЯ (20 уроков) =====
            '1. Введение в написание программ': '1. Введение в написание программ',
            '2. Переменные и типы данных': '2. Переменные и типы данных',
            '3. Консольный ввод и вывод': '3. Консольный ввод и вывод',
            '4. Арифметические операции с числами': '4. Арифметические операции с числами',
            '5. Условные выражения': '5. Условные выражения',
            '6. Операции со строками': '6. Операции со строками',
            '7. Условная конструкция if': '7. Условная конструкция if',
            '8. Циклы for и while': '8. Циклы for и while',
            '9. Функции': '9. Функции',
            '10. Параметры функций': '10. Параметры функций',
            '11. Оператор return': '11. Оператор return',
            '12. Функция как тип': '12. Функция как тип',
            '13. Лямбда-выражения': '13. Лямбда-выражения',
            '14. Преобразование типов': '14. Преобразование типов',
            '15. Область видимости': '15. Область видимости',
            '16. Замыкания': '16. Замыкания',
            '17. Декораторы': '17. Декораторы',
            '18. Основы Python': '18. Основы Python',
            '19. Функции и декораторы': '19. Функции и декораторы',
            '20. Консольный банк': '20. Консольный банк',

            # ===== АНГЛИЙСКИЕ НАЗВАНИЯ (20 уроков) =====
            '1. Introduction to Programming': '1. Введение в написание программ',
            '2. Variables and Data Types': '2. Переменные и типы данных',
            '3. Console Input and Output': '3. Консольный ввод и вывод',
            '4. Arithmetic Operations': '4. Арифметические операции с числами',
            '5. Conditional Expressions': '5. Условные выражения',
            '6. String Operations': '6. Операции со строками',
            '7. The if Statement': '7. Условная конструкция if',
            '8. For and While Loops': '8. Циклы for и while',
            '9. Functions': '9. Функции',
            '10. Function Parameters': '10. Параметры функций',
            '11. The return Operator': '11. Оператор return',
            '12. Function as a Type': '12. Функция как тип',
            '13. Lambda Expressions': '13. Лямбда-выражения',
            '14. Type Conversion': '14. Преобразование типов',
            '15. Variable Scope': '15. Область видимости',
            '16. Closures': '16. Замыкания',
            '17. Decorators': '17. Декораторы',
            '18. Python Basics': '18. Основы Python',
            '19. Functions and Decorators': '19. Функции и декораторы',
            '20. Console Bank': '20. Консольный банк',
        }

    @property
    def _examples_path(self):
        return bundled_data_path('examples.json')

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
        '1. Введение в написание программ',
        '2. Переменные и типы данных',
        '3. Консольный ввод и вывод',
        '4. Арифметические операции с числами',
        '5. Условные выражения',
        '6. Операции со строками',
        '7. Условная конструкция if',
        '8. Циклы for и while',
        '9. Функции',
        '10. Параметры функций',
        '11. Оператор return',
        '12. Функция как тип',
        '13. Лямбда-выражения',
        '14. Преобразование типов',
        '15. Область видимости',
        '16. Замыкания',
        '17. Декораторы',
        '18. Основы Python',
        '19. Функции и декораторы',
        '20. Консольный банк',
    ]
        return russian_titles

    def get_localized_titles(self, language='ru'):
        """Возвращает локализованные названия примеров для спиннера"""
        if language == 'ru':
            return [
            '1. Введение в написание программ',
            '2. Переменные и типы данных',
            '3. Консольный ввод и вывод',
            '4. Арифметические операции с числами',
            '5. Условные выражения',
            '6. Операции со строками',
            '7. Условная конструкция if',
            '8. Циклы for и while',
            '9. Функции',
            '10. Параметры функций',
            '11. Оператор return',
            '12. Функция как тип',
            '13. Лямбда-выражения',
            '14. Преобразование типов',
            '15. Область видимости',
            '16. Замыкания',
            '17. Декораторы',
            '18. Основы Python',
            '19. Функции и декораторы',
            '20. Консольный банк',
        ]
        else:
            return [
            '1. Introduction to Programming',
            '2. Variables and Data Types',
            '3. Console Input and Output',
            '4. Arithmetic Operations',
            '5. Conditional Expressions',
            '6. String Operations',
            '7. The if Statement',
            '8. For and While Loops',
            '9. Functions',
            '10. Function Parameters',
            '11. The return Operator',
            '12. Function as a Type',
            '13. Lambda Expressions',
            '14. Type Conversion',
            '15. Variable Scope',
            '16. Closures',
            '17. Decorators',
            '17. Decorators',
            '18. Python Basics',
            '19. Functions and Decorators',
            '20. Console Bank'
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
# Python Learning IDE

<div align="center">
  <img src="icon.png" width="128" height="128" alt="Python Learning IDE Logo">
  <h3>Learn Python on Android</h3>
  <p>Мощная IDE для изучения Python прямо на вашем телефоне</p>
  
  <img src="https://img.shields.io/badge/version-1.0.0-blue">
  <img src="https://img.shields.io/badge/python-3.10%2B-green">
  <img src="https://img.shields.io/badge/license-MIT-green">
  <img src="https://img.shields.io/badge/Android-8.0%2B-brightgreen">
  <img src="https://img.shields.io/badge/tests-107%20passed-success">
</div>

---

## 📱 О проекте

**Python Learning IDE** — это полноценная среда разработки Python для Android. 
Приложение позволяет писать, редактировать, сохранять и выполнять Python-код 
прямо на вашем мобильном устройстве.

### ✨ Основные возможности

| Функция | Описание |
|---------|----------|
| 🖥️ **Редактор кода** | Подсветка синтаксиса, автодополнение, нумерация строк |
| 📁 **Файловый менеджер** | Открытие, сохранение, переименование, удаление файлов |
| 🎨 **Две темы** | Светлая и тёмная темы оформления |
| 🌍 **Два языка** | Русский и английский интерфейс |
| 🤖 **AI ассистент** | Помощь в написании кода (Gemini API) |
| 📑 **Вкладки** | Работа с несколькими файлами одновременно |
| 🔍 **Поиск и замена** | Быстрый поиск и замена текста в коде |
| ⚡ **Выполнение кода** | Запуск Python-кода прямо в приложении |
| ↩️ **Undo/Redo** | Отмена и повтор действий |
| 🎨 **Форматирование** | Автоматическое форматирование кода (autopep8) |
| 📋 **Копи/Вставка** | Работа с буфером обмена |
| 🔤 **Смена шрифта** | Выбор шрифта для редактора (JetBrains Mono, Fira Code и др.) |

---

## 📸 Скриншоты

<!-- Добавьте скриншоты вашего приложения -->
<!-- 
![Главный экран](screenshots/main.jpg)
![Редактор кода](screenshots/editor.jpg)
![Файловый менеджер](screenshots/files.jpg)
-->

---

## 🚀 Установка

### На Android (APK)

1. Скачайте последнюю версию APK из [Releases](https://github.com/emerlukov/python-learning-ide/releases)
2. Разрешите установку из неизвестных источников в настройках Android
3. Откройте скачанный APK-файл
4. Нажмите "Установить"

### Для разработки (ПК)

#### Требования
- Python 3.10 или выше
- pip (менеджер пакетов Python)

#### Установка

```bash
# Клонируйте репозиторий
git clone https://github.com/emerlukov/python-learning-ide.git
cd python-learning-ide

# Создайте виртуальное окружение
python -m venv venv

# Активируйте виртуальное окружение
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Установите зависимости
pip install -r requirements.txt

# Запустите приложение
python main.py
```
## 📦 Зависимости

| Пакет | Версия | Назначение |
|-------|--------|-------------|
| kivy | 2.3.1 | Графический фреймворк |
| kivymd | 1.2.0 | Material Design виджеты |
| pygments | - | Подсветка синтаксиса |
| plyer | - | Вибрация и системные функции |
| autopep8 | - | Форматирование кода |
| buildozer | - | Сборка APK (опционально) |

```bash
pip install kivy==2.3.1 kivymd==1.2.0 pygments plyer autopep8 buildozer
```
```
📁 Структура проекта
PythonLearning/
├── core/ # Ядро приложения
│ ├── settings.py # Управление настройками
│ ├── themes.py # Управление темами
│ └── translations.py # Переводы (RU/EN)
├── managers/ # Менеджеры
│ ├── autocomplete.py # Автодополнение кода
│ ├── executor.py # Выполнение Python-кода
│ ├── input_handler.py # Обработка ввода
│ ├── emergency_recovery.py # Восстановление после краша
│ ├── file_handlers.py # Файловые операции
│ └── tab_manager.py # Управление вкладками
├── ui/ # UI компоненты
│ ├── menus.py # Меню (язык, тема, шрифт)
│ └── top_bar.py # Верхняя панель
├── utils/ # Утилиты
│ ├── android_utils.py # Android-специфичные функции
│ ├── debug_utils.py # Отладка и логирование
│ ├── error_explainer.py # Объяснение ошибок
│ ├── hotkeys.py # Горячие клавиши
│ └── screen_utils.py # Адаптация под разные экраны
├── widgets/ # Виджеты интерфейса
│ ├── bars.py # Панели инструментов
│ ├── dialogs.py # Диалоговые окна
│ ├── editor.py # Редактор кода
│ └── live_analyzer.py # Анализ кода в реальном времени
├── tests/ # Тесты (107 штук)
│ ├── run_tests.py # Запуск тестов
│ ├── test_settings.py
│ ├── test_theme_manager.py
│ └── ...
├── fonts/ # Шрифты
├── data/ # Данные приложения
│ └── examples.json # 25 примеров кода
├── .github/ # GitHub Actions (CI/CD)
│ └── workflows/
│ ├── build.yml # Сборка APK
│ └── tests.yml # Автоматические тесты
├── animated_splash.py # Анимированная заставка
├── file_manager.py # Файловый менеджер
├── app.py # Основной класс приложения
├── main.py # Точка входа
├── buildozer.spec # Конфигурация для сборки APK
├── requirements.txt # Зависимости
└── README.md # Документация
```

## 🎮 Управление

### Панель действий (Action Bar)

| Кнопка | Действие |
|--------|----------|
| ↩️ | Отменить (Undo) |
| ↪️ | Повторить (Redo) |
| 📋 | Копировать |
| 📌 | Вставить |
| ✂️ | Вырезать |
| ✓ | Выделить всё |
| 🔧 | Автодополнение |
| 🔑 | Ключевые слова Python |
| 🧹 | Очистить весь код |
| 🔍 | Поиск |
| 🔄 | Поиск и замена |
| ⬇️ | Перейти к строке |

### Панель символов (Symbol Bar)

- Табуляция
- Скобки: `( )`, `[ ]`, `{ }`, `" "`, `' '`
- Операторы: `=`, `:`, `+`, `-`, `*`, `/`, `%`
- Спецсимволы: `#`, `@`, `&`, `|`, `!`, `?`, `;`

### Главное меню (☰)

- **Открыть файл** — загрузка кода из файла
- **Сохранить файл** — сохранение кода в файл
- **Поиск** — поиск текста в коде
- **Заменить** — поиск и замена
- **История** — просмотр истории выполнения
- **Формат** — форматирование кода
- **Настройки** — язык, тема, шрифт, подсветка

## 🔧 Настройка AI ассистента

Для использования AI ассистента требуется API ключ Gemini:

1. Перейдите на [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
2. Создайте API ключ
3. В приложении: **Меню → Настройки → API ключ**
4. Вставьте ключ и нажмите **Сохранить**

## 🏗️ Сборка APK (для разработчиков)

### Способ 1: Через buildozer (Linux/Mac)

```bash
pip install buildozer
buildozer init
# Отредактируйте buildozer.spec
buildozer -v android debug
```

### Способ 2: Через WSL2 (Windows)

```bash
# Установите WSL2
wsl --install

# В Ubuntu:
sudo apt update
sudo apt install -y python3-pip git zip unzip openjdk-17-jdk
sudo apt install -y autoconf libtool pkg-config zlib1g-dev
pip3 install buildozer cython

cd /mnt/c/Users/emerl/PycharmProjects/PythonProject3
buildozer -v android debug
```

### Результат

APK-файл появится в папке `bin/`

## 📄 Лицензия
MIT License

Copyright (c) 2025 Python Learning IDE

Разрешается бесплатно использовать, копировать, изменять и распространять
данное программное обеспечение при условии сохранения уведомления об авторских правах.

## 🤝 Вклад в проект
Приветствуются pull requests и issues!

Форкните репозиторий

Создайте ветку для фичи (git checkout -b feature/amazing-feature)

Зафиксируйте изменения (git commit -m 'Add amazing feature')

Отправьте в ветку (git push origin feature/amazing-feature)

Откройте Pull Request

## 📧 Контакты
Автор: [EMERLUKOV]

Email: [emerlukov@gmail.com]

GitHub: github.com/emerlukov

## 🙏 Благодарности
Kivy — за отличный фреймворк

KivyMD — за Material Design компоненты

Pygments — за подсветку синтаксиса

Google Gemini — за AI API

<div align="center">
  <b>Сделано с ❤️ для изучения Python</b>
</div>

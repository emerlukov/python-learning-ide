[app]

# (str) Название приложения
title = Python Learning IDE

# (str) Название пакета
package.name = pythonlearningide

# (str) Домен пакета
package.domain = com.emerlukov

# (str) Исходный код приложения
source.dir = .

# (list) Расширения файлов
source.include_exts = py,png,jpg,kv,atlas,ttf,json,txt,md

# (list) Папки которые не нужно включать
source.exclude_dirs = .git,__pycache__,bin,.buildozer,venv

# (list) Файлы которые не нужно включать
source.exclude_patterns = *.pyc,*.pyo

# (str) Версия приложения
version = 3.4.0

# (list) Зависимости
requirements = python3==3.10.7,kivy==2.3.0,kivymd,pygments,autopep8,plyr

# (str) Экран загрузки
presplash.filename = splash.png

# (str) Иконка приложения
icon.filename = icon.png

# (str) Ориентация
orientation = portrait

# (bool) Полноэкранный режим
fullscreen = 0

# (int) Android API
android.api = 33

# (int) Минимальный Android API
android.minapi = 24

# (int) NDK API
android.ndk_api = 24

# (str) Версия NDK
android.ndk = 25b

# (str) Архитектуры
android.archs = arm64-v8a, armeabi-v7a

# (list) Разрешения
android.permissions = INTERNET,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,MANAGE_EXTERNAL_STORAGE

# (bool) AndroidX
android.enable_androidx = True

# (bool) Использовать storage API
android.accept_sdk_license = True

# (str) Цвет строки состояния
android.statusbar_color = #121212

# (str) Цвет навигации
android.navigationbar_color = #121212

# (bool) Не показывать лог
log_level = 2

# (bool) Backup
android.allow_backup = True

# (str) Точка входа
entrypoint = main.py

# (str) Главный файл
source.main = main.py

# (bool) Копировать libs
copy_libs = 1

# (bool) Использовать sqlite
android.copy_libs = 1

# (str) Дополнительные java классы
# android.add_src =

# (str) Дополнительные aar
# android.add_aars =

# (str) Дополнительные jar
# android.add_jars =

# (str) Дополнительные assets
# android.add_assets =

# (str) Дополнительные ресурсы
# android.add_resources =

# (str) Дополнительные зависимости gradle
# android.gradle_dependencies =

# (bool) Использовать legacy storage
android.manifest.application_arguments = android:requestLegacyExternalStorage="true"

# (str) Сервисы
# services =

# (str) Python-for-android branch
p4a.branch = master

# (bool) Использовать приватное хранилище
android.private_storage = True

# (bool) Wake lock
android.wakelock = False

# (str) Bootstrap
p4a.bootstrap = sdl2

# (str) Цвет splash
android.presplash_color = #121212

# (bool) Очистка после сборки
build_dir = .buildozer

# (str) Архивировать python
android.release_artifact = apk

# (bool) Debuggable
android.debuggable = False

# (str) Имя apk
package.full_name = Python Learning IDE

# (bool) Использовать logcat
android.logcat_filters = *:S python:D

# (str) Home app
# android.home_app = False

# (bool) Extract native libs
android.extract_native_libs = True

# (bool) Отключить окно разрешений SDL
sdl2.disable_text_input = False

# (str) Дополнительные аргументы p4a
# p4a.extra_args =

# (str) Gradle options
# android.gradle_options =

# (str) Версия SDK
android.sdk = 33

# (bool) Использовать AAB
# android.release_artifact = aab


[buildozer]

# (int) Лог
log_level = 2

# (int) Предупреждения
warn_on_root = 1

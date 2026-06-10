[app]

title = Python Learning IDE
package.name = pythonlearningide
package.domain = com.emerlukov
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf,json,txt,md,otf
source.include_dirs = fonts
source.exclude_dirs = .git,__pycache__,bin,.buildozer,venv,.github
source.exclude_patterns = *.pyc,*.pyo
version = 1.0.0

# ========== ТРЕБОВАНИЯ ==========
# ВОЗВРАЩАЕМ kivymd==1.1.1 (она существует)
requirements = python3==3.10.7,hostpython3==3.10.7,kivy==2.3.0,kivymd==1.1.1,pygments,autopep8,pycodestyle,plyer,requests,androidstorage4kivy

# ========== ЗАСТАВКИ ==========
presplash.filename = splash.png
presplash.color = #000000
android.presplash_color = #000000

# ========== ИКОНКА ==========
icon.filename = icon.png

# ========== ОСНОВНЫЕ НАСТРОЙКИ ==========
orientation = portrait
fullscreen = 0

# ========== ANDROID НАСТРОЙКИ ==========
android.api = 34
android.minapi = 24
android.targetapi = 34
android.ndk_api = 24
android.ndk = 25b
android.add_sdk = 34
android.archs = arm64-v8a

android.manifest.extra_queries =
    <intent>
        <action android:name="android.intent.action.OPEN_DOCUMENT_TREE" />
    </intent>

android.manifest.window_softinput_mode = adjustNothing

android.permissions = INTERNET, VIBRATE, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE, MANAGE_EXTERNAL_STORAGE
android.enable_androidx = True
android.accept_sdk_license = True
android.statusbar_color = #FFFFFF
android.navigationbar_color = #FFFFFF

android.private_storage = False
android.allow_backup = True

entrypoint = main.py
source.main = main.py
android.copy_libs = 1

# ========== НАСТРОЙКИ СТАБИЛЬНОСТИ ==========
p4a.branch = master
p4a.hostpython_version = 3.10.7
android.wakelock = False
p4a.bootstrap = sdl2
android.release_artifact = apk
android.debuggable = False
package.full_name = Python Learning IDE
android.logcat_filters = *:S python:D
android.extract_native_libs = True
log_level = 2

[buildozer]
log_level = 2
warn_on_root = 1

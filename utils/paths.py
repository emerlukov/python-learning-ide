"""
Centralized path management for bundled assets and user-writable data.

Bundled (read-only): course.json, examples.json — shipped with the app.
User data (writable): progress, settings, autosave, tabs — stored in
Kivy's user_data_dir on Android, or project data/ during desktop dev.
"""
import os
import shutil
import sys

_PROJECT_ROOT = None
_USER_DATA_DIR = None
_BUNDLED_DATA_DIR = None
_MIGRATION_FLAG = '.paths_migrated_v1'

WRITABLE_DATA_FILES = (
    'progress.json',
    'python_ide_settings.json',
    'autosave.py',
    'emergency_backup.py',
    'course.json',
)

WRITABLE_ROOT_FILES = (
    'tabs.json',
    'language.txt',
)


def get_project_root() -> str:
    global _PROJECT_ROOT
    if _PROJECT_ROOT is None:
        _PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    return _PROJECT_ROOT


def is_android() -> bool:
    """Проверяет, запущено ли приложение на Android"""
    try:
        from kivy.utils import platform
        return platform == 'android'
    except:
        return False


def set_user_data_dir(path: str | None) -> None:
    """Override writable storage directory (for tests)."""
    global _USER_DATA_DIR
    _USER_DATA_DIR = os.path.abspath(path) if path else None


def set_bundled_data_dir(path: str | None) -> None:
    """Override bundled assets directory (for tests)."""
    global _BUNDLED_DATA_DIR
    _BUNDLED_DATA_DIR = os.path.abspath(path) if path else None


def reset_paths() -> None:
    """Reset overrides — call from test tearDown."""
    set_user_data_dir(None)
    set_bundled_data_dir(None)


def get_bundled_data_dir() -> str:
    if _BUNDLED_DATA_DIR:
        return _BUNDLED_DATA_DIR
    return os.path.join(get_project_root(), 'data')


def get_user_data_dir() -> str:
    """Возвращает папку для пользовательских данных"""
    if _USER_DATA_DIR:
        return _USER_DATA_DIR

    # На Android используем app.user_data_dir
    if is_android():
        try:
            from kivy.app import App
            app = App.get_running_app()
            if app and getattr(app, 'user_data_dir', None):
                return app.user_data_dir
        except Exception:
            pass

    # На десктопе всегда используем локальную папку data/
    return get_bundled_data_dir()


def ensure_user_data_dir() -> str:
    path = get_user_data_dir()
    os.makedirs(path, exist_ok=True)
    return path


def user_data_path(filename: str) -> str:
    return os.path.join(ensure_user_data_dir(), filename)


def bundled_data_path(filename: str) -> str:
    return os.path.join(get_bundled_data_dir(), filename)


def resolve_read_path(filename: str) -> str:
    """
    Path for reading a data file: prefer user copy, fall back to bundled asset.
    """
    user_copy = user_data_path(filename)
    if os.path.exists(user_copy):
        return user_copy
    return bundled_data_path(filename)


def migrate_legacy_data() -> None:
    """One-time migration from cwd/project data/ into user_data_dir."""
    user_dir = ensure_user_data_dir()
    flag_path = os.path.join(user_dir, _MIGRATION_FLAG)
    if os.path.exists(flag_path):
        return

    legacy_sources = [
        os.path.join(get_project_root(), 'data'),
        os.path.join(os.getcwd(), 'data'),
    ]

    for legacy_dir in legacy_sources:
        if not os.path.isdir(legacy_dir):
            continue
        for filename in WRITABLE_DATA_FILES:
            src = os.path.join(legacy_dir, filename)
            dst = user_data_path(filename)
            if os.path.exists(src) and not os.path.exists(dst):
                try:
                    shutil.copy2(src, dst)
                except OSError:
                    pass

    for filename in WRITABLE_ROOT_FILES:
        for base in (get_project_root(), os.getcwd()):
            src = os.path.join(base, filename)
            dst = user_data_path(filename)
            if os.path.exists(src) and not os.path.exists(dst):
                try:
                    shutil.copy2(src, dst)
                except OSError:
                    pass

    try:
        with open(flag_path, 'w', encoding='utf-8') as f:
            f.write('ok')
    except OSError:
        pass
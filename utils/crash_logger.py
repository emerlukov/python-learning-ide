"""
Модуль для логирования крашей приложения.
Сохраняет логи в папку загрузок на Android для отладки.
"""

import sys
import traceback
import datetime
import os
import threading
from kivy.utils import platform


class CrashLogger:
    """Логгер для сохранения информации о крашах приложения"""

    def __init__(self):
        self._lock = threading.Lock()
        self._crash_log_dir = self._get_crash_log_dir()
        self._ensure_log_dir()

    def _get_crash_log_dir(self):
        """Возвращает директорию для сохранения логов крашей"""
        if platform == 'android':
            try:
                from android.storage import primary_external_storage_path
                # На Android сохраняем в папку Download
                base_dir = primary_external_storage_path()
                crash_dir = os.path.join(base_dir, "Download", "PythonLearningIDE", "crashes")
            except ImportError:
                # Fallback если android.storage недоступен
                try:
                    from jnius import autoclass
                    Environment = autoclass('android.os.Environment')
                    base_dir = Environment.getExternalStoragePublicDirectory("Download").getPath()
                    crash_dir = os.path.join(base_dir, "PythonLearningIDE", "crashes")
                except:
                    # Последний fallback - текущая директория
                    crash_dir = os.path.join(os.getcwd(), "crashes")
        else:
            # На десктопе сохраняем в папку проекта
            crash_dir = os.path.join(os.getcwd(), "crashes")

        return crash_dir

    def _ensure_log_dir(self):
        """Создает директорию для логов если она не существует"""
        try:
            if not os.path.exists(self._crash_log_dir):
                os.makedirs(self._crash_log_dir, exist_ok=True)
        except Exception as e:
            print(f"[CrashLogger] Error creating log directory: {e}")
            # Fallback - используем временную директорию
            import tempfile
            self._crash_log_dir = tempfile.gettempdir()

    def _get_log_filename(self):
        """Генерирует имя файла лога на основе времени"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"crash_{timestamp}.log"

    def _get_device_info(self):
        """Собирает информацию об устройстве"""
        info = {
            'platform': platform,
            'timestamp': datetime.datetime.now().isoformat(),
        }

        if platform == 'android':
            try:
                from jnius import autoclass
                Build = autoclass('android.os.Build$VERSION')
                info['android_version'] = Build.RELEASE
                info['android_api'] = Build.SDK_INT
                info['device_model'] = autoclass('android.os.Build').MODEL
            except:
                info['android_info'] = 'unavailable'
        else:
            import platform as sys_platform
            info['system'] = sys_platform.system()
            info['release'] = sys_platform.release()

        return info

    def log_crash(self, exc_type, exc_value, exc_traceback):
        """Логирует информацию о краше"""
        with self._lock:
            try:
                log_filename = self._get_log_filename()
                log_path = os.path.join(self._crash_log_dir, log_filename)

                with open(log_path, 'w', encoding='utf-8') as f:
                    # Заголовок
                    f.write("=" * 60 + "\n")
                    f.write("PYTHON LEARNING IDE - CRASH LOG\n")
                    f.write("=" * 60 + "\n\n")

                    # Информация об устройстве
                    f.write("DEVICE INFO:\n")
                    f.write("-" * 40 + "\n")
                    device_info = self._get_device_info()
                    for key, value in device_info.items():
                        f.write(f"{key}: {value}\n")
                    f.write("\n")

                    # Информация об ошибке
                    f.write("EXCEPTION INFO:\n")
                    f.write("-" * 40 + "\n")
                    f.write(f"Type: {exc_type.__name__}\n")
                    f.write(f"Message: {str(exc_value)}\n\n")

                    # Стек вызовов
                    f.write("TRACEBACK:\n")
                    f.write("-" * 40 + "\n")
                    traceback.print_exception(exc_type, exc_value, exc_traceback, file=f)
                    f.write("\n")

                    # Локальные переменные на верхнем уровне стека
                    f.write("LOCAL VARIABLES (top frame):\n")
                    f.write("-" * 40 + "\n")
                    if exc_traceback:
                        tb_frame = exc_traceback.tb_frame
                        try:
                            locals_dict = tb_frame.f_locals
                            for var_name, var_value in locals_dict.items():
                                try:
                                    # Ограничиваем длину значения для безопасности
                                    value_str = str(var_value)
                                    if len(value_str) > 200:
                                        value_str = value_str[:200] + "..."
                                    f.write(f"{var_name} = {value_str}\n")
                                except:
                                    f.write(f"{var_name} = <unable to convert>\n")
                        except:
                            f.write("Unable to retrieve local variables\n")
                    f.write("\n")

                    # Дополнительная информация
                    f.write("ADDITIONAL INFO:\n")
                    f.write("-" * 40 + "\n")
                    f.write(f"Log file: {log_path}\n")
                    f.write(f"Working directory: {os.getcwd()}\n")

                    # Попытка получить информацию о памяти
                    try:
                        import psutil
                        process = psutil.Process()
                        f.write(f"Memory usage: {process.memory_info().rss / 1024 / 1024:.2f} MB\n")
                    except:
                        f.write("Memory info: unavailable\n")

                print(f"[CrashLogger] Crash log saved to: {log_path}")
                return log_path

            except Exception as e:
                print(f"[CrashLogger] Error saving crash log: {e}")
                # Пытаемся сохранить хотя бы в текущую директорию
                try:
                    fallback_path = os.path.join(os.getcwd(), f"crash_fallback_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
                    with open(fallback_path, 'w', encoding='utf-8') as f:
                        f.write(f"Crash log fallback\nError: {e}\n")
                        f.write(f"Original error: {exc_type.__name__}: {str(exc_value)}\n")
                        traceback.print_exception(exc_type, exc_value, exc_traceback, file=f)
                    print(f"[CrashLogger] Fallback log saved to: {fallback_path}")
                except:
                    print("[CrashLogger] Failed to save fallback log")
                return None

    def log_custom_error(self, error_message, context=None):
        """Логирует пользовательскую ошибку без краша"""
        with self._lock:
            try:
                log_filename = self._get_log_filename().replace("crash_", "error_")
                log_path = os.path.join(self._crash_log_dir, log_filename)

                with open(log_path, 'w', encoding='utf-8') as f:
                    f.write("=" * 60 + "\n")
                    f.write("PYTHON LEARNING IDE - ERROR LOG\n")
                    f.write("=" * 60 + "\n\n")

                    f.write("DEVICE INFO:\n")
                    f.write("-" * 40 + "\n")
                    device_info = self._get_device_info()
                    for key, value in device_info.items():
                        f.write(f"{key}: {value}\n")
                    f.write("\n")

                    f.write("ERROR MESSAGE:\n")
                    f.write("-" * 40 + "\n")
                    f.write(f"{error_message}\n\n")

                    if context:
                        f.write("CONTEXT:\n")
                        f.write("-" * 40 + "\n")
                        f.write(f"{context}\n\n")

                    f.write("TIMESTAMP:\n")
                    f.write("-" * 40 + "\n")
                    f.write(f"{datetime.datetime.now().isoformat()}\n")

                print(f"[CrashLogger] Error log saved to: {log_path}")
                return log_path

            except Exception as e:
                print(f"[CrashLogger] Error saving custom error log: {e}")
                return None


# Глобальный экземпляр логгера
_crash_logger = None


def get_crash_logger():
    """Возвращает глобальный экземпляр логгера крашей"""
    global _crash_logger
    if _crash_logger is None:
        _crash_logger = CrashLogger()
    return _crash_logger


def install_crash_handler():
    """Устанавливает глобальный обработчик крашей"""
    crash_logger = get_crash_logger()

    def handle_crash(exc_type, exc_value, exc_traceback):
        """Обработчик необработанных исключений"""
        # Сначала логируем краш
        crash_logger.log_crash(exc_type, exc_value, exc_traceback)

        # Затем вызываем стандартный обработчик
        sys.__excepthook__(exc_type, exc_value, exc_traceback)

    # Устанавливаем наш обработчик
    sys.excepthook = handle_crash

    print("[CrashLogger] Crash handler installed")


def log_error(error_message, context=None):
    """Логирует пользовательскую ошибку без краша"""
    crash_logger = get_crash_logger()
    return crash_logger.log_custom_error(error_message, context)
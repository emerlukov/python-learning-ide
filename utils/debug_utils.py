"""
Debug utilities for logging
"""
import os
from datetime import datetime

# ====================== ГЛОБАЛЬНЫЙ ФЛАГ ОТЛАДКИ ======================
DEBUG = True


def log_error(msg):
    """
    Записывает отладочную информацию в файл на устройстве.
    Используется для отладки на Android, где нет консоли.
    Включить: DEBUG = True
    """
    if not DEBUG:
        return
    try:
        log_paths = [
            '/storage/emulated/0/Download/app_debug.log',
            '/storage/emulated/0/app_debug.log',
            '/sdcard/app_debug.log'
        ]
        for log_path in log_paths:
            try:
                log_dir = os.path.dirname(log_path)
                if log_dir and not os.path.exists(log_dir):
                    os.makedirs(log_dir, exist_ok=True)
                with open(log_path, 'a', encoding='utf-8') as f:
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    f.write(f"{timestamp}: {msg}\n")
                break
            except:
                continue
    except:
        pass
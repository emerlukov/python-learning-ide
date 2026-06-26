# tests/run_tests.py
"""
Run all unit tests for Python Learning IDE
"""
import sys
import os
import subprocess


def run_pytest(args):
    """Запускает pytest"""
    cmd = [sys.executable, "-m", "pytest"] + args
    print(f"Running: {' '.join(cmd)}")
    print("=" * 60)
    return subprocess.run(cmd).returncode


def main():
    if len(sys.argv) < 2:
        # Запуск всех тестов
        sys.exit(run_pytest(["tests/", "-v"]))

    command = sys.argv[1]

    if command == "coverage":
        # Запуск с покрытием
        sys.exit(run_pytest([
            "tests/", "-v",
            "--cov=ide_core", "--cov=managers", "--cov=widgets", "--cov=utils",
            "--cov-report=term", "--cov-report=html"
        ]))
    elif command == "fast":
        # Быстрый запуск (без GUI тестов)
        sys.exit(run_pytest(["tests/", "-v", "-m", "not gui"]))
    elif command == "module" and len(sys.argv) > 2:
        # Запуск конкретного модуля
        sys.exit(run_pytest([f"tests/{sys.argv[2]}.py", "-v"]))
    elif command == "list":
        # Список модулей
        modules = [
            "test_settings", "test_error_explainer", "test_examples_manager",
            "test_theme_manager", "test_tab_manager", "test_code_executor",
            "test_screen_utils", "test_translations", "test_editor",
            "test_dialogs", "test_file_manager", "test_integration"
        ]
        print("Доступные модули:")
        for m in modules:
            print(f"  - {m}")
        sys.exit(0)
    else:
        print(f"Неизвестная команда: {command}")
        print("Доступные: coverage, fast, module, list")
        sys.exit(1)


if __name__ == "__main__":
    main()
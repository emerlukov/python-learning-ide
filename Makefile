# Makefile - файл должен называться именно Makefile (без расширения)

.PHONY: help test coverage test-fast install clean

help:
	@echo "Доступные команды:"
	@echo "  make install      - Установить все зависимости"
	@echo "  make test         - Запустить все тесты"
	@echo "  make coverage     - Запустить тесты с отчетом о покрытии"
	@echo "  make test-fast    - Быстрый запуск (без GUI/Android тестов)"
	@echo "  make clean        - Очистить временные файлы"

install:
	pip install -r requirements.txt
	pip install pytest pytest-cov pytest-xdist pytest-timeout
	pip install pre-commit flake8 black isort mypy bandit
	pre-commit install

test:
	python tests/run_tests.py

coverage:
	python tests/run_tests.py coverage

test-fast:
	python tests/run_tests.py fast

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>nul || true
	find . -type f -name "*.pyc" -delete
	rmdir /s /q .pytest_cache 2>nul
	rmdir /s /q .coverage 2>nul
	rmdir /s /q htmlcov 2>nul
	rmdir /s /q .mypy_cache 2>nul
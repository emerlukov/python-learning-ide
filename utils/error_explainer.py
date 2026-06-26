"""
Error Explainer - анализатор ошибок Python
Находит все ошибки без остановки на первой
"""

import re
from typing import List, Dict, Optional


class ErrorExplainer:
    """Анализатор ошибок Python - находит ВСЕ ошибки за один проход"""

    def __init__(self, locale: str = 'ru'):
        self.locale = locale

    def _msg(self, ru: str, en: str) -> str:
        return ru if self.locale == 'ru' else en

    def explain(self, error_text: str, user_code: str = "", line_offset: int = 0) -> str:
        if not user_code:
            return self._explain_traceback_error(error_text)

        errors = self._find_all_errors(user_code)

        if errors:
            return self._format_errors(errors)

        if error_text:
            return self._explain_traceback_error(error_text)

        return self._msg("Код синтаксически верен!", "Code is syntactically correct!")

    def _find_all_errors(self, code: str) -> List[Dict]:
        """Находит ВСЕ ошибки в коде за один проход"""
        errors = []
        lines = code.split('\n')

        # Добавляем все проверки в порядке выполнения
        checks = [
            self._check_class_colon,
            self._check_clas_typo,
            self._check_def_merged,
            self._check_missing_colon,
            self._check_import_typo,
            self._check_not_typo,
            self._check_raise_typo,
            self._check_assert_typo,
            self._check_true_typo,
            self._check_none_typo,
            self._check_return_typo,
            self._check_range_typo,
            self._check_unclosed_quotes,
            self._check_mismatched_parens,
        ]

        for i, line in enumerate(lines, 1):
            if not line.strip() or line.strip().startswith('#'):
                continue

            for check in checks:
                error = check(line, i)
                if error:
                    errors.append(error)
                    break  # Одна ошибка на строку

        return errors

    def _check_clas_typo(self, line: str, line_num: int) -> Optional[Dict]:
        # Проверка на 'clas' (одна 's')
        if re.search(r'\bclas\b', line.lower()) and 'class' not in line.lower():
            return {'line': line_num, 'text': self._msg(
                "Опечатка в ключевом слове: 'clas' → 'class'",
                "Typo in keyword: 'clas' → 'class'"
            )}
        # Проверка на 'clss' (две 's')
        if re.search(r'\bclss\b', line.lower()) and 'class' not in line.lower():
            return {'line': line_num, 'text': self._msg(
                "Опечатка в ключевом слове: 'clss' → 'class'",
                "Typo in keyword: 'clss' → 'class'"
            )}
        return None

    def _check_class_colon(self, line: str, line_num: int) -> Optional[Dict]:
        # Проверка для правильного 'class'
        if re.search(r'\bclass\s+\w+', line.lower()):
            if ':' not in line:
                return {'line': line_num, 'text': self._msg(
                    "Забыл двоеточие ':' в конце строки после 'class'",
                    "Missing colon ':' at the end of line after 'class'"
                )}
        # Проверка для строк с опечаткой 'clas' или 'clss'
        if re.search(r'\bcla[s]{1,2}\s+\w+', line.lower()):
            if ':' not in line:
                return {'line': line_num, 'text': self._msg(
                    "Забыл двоеточие ':' в конце строки после 'class'",
                    "Missing colon ':' at the end of line after 'class'"
                )}
        return None

    def _check_def_merged(self, line: str, line_num: int) -> Optional[Dict]:
        match = re.search(r'def([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', line)
        if match:
            name = match.group(1)
            return {'line': line_num, 'text': self._msg(
                f"Ключевое слово 'def' слито с '{name}'. Добавь пробел: 'def {name}'",
                f"Keyword 'def' is merged with '{name}'. Add space: 'def {name}'"
            )}
        return None

    def _check_missing_colon(self, line: str, line_num: int) -> Optional[Dict]:
        keywords = ['def', 'class', 'if', 'for', 'while', 'elif', 'else', 'except', 'finally', 'try', 'with']
        line_lower = line.lower()
        for kw in keywords:
            if re.search(rf'\b{kw}\b', line_lower):
                if ':' not in line and not line.rstrip().endswith('\\'):
                    return {'line': line_num, 'text': self._msg(
                        f"Забыл двоеточие ':' в конце строки после '{kw}'",
                        f"Missing colon ':' at the end of line after '{kw}'"
                    )}
        return None

    def _check_import_typo(self, line: str, line_num: int) -> Optional[Dict]:
        if 'improt' in line.lower():
            return {'line': line_num, 'text': self._msg(
                "Опечатка в import: 'improt' → 'import'",
                "Typo in import: 'improt' → 'import'"
            )}
        return None

    def _check_not_typo(self, line: str, line_num: int) -> Optional[Dict]:
        if 'nott' in line.lower():
            return {'line': line_num, 'text': self._msg(
                "Опечатка в операторе 'not': 'nott' → 'not'",
                "Typo in 'not' operator: 'nott' → 'not'"
            )}
        return None

    def _check_raise_typo(self, line: str, line_num: int) -> Optional[Dict]:
        if 'rais' in line.lower() and 'raise' not in line.lower():
            return {'line': line_num, 'text': self._msg(
                "Опечатка в 'raise': 'rais' → 'raise'",
                "Typo in 'raise': 'rais' → 'raise'"
            )}
        return None

    def _check_assert_typo(self, line: str, line_num: int) -> Optional[Dict]:
        if 'asser' in line.lower() and 'assert' not in line.lower():
            return {'line': line_num, 'text': self._msg(
                "Опечатка в 'assert': 'asser' → 'assert'",
                "Typo in 'assert': 'asser' → 'assert'"
            )}
        return None

    def _check_true_typo(self, line: str, line_num: int) -> Optional[Dict]:
        if 'ture' in line.lower() and 'true' not in line.lower():
            return {'line': line_num, 'text': self._msg(
                "Опечатка в True: 'Ture' → 'True'",
                "Typo in True: 'Ture' → 'True'"
            )}
        return None

    def _check_none_typo(self, line: str, line_num: int) -> Optional[Dict]:
        if 'none' in line.lower():
            if 'NOne' in line:
                return {'line': line_num, 'text': self._msg(
                    "Опечатка в None: 'NOne' → 'None'",
                    "Typo in None: 'NOne' → 'None'"
                )}
        return None

    def _check_return_typo(self, line: str, line_num: int) -> Optional[Dict]:
        if 'retrn' in line.lower():
            return {'line': line_num, 'text': self._msg(
                "Опечатка в return: 'retrn' → 'return'",
                "Typo in return: 'retrn' → 'return'"
            )}
        return None

    def _check_range_typo(self, line: str, line_num: int) -> Optional[Dict]:
        if 'rang' in line.lower() and 'range' not in line.lower():
            return {'line': line_num, 'text': self._msg(
                "Опечатка в range: 'rang' → 'range'",
                "Typo in range: 'rang' → 'range'"
            )}
        return None

    def _check_unclosed_quotes(self, line: str, line_num: int) -> Optional[Dict]:
        quote_count = line.count('"') + line.count("'")
        if quote_count % 2 == 1:
            return {'line': line_num, 'text': self._msg(
                "Незакрытые кавычки в строке",
                "Unclosed quotes in string"
            )}
        return None

    def _check_mismatched_parens(self, line: str, line_num: int) -> Optional[Dict]:
        if line.count('(') != line.count(')'):
            return {'line': line_num, 'text': self._msg(
                "Не совпадает количество открывающих и закрывающих скобок",
                "Mismatched parentheses count"
            )}
        return None

    def _explain_traceback_error(self, error_text: str) -> str:
        lines = []
        error_lower = error_text.lower()

        if 'name' in error_lower and 'is not defined' in error_lower:
            name_match = re.search(r"name '(\w+)' is not defined", error_text)
            name = name_match.group(1) if name_match else "?"
            line_num = self._extract_line_number(error_text)

            lines.append(self._msg("Ошибка: переменная или функция не найдена", "Error: name not defined"))
            lines.append("")
            if line_num:
                lines.append(self._msg(f"Строка {line_num}", f"Line {line_num}"))
                lines.append("")
            lines.append(self._msg(f"Переменная или функция '{name}' не определена. Проверь правильность написания.",
                                  f"Variable or function '{name}' is not defined. Check the spelling."))

        elif 'concatenate' in error_lower:
            lines.append(self._msg("Ошибка: неверный тип данных", "Error: invalid type"))
            lines.append("")
            lines.append(self._msg("Нельзя складывать строку и число. Используй str() или f-строки.",
                                  "Cannot concatenate string and integer. Use str() or f-strings."))

        elif 'division by zero' in error_lower:
            lines.append(self._msg("Ошибка: деление на ноль", "Error: division by zero"))
            lines.append("")
            lines.append(self._msg("Проверь делитель перед операцией: if divisor != 0:",
                                  "Check the divisor before division: if divisor != 0:"))

        else:
            lines.append(self._msg("Неизвестная ошибка", "Unknown error"))
            lines.append("")
            lines.append(error_text[:300])

        lines.append("")
        lines.append(self._msg("Не переживай! Ошибки — это нормально. Так ты учишься быстрее.",
                              "Don't worry! Errors are normal. This is how you learn faster."))
        return '\n'.join(lines)

    def _extract_line_number(self, error_text: str) -> Optional[int]:
        matches = re.findall(r'line\s+(\d+)', error_text, re.IGNORECASE)
        return int(matches[-1]) if matches else None

    def _format_errors(self, errors: List[Dict]) -> str:
        lines = []
        lines.append(self._msg("Найдены следующие ошибки:", "Found the following errors:"))
        lines.append("")
        for err in errors:
            line_info = self._msg(f"Строка {err['line']}", f"Line {err['line']}")
            lines.append(f"  {line_info}: {err['text']}")
        lines.append("")
        lines.append(self._msg("Не переживай! Ошибки — это нормально. Так ты учишься быстрее.",
                              "Don't worry! Errors are normal. This is how you learn faster."))
        return '\n'.join(lines)


def explain_error(error_text: str, user_code: str = "", locale: str = 'ru') -> str:
    return ErrorExplainer(locale).explain(error_text, user_code)
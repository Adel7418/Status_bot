"""
Тесты для валидации времени прибытия мастера
"""

import re

import pytest


def validate_scheduled_time_logic(scheduled_time: str) -> tuple[bool, str]:
    """
    Логика валидации времени прибытия (копия из dispatcher.py)

    Returns:
        (is_valid, error_message)
    """
    if not scheduled_time:
        return True, ""

    scheduled_time = scheduled_time.strip()

    # Проверка длины (минимум 3 символа, максимум 100)
    if len(scheduled_time) < 3:
        return False, "Время/инструкция слишком короткие (минимум 3 символа)"

    if len(scheduled_time) > 100:
        return False, "Время/инструкция слишком длинные (максимум 100 символов)"

    # Проверка на опасные символы и SQL injection
    dangerous_patterns = [
        r"\b(drop|delete|truncate|insert|update|alter)\b.*\b(table|from|into|database|set|where)\b",
        r";\s*(drop|delete|truncate|insert|update|alter)\s+",
        r"--",
        r"/\*.*\*/",
        r"\bxp_",
        r"\bsp_",
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, scheduled_time, re.IGNORECASE):
            return False, "Недопустимые символы в тексте"

    return True, ""


class TestScheduledTimeValidation:
    """Тесты для валидации времени прибытия"""

    @pytest.mark.parametrize(
        "time_input",
        [
            "14:30",
            "завтра 10:00",
            "15.10.2025 16:00",
            "Набрать клиенту",
            "После 14:00",
            "Уточнить у клиента",
            "В течение дня",
            "Через 2 часа",
            "10:00-12:00",
            "Звонок за час",
        ],
    )
    def test_valid_scheduled_times(self, time_input):
        """Тест валидных значений времени прибытия"""
        is_valid, error = validate_scheduled_time_logic(time_input)
        assert is_valid, f"Должно быть валидным: '{time_input}', но получена ошибка: {error}"

    @pytest.mark.parametrize(
        "time_input,expected_error",
        [
            ("12", "Время/инструкция слишком короткие"),
            ("ab", "Время/инструкция слишком короткие"),
            ("a" * 101, "Время/инструкция слишком длинные"),
            ("14:00; DROP TABLE users", "Недопустимые символы"),
            ("test -- comment", "Недопустимые символы"),
            ("/* comment */", "Недопустимые символы"),
            ("exec xp_cmdshell", "Недопустимые символы"),
            ("call sp_executesql", "Недопустимые символы"),
            ("UPDATE orders SET", "Недопустимые символы"),
            ("DELETE FROM table", "Недопустимые символы"),
        ],
    )
    def test_invalid_scheduled_times(self, time_input, expected_error):
        """Тест невалидных значений времени прибытия"""
        is_valid, error = validate_scheduled_time_logic(time_input)
        assert not is_valid, f"Должно быть невалидным: '{time_input}'"
        assert (
            expected_error.lower() in error.lower()
        ), f"Ожидалась ошибка содержащая '{expected_error}', получено: '{error}'"

    def test_empty_string(self):
        """Тест пустой строки - должна быть допустимой (опциональное поле)"""
        is_valid, error = validate_scheduled_time_logic("")
        assert is_valid, "Пустая строка должна быть допустимой"

    def test_none_value(self):
        """Тест None значения"""
        # В реальном коде None не передается, но проверим
        is_valid, error = validate_scheduled_time_logic(None)
        assert is_valid, "None должен быть допустимым"

    def test_whitespace_trimming(self):
        """Тест обработки пробелов"""
        is_valid, error = validate_scheduled_time_logic("  14:30  ")
        assert is_valid, "Время с пробелами должно валидироваться после trim"

    def test_cyrillic_text(self):
        """Тест кириллических инструкций"""
        cyrillic_inputs = [
            "Набрать клиенту",
            "Согласовать время",
            "Выехать после обеда",
            "Уточнить детали",
        ]
        for text in cyrillic_inputs:
            is_valid, error = validate_scheduled_time_logic(text)
            assert is_valid, f"Кириллический текст должен быть валидным: '{text}'"

    def test_mixed_formats(self):
        """Тест смешанных форматов"""
        mixed_inputs = [
            "14:00 или позже",
            "10.10 в 15:00",
            "Понедельник 9:00",
            "После 16:00 набрать",
        ]
        for text in mixed_inputs:
            is_valid, error = validate_scheduled_time_logic(text)
            assert is_valid, f"Смешанный формат должен быть валидным: '{text}'"

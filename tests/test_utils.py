"""
Тесты для утилит
"""
import pytest
from app.utils import validate_phone, format_phone


class TestPhoneUtils:
    """Тесты для функций работы с телефонами"""

    def test_validate_phone_valid_with_plus(self):
        """Тест валидации корректного номера с +"""
        assert validate_phone("+79991234567") is True

    def test_validate_phone_valid_without_plus(self):
        """Тест валидации корректного номера без +"""
        assert validate_phone("79991234567") is True

    def test_validate_phone_invalid_short(self):
        """Тест валидации слишком короткого номера"""
        assert validate_phone("123") is False

    def test_validate_phone_invalid_letters(self):
        """Тест валидации номера с буквами"""
        assert validate_phone("+7999abc4567") is False

    def test_format_phone_with_plus(self):
        """Тест форматирования номера с +"""
        assert format_phone("+79991234567") == "+7 999 123-45-67"

    def test_format_phone_without_plus(self):
        """Тест форматирования номера без +"""
        assert format_phone("79991234567") == "+7 999 123-45-67"


"""
Тесты для regex паттернов и вспомогательных функций
"""

import pytest

from app.services.telegram_parser.patterns import (
    PHONE_PATTERN,
    TIME_PATTERN,
    contains_time_indicator,
    extract_phone,
    looks_like_address,
    normalize_phone,
)


class TestPhonePattern:
    """Тесты для паттерна телефонных номеров"""

    def test_phone_with_plus(self):
        """Телефон с +7"""
        match = PHONE_PATTERN.search("+79001234567")
        assert match is not None

    def test_phone_with_8(self):
        """Телефон с 8"""
        match = PHONE_PATTERN.search("89001234567")
        assert match is not None

    def test_phone_with_spaces(self):
        """Телефон с пробелами"""
        match = PHONE_PATTERN.search("8 900 123 45 67")
        assert match is not None

    def test_phone_with_dashes(self):
        """Телефон с тире"""
        match = PHONE_PATTERN.search("8-900-123-45-67")
        assert match is not None

    def test_phone_with_parentheses(self):
        """Телефон со скобками"""
        match = PHONE_PATTERN.search("8(900)123-45-67")
        assert match is not None


class TestExtractPhone:
    """Тесты для функции извлечения телефона"""

    def test_extract_simple_phone(self):
        """Простой телефон"""
        result = extract_phone("С/м не крутит барабан. +79001234567")
        assert result == "+79001234567"

    def test_extract_phone_with_8(self):
        """Телефон с 8"""
        result = extract_phone("ул. Ленина 5, кв. 10, 89001234567")
        assert result == "89001234567"

    def test_no_phone(self):
        """Нет телефона"""
        result = extract_phone("С/м течёт")
        assert result is None

    def test_phone_in_middle(self):
        """Телефон в середине текста"""
        result = extract_phone("Заявка +79001234567 срочная")
        assert result == "+79001234567"


class TestNormalizePhone:
    """Тесты для нормализации телефона"""

    def test_normalize_8_to_plus7(self):
        """Замена 8 на +7"""
        result = normalize_phone("89001234567")
        assert result == "+79001234567"

    def test_normalize_already_plus7(self):
        """Уже есть +7"""
        result = normalize_phone("+79001234567")
        assert result == "+79001234567"

    def test_normalize_with_spaces(self):
        """С пробелами"""
        result = normalize_phone("8 (900) 123-45-67")
        assert result == "+79001234567"


class TestTimePattern:
    """Тесты для паттерна времени"""

    def test_time_hh_mm(self):
        """Время ЧЧ:ММ"""
        match = TIME_PATTERN.search("14:00")
        assert match is not None

    def test_time_hh_dot_mm(self):
        """Время ЧЧ.ММ"""
        match = TIME_PATTERN.search("10.30")
        assert match is not None

    def test_time_range(self):
        """Диапазон времени"""
        match = TIME_PATTERN.search("с 9 до 12")
        assert match is not None

    def test_time_until(self):
        """До определённого времени"""
        match = TIME_PATTERN.search("к 15:00")
        assert match is not None


class TestContainsTimeIndicator:
    """Тесты для проверки временных индикаторов"""

    def test_tomorrow(self):
        """Завтра"""
        assert contains_time_indicator("завтра к 14:00") is True

    def test_time_range(self):
        """Диапазон"""
        assert contains_time_indicator("с 9 до 12") is True

    def test_no_time(self):
        """Нет времени"""
        assert contains_time_indicator("С/м не крутит барабан") is False

    def test_urgent(self):
        """Срочно"""
        assert contains_time_indicator("срочно") is True

    def test_today(self):
        """Сегодня"""
        assert contains_time_indicator("сегодня") is True


class TestLooksLikeAddress:
    """Тесты для определения адреса"""

    def test_street_with_number(self):
        """Улица с номером"""
        assert looks_like_address("ул. Ленина 5, кв. 10") is True

    def test_address_short(self):
        """Короткий адрес"""
        assert looks_like_address("Ленина 5-10") is True

    def test_not_address(self):
        """Не адрес"""
        assert looks_like_address("не крутит барабан") is False

    def test_with_apartment(self):
        """С квартирой"""
        assert looks_like_address("Гагарина 12 кв 5") is True

    def test_simple_problem(self):
        """Простое описание проблемы"""
        assert looks_like_address("течёт вода") is False

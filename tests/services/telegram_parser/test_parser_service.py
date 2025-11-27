"""
Тесты для OrderParserService
"""

import pytest

from app.services.telegram_parser.parser_service import OrderParserService


class TestOrderParserService:
    """Тесты для парсера заявок"""

    @pytest.fixture
    def parser(self):
        """Фикстура для создания парсера"""
        return OrderParserService()

    def test_parse_full_message(self, parser):
        """Парсинг полного сообщения со всеми полями"""
        text = """С/м не крутит барабан, шумит при отжиме
ул. Ленина 5, кв. 10
+79001234567
завтра к 14:00"""

        result = parser.parse_message(text, message_id=12345)

        assert result.success is True
        assert result.status == "success"
        assert result.data is not None
        assert result.data.equipment_type == "Стиральная машина"
        assert "крутит" in result.data.problem_description.lower()
        assert "Ленина" in result.data.address
        assert result.data.phone == "+79001234567"
        assert result.data.scheduled_time is not None
        assert result.data.client_name == "Клиент"

    def test_parse_minimal_message(self, parser):
        """Парсинг минимального сообщения (только обязательные поля)"""
        text = """тв не включается
Гагарина 12-5"""

        result = parser.parse_message(text, message_id=12346)

        assert result.success is True
        assert result.data.equipment_type == "Телевизор"
        assert "включается" in result.data.problem_description.lower()
        assert "Гагарина" in result.data.address
        assert result.data.phone is None
        assert result.data.scheduled_time is None

    def test_parse_single_line(self, parser):
        """Парсинг однострочного сообщения"""
        text = "С/м течёт. ул. Ленина 5-10. +79001234567"

        result = parser.parse_message(text, message_id=12347)

        assert result.success is True
        assert result.data.equipment_type == "Стиральная машина"
        assert "течёт" in result.data.problem_description.lower()
        assert "Ленина" in result.data.address

    def test_parse_missing_address(self, parser):
        """Парсинг без адреса - должна быть ошибка"""
        text = "С/м течёт вода снизу"

        result = parser.parse_message(text, message_id=12348)

        assert result.success is False
        assert result.status == "missing_fields"
        assert "address" in result.missing_fields

    def test_parse_empty_message(self, parser):
        """Парсинг пустого сообщения"""
        text = ""

        result = parser.parse_message(text, message_id=12349)

        assert result.success is False
        assert result.status == "invalid_format"

    def test_parse_dishwasher(self, parser):
        """Парсинг посудомоечной машины"""
        text = """п/м не сливает воду
Ленина 10 кв 5"""

        result = parser.parse_message(text, message_id=12350)

        assert result.success is True
        assert result.data.equipment_type == "Посудомоечная машина"
        assert "сливает" in result.data.problem_description.lower()

    def test_parse_refrigerator(self, parser):
        """Парсинг холодильника"""
        text = """холод не морозит
ул. Пушкина 20-15"""

        result = parser.parse_message(text, message_id=12351)

        assert result.success is True
        assert result.data.equipment_type == "Холодильник"

    def test_parse_with_time_range(self, parser):
        """Парсинг с диапазоном времени"""
        text = """тв не работает
Гагарина 5
с 9 до 12"""

        result = parser.parse_message(text, message_id=12352)

        assert result.success is True
        assert result.data.scheduled_time is not None
        assert "9" in result.data.scheduled_time

    def test_parse_colloquial_equipment(self, parser):
        """Парсинг разговорных названий"""
        text = """стиралка шумит
Ленина 5"""

        result = parser.parse_message(text, message_id=12353)

        assert result.success is True
        assert result.data.equipment_type == "Стиральная машина"

    def test_parse_message_id_preserved(self, parser):
        """ID сообщения сохраняется"""
        text = "тв не работает. Ленина 5"
        message_id = 99999

        result = parser.parse_message(text, message_id=message_id)

        assert result.data.message_id == message_id

    def test_parse_raw_message_preserved(self, parser):
        """Исходное сообщение сохраняется"""
        text = "тв не работает. Ленина 5"

        result = parser.parse_message(text, message_id=12354)

        assert result.data.raw_message == text

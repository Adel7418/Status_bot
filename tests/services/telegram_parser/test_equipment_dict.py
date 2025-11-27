"""
Тесты для словаря сокращений оборудования
"""

import pytest

from app.services.telegram_parser.equipment_dict import (
    EQUIPMENT_ABBREVIATIONS,
    normalize_equipment_type,
)


class TestEquipmentAbbreviations:
    """Тесты для словаря сокращений"""

    def test_abbreviations_dict_not_empty(self):
        """Словарь сокращений не пустой"""
        assert len(EQUIPMENT_ABBREVIATIONS) > 0

    def test_all_values_are_strings(self):
        """Все значения в словаре - строки"""
        for key, value in EQUIPMENT_ABBREVIATIONS.items():
            assert isinstance(key, str)
            assert isinstance(value, str)

    def test_common_abbreviations_exist(self):
        """Проверка наличия основных сокращений"""
        assert "с/м" in EQUIPMENT_ABBREVIATIONS
        assert "тв" in EQUIPMENT_ABBREVIATIONS
        assert "холод" in EQUIPMENT_ABBREVIATIONS


class TestNormalizeEquipmentType:
    """Тесты для функции нормализации типа оборудования"""

    def test_exact_match_lowercase(self):
        """Точное совпадение в нижнем регистре"""
        result = normalize_equipment_type("с/м")
        assert result == "Стиральная машина"

    def test_exact_match_uppercase(self):
        """Точное совпадение в верхнем регистре"""
        result = normalize_equipment_type("С/М")
        assert result == "Стиральная машина"

    def test_with_brand_name(self):
        """Сокращение с названием бренда"""
        result = normalize_equipment_type("с/м LG")
        assert result == "Стиральная машина"

    def test_tv_abbreviation(self):
        """Сокращение ТВ"""
        result = normalize_equipment_type("тв")
        assert result == "Телевизор"

    def test_tv_with_brand(self):
        """ТВ с брендом"""
        result = normalize_equipment_type("тв samsung")
        assert result == "Телевизор"

    def test_dishwasher(self):
        """Посудомоечная машина"""
        result = normalize_equipment_type("п/м")
        assert result == "Посудомоечная машина"

    def test_refrigerator(self):
        """Холодильник"""
        result = normalize_equipment_type("холод")
        assert result == "Холодильник"

    def test_unknown_equipment(self):
        """Неизвестный тип оборудования"""
        result = normalize_equipment_type("Неизвестная техника")
        assert result == "Неизвестная"  # Возвращает первое слово с заглавной

    def test_empty_string(self):
        """Пустая строка"""
        result = normalize_equipment_type("")
        assert result == ""

    def test_whitespace_handling(self):
        """Обработка пробелов"""
        result = normalize_equipment_type("  с/м  ")
        assert result == "Стиральная машина"

    def test_colloquial_form(self):
        """Разговорная форма"""
        result = normalize_equipment_type("стиралка")
        assert result == "Стиральная машина"

    def test_microwave(self):
        """Микроволновка"""
        result = normalize_equipment_type("свч")
        assert result == "Микроволновая печь"

    def test_conditioner(self):
        """Кондиционер"""
        result = normalize_equipment_type("кондей")
        assert result == "Кондиционер"

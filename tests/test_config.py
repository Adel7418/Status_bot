"""
Тесты для модуля config
"""
import pytest
from app.config import UserRole, OrderStatus, EquipmentType, Config


class TestUserRole:
    """Тесты для класса UserRole"""

    def test_all_roles(self):
        """Тест получения всех ролей"""
        roles = UserRole.all_roles()
        assert UserRole.ADMIN in roles
        assert UserRole.DISPATCHER in roles
        assert UserRole.MASTER in roles
        assert UserRole.UNKNOWN in roles


class TestOrderStatus:
    """Тесты для класса OrderStatus"""

    def test_all_statuses(self):
        """Тест получения всех статусов"""
        statuses = OrderStatus.all_statuses()
        assert OrderStatus.NEW in statuses
        assert OrderStatus.ASSIGNED in statuses
        assert OrderStatus.ACCEPTED in statuses
        assert OrderStatus.ONSITE in statuses
        assert OrderStatus.CLOSED in statuses
        assert OrderStatus.REFUSED in statuses
        assert OrderStatus.DR in statuses

    def test_get_status_emoji(self):
        """Тест получения эмодзи для статуса"""
        assert OrderStatus.get_status_emoji(OrderStatus.NEW) == "🆕"
        assert OrderStatus.get_status_emoji(OrderStatus.ASSIGNED) == "👨‍🔧"
        assert OrderStatus.get_status_emoji(OrderStatus.CLOSED) == "💰"

    def test_get_status_name(self):
        """Тест получения названия статуса"""
        assert OrderStatus.get_status_name(OrderStatus.NEW) == "Новая"
        assert OrderStatus.get_status_name(OrderStatus.ASSIGNED) == "Назначена"
        assert OrderStatus.get_status_name(OrderStatus.CLOSED) == "Завершена"


class TestEquipmentType:
    """Тесты для класса EquipmentType"""

    def test_all_types(self):
        """Тест получения всех типов техники"""
        types = EquipmentType.all_types()
        assert EquipmentType.WASHING_MACHINE in types
        assert EquipmentType.DISHWASHER in types
        assert EquipmentType.TV in types
        assert len(types) == 8


class TestConfig:
    """Тесты для класса Config"""

    def test_validate_with_empty_token(self, monkeypatch):
        """Тест валидации с пустым токеном"""
        monkeypatch.setattr(Config, "BOT_TOKEN", "")
        monkeypatch.setattr(Config, "ADMIN_IDS", [123])
        
        with pytest.raises(ValueError, match="BOT_TOKEN не установлен"):
            Config.validate()

    def test_validate_with_empty_admin_ids(self, monkeypatch):
        """Тест валидации с пустым списком админов"""
        monkeypatch.setattr(Config, "BOT_TOKEN", "test_token")
        monkeypatch.setattr(Config, "ADMIN_IDS", [])
        
        with pytest.raises(ValueError, match="ADMIN_IDS не установлены"):
            Config.validate()

    def test_validate_success(self, monkeypatch):
        """Тест успешной валидации"""
        monkeypatch.setattr(Config, "BOT_TOKEN", "test_token")
        monkeypatch.setattr(Config, "ADMIN_IDS", [123])
        
        assert Config.validate() is True


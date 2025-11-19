"""
Unit tests for Presenters
"""

from datetime import UTC, datetime
from unittest.mock import Mock

import pytest

from app.config import OrderStatus
from app.presenters import MasterPresenter, OrderPresenter


class TestOrderPresenter:
    """Tests for OrderPresenter"""

    def test_format_order_short(self):
        """Test short order formatting"""
        order = Mock()
        order.id = 123
        order.equipment_type = "Холодильник"
        order.scheduled_time = "14:00"
        order.status = OrderStatus.ASSIGNED

        result = OrderPresenter.format_order_short(order)

        assert "#123" in result
        assert "Холодильник" in result
        assert "14:00" in result
        assert "👨‍🔧" in result  # status emoji

    def test_format_order_short_without_scheduled_time(self):
        """Test short order formatting without scheduled time"""
        order = Mock()
        order.id = 456
        order.equipment_type = "Стиральная машина"
        order.scheduled_time = None
        order.status = OrderStatus.NEW

        result = OrderPresenter.format_order_short(order)

        assert "#456" in result
        assert "Стиральная машина" in result
        assert "14:00" not in result

    def test_format_order_details_with_phone(self):
        """Test detailed order formatting with phone"""
        order = Mock()
        order.id = 789
        order.status = OrderStatus.ACCEPTED
        order.equipment_type = "Микроволновка"
        order.description = "Не греет"
        order.client_name = "Иван Иванов"
        order.client_address = "ул. Ленина, 1"
        order.client_phone = "+79991234567"
        order.assigned_master_id = None
        order.notes = None
        order.scheduled_time = None
        order.created_at = datetime(2025, 11, 16, 12, 0, tzinfo=UTC)

        result = OrderPresenter.format_order_details(order, include_client_phone=True)

        assert "#789" in result
        assert "Микроволновка" in result
        assert "Не греет" in result
        assert "Иван Иванов" in result
        assert "ул. Ленина, 1" in result
        assert "+79991234567" in result
        assert "16.11.2025" in result

    def test_format_order_details_without_phone(self):
        """Test detailed order formatting without phone"""
        order = Mock()
        order.id = 100
        order.status = OrderStatus.ACCEPTED
        order.equipment_type = "Телевизор"
        order.description = "Нет звука"
        order.client_name = "Петр Петров"
        order.client_address = "ул. Пушкина, 2"
        order.client_phone = "+79997654321"
        order.assigned_master_id = None
        order.notes = None
        order.scheduled_time = None
        order.created_at = datetime(2025, 11, 16, 15, 30, tzinfo=UTC)

        result = OrderPresenter.format_order_details(order, include_client_phone=False)

        assert "#100" in result
        assert "Телевизор" in result
        assert "+79997654321" not in result
        assert "Будет доступен после прибытия" in result

    def test_format_order_details_with_master(self):
        """Test detailed order formatting with master object"""
        order = Mock()
        order.id = 200
        order.status = OrderStatus.ONSITE
        order.equipment_type = "Посудомойка"
        order.description = "Течет"
        order.client_name = "Мария Сидорова"
        order.client_address = "ул. Гагарина, 3"
        order.client_phone = "+79995551122"
        order.assigned_master_id = 5
        order.notes = "Срочно"
        order.scheduled_time = "16:00"
        order.created_at = datetime(2025, 11, 16, 10, 0, tzinfo=UTC)

        master = Mock()
        master.get_display_name = Mock(return_value="Сергей Мастеров")

        result = OrderPresenter.format_order_details(
            order, include_client_phone=True, master=master
        )

        assert "#200" in result
        assert "Сергей Мастеров" in result
        assert "Срочно" in result
        assert "16:00" in result

    def test_format_order_details_with_escape_html(self):
        """Test order formatting with HTML escaping"""
        order = Mock()
        order.id = 300
        order.status = OrderStatus.NEW
        order.equipment_type = "Тестовая <техника>"
        order.description = "Описание & спецсимволы"
        order.client_name = "Клиент <VIP>"
        order.client_address = "ул. Тестовая & К°"
        order.client_phone = "+79991112233"
        order.assigned_master_id = None
        order.notes = None
        order.scheduled_time = None
        order.created_at = datetime(2025, 11, 16, 9, 0, tzinfo=UTC)

        result = OrderPresenter.format_order_details(order, escape_html=True)

        assert "#300" in result
        assert "&lt;техника&gt;" in result
        assert "&amp; спецсимволы" in result
        assert "&lt;VIP&gt;" in result

    def test_format_order_list(self):
        """Test order list formatting"""
        orders = []
        for i in range(3):
            order = Mock()
            order.id = i + 1
            order.equipment_type = f"Тип{i+1}"
            order.status = OrderStatus.NEW
            order.scheduled_time = None
            orders.append(order)

        result = OrderPresenter.format_master_list = Mock(return_value="Мастер List")
        result = OrderPresenter.format_order_list(orders, "Мои заявки")

        assert "Мои заявки" in result
        assert "(3)" in result
        assert "#1" in result
        assert "#2" in result
        assert "#3" in result

    def test_format_order_list_empty(self):
        """Test empty order list formatting"""
        result = OrderPresenter.format_order_list([], "Мои заявки")

        assert "нет заявок" in result


class TestMasterPresenter:
    """Tests for MasterPresenter"""

    def test_format_master_short(self):
        """Test short master formatting"""
        master = Mock()
        master.get_display_name = Mock(return_value="Алексей Ремонтов")
        master.specialization = "Холодильники"
        master.is_active = True

        result = MasterPresenter.format_master_short(master)

        assert "Алексей Ремонтов" in result
        assert "Холодильники" in result
        assert "🟢" in result  # active emoji

    def test_format_master_short_inactive(self):
        """Test short master formatting for inactive master"""
        master = Mock()
        master.get_display_name = Mock(return_value="Петр Мастер")
        master.specialization = "Стиралки"
        master.is_active = False

        result = MasterPresenter.format_master_short(master)

        assert "Петр Мастер" in result
        assert "🔴" in result  # inactive emoji

    def test_format_master_details(self):
        """Test detailed master formatting"""
        master = Mock()
        master.get_display_name = Mock(return_value="Иван Сервисов")
        master.phone = "+79991234567"
        master.specialization = "Микроволновки"
        master.is_approved = True
        master.is_active = True
        master.work_chat_id = None

        result = MasterPresenter.format_master_details(master, include_stats=False)

        assert "Иван Сервисов" in result
        assert "+79991234567" in result
        assert "Микроволновки" in result
        assert "✅" in result  # approved
        assert "🟢" in result  # active

    def test_format_master_list(self):
        """Test master list formatting"""
        masters = []
        for i in range(2):
            master = Mock()
            master.get_display_name = Mock(return_value=f"Мастер{i+1}")
            master.specialization = f"Спец{i+1}"
            master.is_active = True
            masters.append(master)

        result = MasterPresenter.format_master_list(masters, "Доступные мастера")

        assert "Доступные мастера" in result
        assert "(2)" in result
        assert "Мастер1" in result
        assert "Мастер2" in result

    def test_format_master_list_empty(self):
        """Test empty master list formatting"""
        result = MasterPresenter.format_master_list([], "Мастера")

        assert "нет мастеров" in result

    def test_format_master_stats(self):
        """Test master stats formatting"""
        master = Mock()
        master.get_display_name = Mock(return_value="Сергей Профи")

        result = MasterPresenter.format_master_stats(
            master, total_orders=10, completed_orders=8, in_progress_orders=2, total_revenue=50000.0
        )

        assert "Сергей Профи" in result
        assert "10" in result
        assert "8" in result
        assert "2" in result
        assert "50000.00" in result
        assert "80.0%" in result  # completion rate


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

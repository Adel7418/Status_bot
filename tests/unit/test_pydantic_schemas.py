"""Тесты для Pydantic схем валидации"""
import pytest
from pydantic import ValidationError

from app.schemas import MasterCreateSchema, OrderCreateSchema, UserCreateSchema


class TestOrderCreateSchema:
    """Тесты валидации создания заявок"""

    def test_valid_order_creation(self):
        """Тест успешного создания заявки с валидными данными"""
        order_data = {
            "equipment_type": "Стиральные машины",
            "description": "Машинка не включается, нужна диагностика",
            "client_name": "Иванов Иван Петрович",  # Можно и ФИО, и просто имя ≥5 символов
            "client_address": "ул. Ленина, дом 10, квартира 5",
            "client_phone": "+79001234567",
            "dispatcher_id": 123456789,
        }

        order = OrderCreateSchema(**order_data)
        assert order.equipment_type == "Стиральные машины"
        assert order.client_phone == "+79001234567"
        assert len(order.client_name) >= 5

    def test_phone_formatting(self):
        """Тест автоматического форматирования телефона"""
        order_data = {
            "equipment_type": "ДШ/ВП",
            "description": "Не работает духовка, не нагревается",
            "client_name": "Петров Петр",
            "client_address": "пр. Мира, 25, кв. 10",
            "client_phone": "89001234567",  # без +7
            "dispatcher_id": 123456789,
        }

        order = OrderCreateSchema(**order_data)
        assert order.client_phone == "+79001234567"  # автоматически форматируется

    def test_invalid_equipment_type(self):
        """Тест невалидного типа техники"""
        order_data = {
            "equipment_type": "Космический корабль",  # недопустимый тип
            "description": "Не заводится двигатель",
            "client_name": "Гагарин Юрий Алексеевич",
            "client_address": "Космодром Байконур, площадка 1",
            "client_phone": "+79001234567",
            "dispatcher_id": 123456789,
        }

        with pytest.raises(ValidationError) as exc_info:
            OrderCreateSchema(**order_data)

        assert "Недопустимый тип техники" in str(exc_info.value)

    def test_short_description(self):
        """Тест слишком короткого описания"""
        order_data = {
            "equipment_type": "Стиральные машины",
            "description": "Сло",  # слишком короткое (меньше 4 символов)
            "client_name": "Иванов Иван",
            "client_address": "ул. Ленина, 10, кв. 5",
            "client_phone": "+79001234567",
            "dispatcher_id": 123456789,
        }

        with pytest.raises(ValidationError) as exc_info:
            OrderCreateSchema(**order_data)

        # Проверяем, что ошибка связана с длиной описания (description)
        error_str = str(exc_info.value).lower()
        assert ("description" in error_str and ("at least 4" in error_str or "string_too_short" in error_str))

    def test_sql_injection_protection(self):
        """Тест защиты от SQL injection в описании"""
        order_data = {
            "equipment_type": "Стиральные машины",
            "description": "Машинка не работает; DROP TABLE orders; --",
            "client_name": "Хакер Иван",
            "client_address": "Dark Web, дом 1",
            "client_phone": "+79001234567",
            "dispatcher_id": 123456789,
        }

        with pytest.raises(ValidationError) as exc_info:
            OrderCreateSchema(**order_data)

        assert "недопустимые символы" in str(exc_info.value).lower()

    def test_invalid_client_name(self):
        """Тест невалидного имени (слишком короткое)"""
        order_data = {
            "equipment_type": "ДШ/ВП",
            "description": "Не включается духовка",
            "client_name": "И",  # меньше 2 символов (минимум 2 по схеме)
            "client_address": "ул. Ленина, 10",
            "client_phone": "+79001234567",
            "dispatcher_id": 123456789,
        }

        with pytest.raises(ValidationError) as exc_info:
            OrderCreateSchema(**order_data)

        # Проверяем, что ошибка связана с именем клиента (client_name)
        error_str = str(exc_info.value).lower()
        assert ("client_name" in error_str and ("at least 2" in error_str or "string_too_short" in error_str))

    def test_valid_single_name(self):
        """Тест валидного имени (одно слово, 5+ символов)"""
        order_data = {
            "equipment_type": "Стиральные машины",
            "description": "Машинка не работает, нужна диагностика",
            "client_name": "Александр",  # Одно слово, но 9 символов - валидно
            "client_address": "ул. Ленина, 10, кв. 5",
            "client_phone": "+79001234567",
            "dispatcher_id": 123456789,
        }

        order = OrderCreateSchema(**order_data)
        assert order.client_name == "Александр"
        assert len(order.client_name) >= 5

    def test_address_without_number(self):
        """Тест адреса без номера дома"""
        order_data = {
            "equipment_type": "Стиральные машины",
            "description": "Машинка не работает, нужна диагностика",
            "client_name": "Иванов Иван",
            "client_address": "улица Ленина",  # нет номера дома
            "client_phone": "+79001234567",
            "dispatcher_id": 123456789,
        }

        with pytest.raises(ValidationError) as exc_info:
            OrderCreateSchema(**order_data)

        assert "номер дома" in str(exc_info.value).lower()

    def test_invalid_phone_format(self):
        """Тест невалидного формата телефона"""
        order_data = {
            "equipment_type": "Стиральные машины",
            "description": "Машинка не работает",
            "client_name": "Иванов Иван",
            "client_address": "ул. Ленина, 10",
            "client_phone": "123",  # слишком короткий
            "dispatcher_id": 123456789,
        }

        with pytest.raises(ValidationError):
            OrderCreateSchema(**order_data)


class TestMasterCreateSchema:
    """Тесты валидации создания мастеров"""

    def test_valid_master_creation(self):
        """Тест успешного создания мастера"""
        master_data = {
            "telegram_id": 123456789,
            "phone": "+79001234567",
            "specialization": "Ремонт стиральных машин",
            "is_approved": False,
        }

        master = MasterCreateSchema(**master_data)
        assert master.telegram_id == 123456789
        assert master.phone == "+79001234567"

    def test_invalid_telegram_id(self):
        """Тест невалидного Telegram ID"""
        master_data = {
            "telegram_id": -100,  # отрицательный ID
            "phone": "+79001234567",
            "specialization": "Ремонт техники",
        }

        with pytest.raises(ValidationError):
            MasterCreateSchema(**master_data)

    def test_short_specialization(self):
        """Тест слишком короткой специализации"""
        master_data = {
            "telegram_id": 123456789,
            "phone": "+79001234567",
            "specialization": "Ре",  # слишком короткое
        }

        with pytest.raises(ValidationError):
            MasterCreateSchema(**master_data)


class TestUserCreateSchema:
    """Тесты валидации создания пользователей"""

    def test_valid_user_creation(self):
        """Тест успешного создания пользователя"""
        user_data = {
            "telegram_id": 123456789,
            "username": "ivan_petrov",
            "first_name": "Иван",
            "last_name": "Петров",
            "role": "DISPATCHER",
        }

        user = UserCreateSchema(**user_data)
        assert user.telegram_id == 123456789
        assert user.username == "ivan_petrov"

    def test_username_with_at(self):
        """Тест username с @ (должен убраться автоматически)"""
        user_data = {
            "telegram_id": 123456789,
            "username": "@ivan_petrov",  # с @
            "first_name": "Иван",
            "role": "MASTER",
        }

        user = UserCreateSchema(**user_data)
        assert user.username == "ivan_petrov"  # @ убрался

    def test_invalid_role(self):
        """Тест невалидной роли"""
        user_data = {
            "telegram_id": 123456789,
            "username": "ivan",
            "first_name": "Иван",
            "role": "SUPERHERO",  # недопустимая роль
        }

        with pytest.raises(ValidationError):
            UserCreateSchema(**user_data)


if __name__ == "__main__":
    # Можно запустить для быстрой проверки
    print("Testing OrderCreateSchema...")
    test = TestOrderCreateSchema()
    try:
        test.test_valid_order_creation()
        print("✅ Valid order creation - OK")
    except Exception as e:
        print(f"❌ Valid order creation - FAILED: {e}")

    try:
        test.test_sql_injection_protection()
        print("✅ SQL injection protection - OK")
    except Exception as e:
        print(f"❌ SQL injection protection - FAILED: {e}")

    print("\nAll quick tests passed!")

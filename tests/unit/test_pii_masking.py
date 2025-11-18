"""
Тесты для утилит маскирования персональных данных (PII)
"""

from app.utils.pii_masking import (
    mask_address,
    mask_dict,
    mask_name,
    mask_phone,
    mask_username,
    safe_log_order_details,
    safe_str_order,
    safe_str_user,
    sanitize_log_message,
)


class TestMaskPhone:
    """Тесты маскирования телефонов"""

    def test_mask_russian_phone_with_plus(self):
        """Маскирование российского номера с +"""
        assert mask_phone("+79991234567") == "+7****4567"

    def test_mask_russian_phone_without_plus(self):
        """Маскирование российского номера без +"""
        assert mask_phone("89991234567") == "89****4567"

    def test_mask_phone_with_formatting(self):
        """Маскирование форматированного номера"""
        result = mask_phone("+7 (999) 123-45-67")
        assert result == "+7****4567"

    def test_mask_short_phone(self):
        """Маскирование короткого номера"""
        assert mask_phone("123") == "****"

    def test_mask_none_phone(self):
        """Маскирование None"""
        assert mask_phone(None) == "[no phone]"

    def test_mask_empty_phone(self):
        """Маскирование пустой строки"""
        assert mask_phone("") == "[no phone]"


class TestMaskName:
    """Тесты маскирования имен"""

    def test_mask_full_name(self):
        """Маскирование полного имени"""
        assert mask_name("Иванов Иван Петрович") == "И***в И***н П***ч"

    def test_mask_short_name(self):
        """Маскирование короткого имени"""
        assert mask_name("Петров") == "П***в"

    def test_mask_single_letter(self):
        """Маскирование одной буквы"""
        assert mask_name("А") == "*"

    def test_mask_two_letters(self):
        """Маскирование двух букв"""
        assert mask_name("Ли") == "Л*"

    def test_mask_none_name(self):
        """Маскирование None"""
        assert mask_name(None) == "[no name]"

    def test_mask_empty_name(self):
        """Маскирование пустой строки"""
        assert mask_name("") == "[no name]"


class TestMaskAddress:
    """Тесты маскирования адресов"""

    def test_mask_full_address(self):
        """Маскирование полного адреса"""
        result = mask_address("Москва, ул. Ленина, д. 10, кв. 5")
        assert result.startswith("Москва, ")
        assert "..." in result

    def test_mask_city_only(self):
        """Маскирование только города"""
        assert mask_address("Москва") == "Москва..."

    def test_mask_none_address(self):
        """Маскирование None"""
        assert mask_address(None) == "[no address]"

    def test_mask_empty_address(self):
        """Маскирование пустой строки"""
        assert mask_address("") == "[no address]"


class TestMaskUsername:
    """Тесты маскирования username"""

    def test_mask_regular_username(self):
        """Маскирование обычного username"""
        assert mask_username("john_doe") == "j***e"

    def test_mask_short_username(self):
        """Маскирование короткого username"""
        assert mask_username("ab") == "**"

    def test_mask_single_char_username(self):
        """Маскирование одного символа"""
        assert mask_username("a") == "*"

    def test_mask_none_username(self):
        """Маскирование None"""
        assert mask_username(None) == "[no username]"


class TestSafeStrUser:
    """Тесты безопасного представления User"""

    def test_safe_str_user_with_dict(self):
        """Безопасное представление User как словаря"""
        user = {"telegram_id": 123456, "role": "DISPATCHER"}
        result = safe_str_user(user)
        assert "123456" in result
        assert "DISPATCHER" in result
        assert "User(" in result

    def test_safe_str_user_with_object(self):
        """Безопасное представление User как объекта"""

        class MockUser:
            telegram_id = 123456
            role = "MASTER"

        result = safe_str_user(MockUser())
        assert "123456" in result
        assert "MASTER" in result

    def test_safe_str_user_none(self):
        """Безопасное представление None"""
        assert safe_str_user(None) == "[no user]"


class TestSafeStrOrder:
    """Тесты безопасного представления Order"""

    def test_safe_str_order_with_dict(self):
        """Безопасное представление Order как словаря"""
        order = {
            "id": 1,
            "status": "ASSIGNED",
            "equipment_type": "Холодильник",
            "assigned_master_id": 5,
        }
        result = safe_str_order(order)
        assert "#1" in result
        assert "ASSIGNED" in result
        assert "Холодильник" in result
        assert "master=5" in result

    def test_safe_str_order_with_object(self):
        """Безопасное представление Order как объекта"""

        class MockOrder:
            id = 1
            status = "NEW"
            equipment_type = "Стиральная машина"
            assigned_master_id = None

        result = safe_str_order(MockOrder())
        assert "#1" in result
        assert "NEW" in result
        assert "Стиральная машина" in result

    def test_safe_str_order_none(self):
        """Безопасное представление None"""
        assert safe_str_order(None) == "[no order]"


class TestSafeLogOrderDetails:
    """Тесты детального логирования Order"""

    def test_safe_log_without_client_info(self):
        """Логирование без информации о клиенте"""

        class MockOrder:
            id = 1
            status = "ASSIGNED"
            equipment_type = "Холодильник"
            assigned_master_id = 5

        result = safe_log_order_details(MockOrder(), show_client_info=False)
        assert "#1" in result
        assert "ASSIGNED" in result
        # Не должно быть данных клиента
        assert "Client:" not in result

    def test_safe_log_with_masked_client_info(self):
        """Логирование с маскированной информацией о клиенте"""

        class MockOrder:
            id = 1
            status = "ASSIGNED"
            equipment_type = "Холодильник"
            assigned_master_id = 5
            client_name = "Иванов Иван"
            client_phone = "+79991234567"
            client_address = "Москва, ул. Ленина, 10"

        result = safe_log_order_details(MockOrder(), show_client_info=True)
        assert "#1" in result
        # Должны быть маскированные данные
        assert "Client:" in result
        assert "И***в" in result
        assert "****4567" in result
        assert "Москва" in result


class TestSanitizeLogMessage:
    """Тесты очистки сообщений логов от PII"""

    def test_sanitize_phone_with_plus(self):
        """Удаление телефона с +"""
        message = "Client phone: +79991234567"
        result = sanitize_log_message(message)
        assert "+79991234567" not in result
        assert "[PHONE]" in result

    def test_sanitize_phone_without_plus(self):
        """Удаление телефона без +"""
        message = "Contact: 89991234567"
        result = sanitize_log_message(message)
        assert "89991234567" not in result
        assert "[PHONE]" in result

    def test_sanitize_email(self):
        """Удаление email"""
        message = "User email: john.doe@example.com"
        result = sanitize_log_message(message)
        assert "john.doe@example.com" not in result
        assert "[EMAIL]" in result

    def test_sanitize_multiple_pii(self):
        """Удаление нескольких PII"""
        message = "Contact: +79991234567, email: test@mail.ru"
        result = sanitize_log_message(message)
        assert "+79991234567" not in result
        assert "test@mail.ru" not in result
        assert "[PHONE]" in result
        assert "[EMAIL]" in result


class TestMaskDict:
    """Тесты маскирования словарей"""

    def test_mask_dict_with_pii(self):
        """Маскирование словаря с PII"""
        data = {
            "id": 1,
            "client_name": "Иванов Иван",
            "client_phone": "+79991234567",
            "client_address": "Москва, ул. Ленина, 10",
            "username": "john_doe",
            "status": "NEW",
        }
        masked = mask_dict(data)

        # ID и status остаются
        assert masked["id"] == 1
        assert masked["status"] == "NEW"

        # PII маскируются
        assert masked["client_name"] != "Иванов Иван"
        assert "***" in masked["client_name"]
        assert masked["client_phone"] != "+79991234567"
        assert "****" in masked["client_phone"]
        assert masked["client_address"] != "Москва, ул. Ленина, 10"
        assert masked["username"] != "john_doe"

    def test_mask_dict_without_pii(self):
        """Маскирование словаря без PII"""
        data = {"id": 1, "status": "NEW", "total_amount": 1000}
        masked = mask_dict(data)

        # Все остается как есть
        assert masked == data

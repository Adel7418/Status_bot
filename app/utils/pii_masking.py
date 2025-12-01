"""
Утилиты для маскирования персональных данных (PII) в логах
Соответствие GDPR, 152-ФЗ, ISO 27001

Маскируются:
- Телефоны клиентов
- Имена клиентов
- Адреса клиентов
- Username пользователей Telegram
- Другие чувствительные данные
"""

import re
from typing import Any


def mask_phone(phone: str | None) -> str:
    """
    Маскирует телефонный номер

    Примеры:
        +79991234567 → +7****4567
        89991234567 → 8****4567
        +7 (999) 123-45-67 → +7****67

    Args:
        phone: Телефонный номер

    Returns:
        Маскированный номер
    """
    if not phone:
        return "[no phone]"

    # Удаляем все нецифровые символы кроме +
    clean_phone = re.sub(r"[^\d+]", "", phone)

    # Если номер слишком короткий
    if len(clean_phone) < 5:
        return "****"

    # Показываем первые 2 символа (код страны) и последние 4 цифры
    prefix = clean_phone[:2]
    suffix = clean_phone[-4:]

    return f"{prefix}****{suffix}"


def mask_name(name: str | None) -> str:
    """
    Маскирует имя клиента

    Примеры:
        Иванов Иван → И***в И***
        Петров → П***в
        А → *

    Args:
        name: Имя клиента

    Returns:
        Маскированное имя
    """
    if not name:
        return "[no name]"

    # Разбиваем на части (ФИО)
    parts = name.strip().split()
    masked_parts = []

    for part in parts:
        if len(part) <= 1:
            masked_parts.append("*")
        elif len(part) == 2:
            masked_parts.append(f"{part[0]}*")
        else:
            # Показываем первую и последнюю букву
            masked_parts.append(f"{part[0]}***{part[-1]}")

    return " ".join(masked_parts)


def mask_address(address: str | None) -> str:
    """
    Маскирует адрес клиента

    Примеры:
        Москва, ул. Ленина, д. 10, кв. 5 → Москва, ул. Л***...
        Санкт-Петербург, Невский пр. 100 → Санкт-Петербург...

    Args:
        address: Адрес клиента

    Returns:
        Маскированный адрес (город + начало улицы)
    """
    if not address:
        return "[no address]"

    # Разбиваем по запятой
    parts = address.split(",")

    if len(parts) == 0:
        return "***"

    # Показываем только город (первую часть)
    city = parts[0].strip()

    if len(parts) > 1:
        # Показываем начало второй части (улицы)
        street_start = parts[1].strip()[:8]
        return f"{city}, {street_start}..."

    return f"{city}..."


def mask_username(username: str | None) -> str:
    """
    Маскирует Telegram username

    Примеры:
        john_doe → j***e
        a → *
        None → [no username]

    Args:
        username: Telegram username

    Returns:
        Маскированный username
    """
    if not username:
        return "[no username]"

    if len(username) <= 2:
        return "*" * len(username)

    return f"{username[0]}***{username[-1]}"


def mask_telegram_id(telegram_id: int | None) -> str:
    """
    Маскирует Telegram ID (оставляем как есть для отладки)

    Note: Telegram ID не является PII по GDPR, но можем маскировать для параноидов

    Args:
        telegram_id: Telegram user ID

    Returns:
        ID или маска
    """
    if not telegram_id:
        return "[no id]"

    # Для Telegram ID обычно не маскируем, но можно включить если нужно
    return str(telegram_id)


def safe_str_user(user: Any) -> str:
    """
    Безопасное строковое представление User объекта для логов

    Args:
        user: User объект (из app.database.models)

    Returns:
        Безопасная строка без PII
    """
    if not user:
        return "[no user]"

    # Если это словарь
    if isinstance(user, dict):
        user_id = user.get("telegram_id", user.get("id", "?"))
        role = user.get("role", "UNKNOWN")
        return f"User(id={user_id}, role={role})"

    # Если это объект User
    try:
        user_id = getattr(user, "telegram_id", getattr(user, "id", "?"))
        role = getattr(user, "role", "UNKNOWN")
        return f"User(id={user_id}, role={role})"
    except Exception:
        return "[user object]"


def safe_str_order(order: Any) -> str:
    """
    Безопасное строковое представление Order объекта для логов

    Args:
        order: Order объект (из app.database.models)

    Returns:
        Безопасная строка без PII клиента
    """
    if not order:
        return "[no order]"

    # Если это словарь
    if isinstance(order, dict):
        order_id = order.get("id", "?")
        status = order.get("status", "UNKNOWN")
        equipment = order.get("equipment_type", "Unknown")
        master_id = order.get("assigned_master_id", "Unassigned")
        return f"Order(#{order_id}, {status}, {equipment}, master={master_id})"

    # Если это объект Order
    try:
        order_id = getattr(order, "id", "?")
        status = getattr(order, "status", "UNKNOWN")
        equipment = getattr(order, "equipment_type", "Unknown")
        master_id = getattr(order, "assigned_master_id", "Unassigned")
        return f"Order(#{order_id}, {status}, {equipment}, master={master_id})"
    except Exception:
        return "[order object]"


def safe_log_order_details(order: Any, show_client_info: bool = False) -> str:
    """
    Подробная информация о заказе для логов (опционально с маскированными данными клиента)

    Args:
        order: Order объект
        show_client_info: Показать маскированные данные клиента

    Returns:
        Детальная информация о заказе
    """
    if not order:
        return "[no order]"

    base_info = safe_str_order(order)

    if not show_client_info:
        return base_info

    # Добавляем маскированные данные клиента
    try:
        client_name = mask_name(getattr(order, "client_name", None))
        client_phone = mask_phone(getattr(order, "client_phone", None))
        client_address = mask_address(getattr(order, "client_address", None))

        return (
            f"{base_info} | "
            f"Client: {client_name} | "
            f"Phone: {client_phone} | "
            f"Address: {client_address}"
        )
    except Exception:
        return base_info


def sanitize_log_message(message: str) -> str:
    """
    Очищает строку лога от возможных PII используя регулярные выражения

    Паттерны:
    - Телефоны: +7XXXXXXXXXX, 8XXXXXXXXXX
    - Email: xxx@xxx.xxx
    - Пароли: слова длиннее 8 символов с буквами и цифрами

    Args:
        message: Исходное сообщение

    Returns:
        Очищенное сообщение
    """
    # Маскируем телефоны
    message = re.sub(
        r"\+?[78][\s\-\(\)]?\d{3}[\s\-\(\)]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}", "[PHONE]", message
    )

    # Маскируем email
    message = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL]", message)
    
    # Маскируем возможные пароли (8+ символов с буквами и цифрами)
    # Паттерн: слово содержит как минимум одну букву и одну цифру, длина 8+
    message = re.sub(r"\b(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d@$!%*?&]{8,}\b", "[REDACTED]", message)
    
    return message


# Константы для удобства
NO_PII_FIELDS = {
    "id",
    "order_id",
    "telegram_id",
    "status",
    "equipment_type",
    "created_at",
    "updated_at",
    "is_active",
    "is_approved",
    "total_amount",
    "materials_cost",
    "master_profit",
    "company_profit",
}

PII_FIELDS = {
    "client_name",
    "client_phone",
    "client_address",
    "username",
    "first_name",
    "last_name",
    "phone",
}


def mask_dict(data: dict[str, Any]) -> dict[str, Any]:
    """
    Маскирует PII поля в словаре

    Args:
        data: Словарь с данными

    Returns:
        Словарь с маскированными PII
    """
    masked = data.copy()

    for key, value in masked.items():
        if key in PII_FIELDS and value:
            if "phone" in key.lower():
                masked[key] = mask_phone(str(value))
            elif "name" in key.lower():
                masked[key] = mask_name(str(value))
            elif "address" in key.lower():
                masked[key] = mask_address(str(value))
            elif "username" in key.lower():
                masked[key] = mask_username(str(value))

    return masked

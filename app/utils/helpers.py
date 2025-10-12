"""
Вспомогательные функции
"""

import logging
import re
from datetime import datetime

# Импорт retry механизма
from app.utils.retry import (
    retry_on_telegram_error,
    safe_answer_callback,
    safe_delete_message,
    safe_edit_message,
    safe_send_message,
)


logger = logging.getLogger(__name__)


def validate_phone(phone: str) -> bool:
    """
    Валидация номера телефона

    Args:
        phone: Номер телефона

    Returns:
        True если номер валиден, иначе False
    """
    # Очищаем номер от всех символов кроме цифр и +
    cleaned = re.sub(r"[^\d+]", "", phone.strip())

    # Проверяем основные форматы
    patterns = [
        r"^\+7\d{10}$",  # +79001234567
        r"^8\d{10}$",  # 89001234567
        r"^7\d{10}$",  # 79001234567
    ]

    return any(re.match(pattern, cleaned) for pattern in patterns)


def format_phone(phone: str) -> str:
    """
    Форматирование номера телефона

    Args:
        phone: Номер телефона

    Returns:
        Отформатированный номер
    """
    # Удаляем все символы кроме цифр и +
    cleaned = re.sub(r"[^\d+]", "", phone.strip())

    # Если номер начинается с 8, заменяем на +7
    if cleaned.startswith("8") and len(cleaned) == 11:
        cleaned = "+7" + cleaned[1:]
    elif (cleaned.startswith("7") and len(cleaned) == 11) or not cleaned.startswith("+"):
        cleaned = "+" + cleaned

    return cleaned


def format_datetime(dt: datetime) -> str:
    """
    Форматирование даты и времени

    Args:
        dt: Объект datetime

    Returns:
        Строка с датой и временем
    """
    return dt.strftime("%d.%m.%Y %H:%M")


def format_date(dt: datetime) -> str:
    """
    Форматирование даты

    Args:
        dt: Объект datetime

    Returns:
        Строка с датой
    """
    return dt.strftime("%d.%m.%Y")


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Обрезка текста до определенной длины

    Args:
        text: Исходный текст
        max_length: Максимальная длина
        suffix: Суффикс для обрезанного текста

    Returns:
        Обрезанный текст
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def escape_markdown(text: str) -> str:
    """
    Экранирование специальных символов для Markdown

    Args:
        text: Исходный текст

    Returns:
        Экранированный текст
    """
    special_chars = [
        "_",
        "*",
        "[",
        "]",
        "(",
        ")",
        "~",
        "`",
        ">",
        "#",
        "+",
        "-",
        "=",
        "|",
        "{",
        "}",
        ".",
        "!",
    ]
    for char in special_chars:
        text = text.replace(char, "\\" + char)
    return text


def get_user_display_name(
    first_name: str | None = None,
    last_name: str | None = None,
    username: str | None = None,
    telegram_id: int | None = None,
) -> str:
    """
    Получение отображаемого имени пользователя

    Args:
        first_name: Имя
        last_name: Фамилия
        username: Username
        telegram_id: Telegram ID

    Returns:
        Отображаемое имя
    """
    if first_name and last_name:
        return f"{first_name} {last_name}"
    if first_name:
        return first_name
    if username:
        return f"@{username}"
    if telegram_id:
        return f"ID: {telegram_id}"
    return "Неизвестный пользователь"


def parse_callback_data(callback_data: str) -> dict:
    """
    Парсинг callback data

    Args:
        callback_data: Строка callback data (формат: action:param1:param2)

    Returns:
        Словарь с распарсенными данными
    """
    parts = callback_data.split(":")
    return {
        "action": parts[0] if len(parts) > 0 else None,
        "params": parts[1:] if len(parts) > 1 else [],
    }


def create_callback_data(action: str, *params) -> str:
    """
    Создание callback data

    Args:
        action: Действие
        *params: Параметры

    Returns:
        Строка callback data
    """
    return ":".join([action] + [str(p) for p in params])


def log_action(user_id: int, action: str, details: str | None = None):
    """
    Логирование действия пользователя

    Args:
        user_id: ID пользователя
        action: Действие
        details: Детали действия
    """
    log_msg = f"User {user_id} - {action}"
    if details:
        log_msg += f" - {details}"
    logger.info(log_msg)


def calculate_profit_split(
    total_amount: float, materials_cost: float, has_review: bool = False
) -> tuple[float, float]:
    """
    Расчет распределения прибыли между мастером и компанией

    Правила:
    - Чистая прибыль >= 7000: 50% мастеру, 50% компании
    - Чистая прибыль < 7000: 40% мастеру, 60% компании
    - Если взят отзыв: +10% от чистой прибыли мастеру (вычитается из прибыли компании)

    Args:
        total_amount: Общая сумма заказа
        materials_cost: Сумма расходного материала
        has_review: Взял ли мастер отзыв у клиента

    Returns:
        Кортеж (прибыль мастера, прибыль компании)
    """
    # Чистая прибыль
    net_profit = total_amount - materials_cost

    # Определяем процент в зависимости от суммы
    if net_profit >= 7000:
        # 50/50
        master_profit = net_profit * 0.5
        company_profit = net_profit * 0.5
    else:
        # 40/60
        master_profit = net_profit * 0.4
        company_profit = net_profit * 0.6

    # Если взят отзыв - добавляем 10% к прибыли мастера
    if has_review:
        review_bonus = net_profit * 0.1
        master_profit += review_bonus
        company_profit -= review_bonus

    return (master_profit, company_profit)

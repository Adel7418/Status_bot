"""
Вспомогательные функции
"""
import re
import logging
from datetime import datetime
from typing import Optional
from app.config import PHONE_REGEX

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
    cleaned = re.sub(r'[^\d+]', '', phone.strip())
    
    # Проверяем основные форматы
    patterns = [
        r'^\+7\d{10}$',  # +79001234567
        r'^8\d{10}$',    # 89001234567
        r'^7\d{10}$'     # 79001234567
    ]
    
    for pattern in patterns:
        if re.match(pattern, cleaned):
            return True
    
    return False


def format_phone(phone: str) -> str:
    """
    Форматирование номера телефона
    
    Args:
        phone: Номер телефона
        
    Returns:
        Отформатированный номер
    """
    # Удаляем все символы кроме цифр и +
    cleaned = re.sub(r'[^\d+]', '', phone.strip())
    
    # Если номер начинается с 8, заменяем на +7
    if cleaned.startswith('8') and len(cleaned) == 11:
        cleaned = '+7' + cleaned[1:]
    elif cleaned.startswith('7') and len(cleaned) == 11:
        cleaned = '+' + cleaned
    elif not cleaned.startswith('+'):
        cleaned = '+' + cleaned
    
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
    return text[:max_length - len(suffix)] + suffix


def escape_markdown(text: str) -> str:
    """
    Экранирование специальных символов для Markdown
    
    Args:
        text: Исходный текст
        
    Returns:
        Экранированный текст
    """
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, '\\' + char)
    return text


def get_user_display_name(
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    username: Optional[str] = None,
    telegram_id: Optional[int] = None
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
    elif first_name:
        return first_name
    elif username:
        return f"@{username}"
    elif telegram_id:
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
        "params": parts[1:] if len(parts) > 1 else []
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


def log_action(user_id: int, action: str, details: Optional[str] = None):
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


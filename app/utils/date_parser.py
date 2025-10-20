"""
Утилита для парсинга дат из естественного языка на русском
"""

import logging
from datetime import datetime

import dateparser  # type: ignore[import-untyped]

from app.utils.helpers import MOSCOW_TZ, get_now


logger = logging.getLogger(__name__)


def parse_natural_datetime(text: str) -> tuple[datetime | None, str]:
    """
    Парсинг даты/времени из естественного языка на русском

    Args:
        text: Текст с датой/временем (например "завтра в 10:00", "через 2 дня 15:30")

    Returns:
        Кортеж (datetime объект с московским часовым поясом, исходный текст)
        Если распарсить не удалось - (None, исходный текст)

    Examples:
        >>> parse_natural_datetime("завтра в 10:00")
        (datetime(2025, 10, 21, 10, 0, tzinfo=MOSCOW_TZ), "завтра в 10:00")

        >>> parse_natural_datetime("через 2 дня 14:30")
        (datetime(2025, 10, 22, 14, 30, tzinfo=MOSCOW_TZ), "через 2 дня 14:30")

        >>> parse_natural_datetime("Набрать клиенту")
        (None, "Набрать клиенту")
    """
    if not text or not text.strip():
        return None, text

    text = text.strip()

    # Настройки для dateparser
    settings = {
        "TIMEZONE": "Europe/Moscow",
        "RETURN_AS_TIMEZONE_AWARE": True,
        "PREFER_DATES_FROM": "future",  # Предпочитаем будущие даты
        "RELATIVE_BASE": get_now().replace(tzinfo=MOSCOW_TZ),
    }

    # Пытаемся распарсить дату
    try:
        parsed_date = dateparser.parse(
            text,
            languages=["ru", "en"],  # Поддержка русского и английского
            settings=settings,
        )

        if parsed_date:
            # Убедимся что есть timezone
            if parsed_date.tzinfo is None:
                parsed_date = parsed_date.replace(tzinfo=MOSCOW_TZ)

            logger.info(f"Успешно распознана дата: '{text}' -> {parsed_date}")
            return parsed_date, text

    except Exception as e:
        logger.debug(f"Не удалось распарсить дату '{text}': {e}")

    # Если не смогли распарсить - возвращаем None
    return None, text


def format_datetime_for_storage(dt: datetime | None, original_text: str) -> str:
    """
    Форматирование datetime для сохранения в БД

    Args:
        dt: Распарсенный datetime
        original_text: Исходный текст

    Returns:
        Строка для сохранения в БД

    Examples:
        >>> format_datetime_for_storage(datetime(2025, 10, 21, 10, 0), "завтра в 10:00")
        "21.10.2025 10:00 (завтра в 10:00)"

        >>> format_datetime_for_storage(None, "Набрать клиенту")
        "Набрать клиенту"
    """
    if dt is None:
        return original_text

    # Форматируем дату в удобный формат
    formatted = dt.strftime("%d.%m.%Y %H:%M")

    # Если исходный текст короткий и похож на время - не дублируем
    if len(original_text) < 20 and any(
        keyword in original_text.lower()
        for keyword in ["завтра", "послезавтра", "через", "сегодня"]
    ):
        return f"{formatted} ({original_text})"

    return formatted


def format_datetime_user_friendly(dt: datetime | None, original_text: str) -> str:
    """
    Форматирование datetime для отображения пользователю

    Args:
        dt: Распарсенный datetime
        original_text: Исходный текст

    Returns:
        Строка для отображения

    Examples:
        >>> format_datetime_user_friendly(datetime(2025, 10, 21, 10, 0), "завтра в 10:00")
        "завтра в 10:00 → 21.10.2025 10:00"
    """
    if dt is None:
        return original_text

    formatted = dt.strftime("%d.%m.%Y %H:%M")

    # Показываем пользователю что мы поняли
    return f"{original_text} → {formatted}"


def should_parse_as_date(text: str) -> bool:
    """
    Проверка, нужно ли пытаться парсить текст как дату

    Args:
        text: Входной текст

    Returns:
        True если текст похож на дату/время

    Examples:
        >>> should_parse_as_date("завтра в 10:00")
        True

        >>> should_parse_as_date("Набрать клиенту")
        False
    """
    if not text or not text.strip():
        return False

    text_lower = text.lower()

    # Ключевые слова для дат/времени
    date_keywords = [
        "завтра",
        "послезавтра",
        "через",
        "сегодня",
        "в",
        ":",  # Время 10:00
        ".",  # Дата 15.10.2025
        "/",  # Дата 15/10/2025
        "-",  # Дата 15-10-2025
        "неделю",
        "месяц",
        "дня",
        "день",
        "часа",
        "час",
        "минут",
    ]

    # Если есть хотя бы одно ключевое слово или цифры - пытаемся парсить
    return any(keyword in text_lower for keyword in date_keywords) or any(
        char.isdigit() for char in text
    )

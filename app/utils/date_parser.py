"""
Утилита для парсинга дат из естественного языка на русском
"""

import logging
import re
from datetime import datetime, timedelta

import dateparser  # type: ignore[import-untyped]

from app.utils.helpers import MOSCOW_TZ, get_now


logger = logging.getLogger(__name__)


def _preprocess_time_text(text: str) -> str:
    """
    Предобработка текста для лучшего распознавания времени

    Args:
        text: Исходный текст

    Returns:
        Обработанный текст

    Examples:
        >>> _preprocess_time_text("через час")
        "через 1 час"

        >>> _preprocess_time_text("через полтора часа")
        "через 1.5 часа"

        >>> _preprocess_time_text("через 1-1.5 часа")
        "через 1.25 часа"

        >>> _preprocess_time_text("через полчаса")
        "через 30 минут"
    """
    text_lower = text.lower()

    # Замена "через час" на "через 1 час"
    text_lower = re.sub(r"\bчерез\s+час\b", "через 1 час", text_lower)

    # Замена "полчаса" на "30 минут"
    text_lower = re.sub(r"\bполчаса\b", "30 минут", text_lower)

    # Замена "полтора" на "1.5"
    text_lower = re.sub(r"\bполтора\b", "1.5", text_lower)

    # Замена "два с половиной" на "2.5"
    text_lower = re.sub(r"\bдва\s+с\s+половиной\b", "2.5", text_lower)
    text_lower = re.sub(r"\bтри\s+с\s+половиной\b", "3.5", text_lower)

    # Замена диапазонов типа "1-1.5" на среднее значение "1.25"
    # Паттерн: "1-1.5", "2-3" и т.д.
    # Важно: НЕ заменяем даты типа "20-10-2025"
    range_pattern = r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*(?:час|дн|мин)"
    matches = list(re.finditer(range_pattern, text_lower))
    for match in matches:
        start = float(match.group(1))
        end = float(match.group(2))
        average = (start + end) / 2
        # Заменяем только диапазон чисел, оставляем единицы измерения
        old_range = f"{match.group(1)}-{match.group(2)}"
        new_value = str(average)
        text_lower = text_lower.replace(old_range, new_value, 1)

    return text_lower


def validate_parsed_datetime(dt: datetime, original_text: str) -> dict[str, str | bool]:
    """
    Валидация распарсенной даты/времени

    Args:
        dt: Распарсенная дата
        original_text: Исходный текст

    Returns:
        Словарь с результатом валидации:
        {
            "is_valid": bool,
            "error": str | None,
            "warning": str | None
        }
    """
    now = get_now().replace(tzinfo=MOSCOW_TZ)

    # 1. Проверка: дата не в прошлом (с учетом погрешности 5 минут)
    if dt < (now - timedelta(minutes=5)):
        return {
            "is_valid": False,
            "error": f"Дата в прошлом: {dt.strftime('%d.%m.%Y %H:%M')}",
            "warning": None,
        }

    # 2. Проверка: дата не слишком далеко в будущем (макс 1 год)
    max_future = now + timedelta(days=365)
    if dt > max_future:
        return {
            "is_valid": False,
            "error": f"Дата слишком далеко в будущем (>1 года): {dt.strftime('%d.%m.%Y %H:%M')}",
            "warning": None,
        }

    # 3. Проверка: для коротких интервалов (< 24 часов) предупреждение если слишком скоро
    time_until = dt - now
    if time_until < timedelta(minutes=30):
        return {
            "is_valid": True,
            "error": None,
            "warning": f"Очень скоро: через {int(time_until.total_seconds() / 60)} минут",
        }

    # 4. Все хорошо
    return {"is_valid": True, "error": None, "warning": None}


def parse_natural_datetime(text: str, validate: bool = True) -> tuple[datetime | None, str]:
    """
    Парсинг даты/времени из естественного языка на русском

    Args:
        text: Текст с датой/временем (например "завтра в 10:00", "через 2 часа")
        validate: Валидировать распарсенное время (не в прошлом, не слишком далеко)

    Returns:
        Кортеж (datetime объект с московским часовым поясом, исходный текст)
        Если распарсить не удалось - (None, исходный текст)

    Examples:
        >>> parse_natural_datetime("завтра в 10:00")
        (datetime(2025, 10, 21, 10, 0, tzinfo=MOSCOW_TZ), "завтра в 10:00")

        >>> parse_natural_datetime("через 2 часа")
        (datetime(2025, 10, 21, 2, 30, tzinfo=MOSCOW_TZ), "через 2 часа")

        >>> parse_natural_datetime("через полтора часа")
        (datetime(2025, 10, 21, 2, 0, tzinfo=MOSCOW_TZ), "через полтора часа")

        >>> parse_natural_datetime("через 1-1.5 часа")
        (datetime(2025, 10, 21, 1, 45, tzinfo=MOSCOW_TZ), "через 1-1.5 часа")

        >>> parse_natural_datetime("Набрать клиенту")
        (None, "Набрать клиенту")
    """
    if not text or not text.strip():
        return None, text

    original_text = text.strip()
    text = original_text

    # Предобработка для лучшего распознавания
    preprocessed_text = _preprocess_time_text(text)

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
            preprocessed_text,
            languages=["ru", "en"],  # Поддержка русского и английского
            settings=settings,
        )

        if parsed_date:
            # Убедимся что есть timezone
            if parsed_date.tzinfo is None:
                parsed_date = parsed_date.replace(tzinfo=MOSCOW_TZ)

            # Валидация если требуется
            if validate:
                validation_result = validate_parsed_datetime(parsed_date, original_text)
                if not validation_result["is_valid"]:
                    logger.warning(
                        f"Валидация не прошла для '{original_text}': {validation_result['error']}"
                    )
                    return None, original_text

            logger.info(f"Успешно распознана дата: '{original_text}' -> {parsed_date}")
            return parsed_date, original_text

    except Exception as e:
        logger.debug(f"Не удалось распарсить дату '{original_text}': {e}")

    # Если не смогли распарсить - возвращаем None
    return None, original_text


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

        >>> should_parse_as_date("через час")
        True

        >>> should_parse_as_date("через полтора часа")
        True

        >>> should_parse_as_date("через 1-1.5 часа")
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
        "неделю",
        "месяц",
        "дня",
        "день",
        "часа",
        "час",
        "минут",
        "полтора",
        "полчаса",
    ]

    # Проверка на диапазоны типа "1-1.5"
    has_range = re.search(r"\d+\s*-\s*\d+", text_lower)

    # Если есть хотя бы одно ключевое слово или цифры или диапазон - пытаемся парсить
    return (
        any(keyword in text_lower for keyword in date_keywords)
        or any(char.isdigit() for char in text)
        or bool(has_range)
    )

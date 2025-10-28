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

        >>> _preprocess_time_text("после завтра")
        "послезавтра"

        >>> _preprocess_time_text("16:00")
        "сегодня в 16:00" (если время еще не прошло) или "завтра в 16:00" (если прошло)
    """
    text_lower = text.lower()

    # Обработка фразы "после" + время (например, "после 16:00")
    after_time_pattern = r"^после\s+(\d{1,2}:\d{2})$"
    if re.match(after_time_pattern, text_lower):
        time_part = re.match(after_time_pattern, text_lower).group(1)
        # Преобразуем "после 16:00" в интервал "с 16:00 до 17:00" (+1 час)
        try:
            time_parts = time_part.split(":")
            start_hour = int(time_parts[0])
            start_minute = int(time_parts[1])
            # Добавляем 1 час для окончания интервала
            end_hour = start_hour + 1
            if end_hour >= 24:
                end_hour = 0
            now = get_now().replace(tzinfo=MOSCOW_TZ)
            start_time = now.replace(hour=start_hour, minute=start_minute, second=0, microsecond=0)
            # Если время прошло сегодня, ставим на завтра
            if start_time <= now:
                return f"завтра с {start_hour:02d}:{start_minute:02d} до {end_hour:02d}:00"
            return f"с {start_hour:02d}:{start_minute:02d} до {end_hour:02d}:00"
        except (ValueError, IndexError):
            return f"после {time_part}"

    # Обработка фразы "до" + дата (например, "до 01.11.2025")
    before_date_pattern = r"^до\s+(\d{1,2})[./](\d{1,2})[./](\d{2,4})$"
    if re.match(before_date_pattern, text_lower):
        # Для "до DD.MM.YYYY" просто возвращаем текст как есть для дальнейшей обработки
        return text
    
    # Обработка фразы "до" + время (например, "до 16:00", "до 12")
    before_time_pattern = r"^до\s+(\d{1,2})(?::(\d{2}))?$"
    if re.match(before_time_pattern, text_lower):
        time_match = re.match(before_time_pattern, text_lower)
        end_hour = int(time_match.group(1))
        end_minute_str = time_match.group(2)
        # Преобразуем "до 16:00" или "до 12" в интервал "с текущего_времени до указанного"
        try:
            # Проверяем есть ли минуты
            if end_minute_str:
                end_minute = int(end_minute_str)
            else:
                # "до 12" - без двоеточия
                end_minute = 0
                
            now = get_now().replace(tzinfo=MOSCOW_TZ)
            current_hour = now.hour
            current_minute = now.minute
            # Создаем интервал от текущего времени до указанного
            # Если текущее время уже после указанного, ставим на завтра
            end_time = now.replace(hour=end_hour, minute=end_minute, second=0, microsecond=0)
            if end_time <= now:
                # Если время прошло сегодня, интервал на завтра
                return f"завтра с {current_hour:02d}:{current_minute:02d} до {end_hour:02d}:{end_minute:02d}"
            return f"с {current_hour:02d}:{current_minute:02d} до {end_hour:02d}:{end_minute:02d}"
        except (ValueError, IndexError):
            return text  # Возвращаем как есть

    # Обработка интервалов времени (например, "с 10:00 до 16:00", "10-16", "с 14 до 18")
    interval_pattern = r"^с\s+(\d{1,2})(?::\d{2})?\s+до\s+(\d{1,2})(?::\d{2})?$"
    interval_simple = r"^(\d{1,2})(?:-\s*|\s+до\s+)(\d{1,2})$"
    
    if re.match(interval_pattern, text_lower):
        match = re.match(interval_pattern, text_lower)
        start_hour = int(match.group(1))
        end_hour = int(match.group(2))
        # Возвращаем интервал как есть, чтобы parse_natural_datetime обработал его
        return text  # Возвращаем оригинал
    
    if re.match(interval_simple, text_lower):
        match = re.match(interval_simple, text_lower)
        start_hour = int(match.group(1))
        end_hour = int(match.group(2))
        # Преобразуем "10-16" в "с 10 до 16" (формат понятный dateparser)
        return f"с {start_hour} до {end_hour}"

    # Обработка случая, когда введено только время (например, "16:00")
    time_only_pattern = r"^(\d{1,2}:\d{2})$"
    if re.match(time_only_pattern, text_lower):
        # Проверяем, не прошло ли уже это время сегодня
        try:
            # Парсим время
            time_parts = text_lower.split(":")
            hour = int(time_parts[0])
            minute = int(time_parts[1])

            # Получаем текущее время
            now = get_now().replace(tzinfo=MOSCOW_TZ)

            # Создаем время на сегодня
            today_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

            # Если время уже прошло сегодня - ставим завтра
            if today_time <= now:
                return f"завтра в {text_lower}"
            return f"сегодня в {text_lower}"

        except (ValueError, IndexError):
            # Если не удалось распарсить время - используем "сегодня"
            return f"сегодня в {text_lower}"

    # Замена "после завтра" на "послезавтра" для единообразия
    text_lower = re.sub(r"\bпосле\s+завтра\b", "послезавтра", text_lower)
    text_lower = re.sub(r"\bна\s+после\s+завтра\b", "послезавтра", text_lower)
    text_lower = re.sub(r"\bна\s+послезавтра\b", "послезавтра", text_lower)

    # Замена "на завтра" на "завтра"
    text_lower = re.sub(r"\bна\s+завтра\b", "завтра", text_lower)

    # Замена "через час" на "через 1 час"
    text_lower = re.sub(r"\bчерез\s+час\b", "через 1 час", text_lower)

    # Замена "полчаса" на "30 минут"
    text_lower = re.sub(r"\bполчаса\b", "30 минут", text_lower)

    # Замена "полтора" на "1.5"
    text_lower = re.sub(r"\bполтора\b", "1.5", text_lower)

    # Замена "два с половиной" на "2.5"
    text_lower = re.sub(r"\bдва\s+с\s+половиной\b", "2.5", text_lower)
    text_lower = re.sub(r"\bтри\s+с\s+половиной\b", "3.5", text_lower)

    # Улучшенная обработка времени: "завтра в 12" -> "завтра в 12:00"
    # Паттерн: "в" + пробел + число (1-23) + конец строки или пробел
    time_pattern = r"\bв\s+(\d{1,2})\b(?=\s|$|[^\d])"

    def format_time(match):
        hour = int(match.group(1))
        if 0 <= hour <= 23:
            return f"в {hour}:00"
        return match.group(0)

    text_lower = re.sub(time_pattern, format_time, text_lower)

    # Дополнительная обработка для случаев типа "завтра в 12" в конце строки
    time_pattern_end = r"\bв\s+(\d{1,2})$"

    def format_time_end(match):
        hour = int(match.group(1))
        if 0 <= hour <= 23:
            return f"в {hour}:00"
        return match.group(0)

    text_lower = re.sub(time_pattern_end, format_time_end, text_lower)

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
    
    # 🔥 СПЕЦИАЛЬНАЯ ОБРАБОТКА ИНТЕРВАЛОВ
    # Проверяем интервалы "с 10:00 до 16:00", "10-16" и т.д.
    text_lower = text.lower()
    
    # Полный формат: "с 10:00 до 16:00", "с 14 до 18"
    interval_pattern = r"^с\s+(\d{1,2})(?::(\d{2}))?\s+до\s+(\d{1,2})(?::(\d{2}))?$"
    # Простой формат: "10-16", "10 до 16"
    interval_simple = r"^(\d{1,2})(?:-\s*|\s+до\s+)(\d{1,2})$"
    # Начало интервала: "с 12"
    interval_start_only = r"^с\s+(\d{1,2})(?::(\d{2}))?$"
    
    # Обработка "с 12" (начало интервала без конца)
    if re.match(interval_start_only, text_lower):
        match = re.match(interval_start_only, text_lower)
        start_hour = int(match.group(1))
        start_minute = int(match.group(2)) if match.group(2) else 0
        
        now = get_now().replace(tzinfo=MOSCOW_TZ)
        target_time = now.replace(hour=start_hour, minute=start_minute, second=0, microsecond=0)
        # Если время уже прошло сегодня, ставим завтра
        if target_time <= now:
            target_time = target_time + timedelta(days=1)
        # Возвращаем datetime и user_friendly текст (только начало интервала)
        user_friendly = f"с {start_hour:02d}:{start_minute:02d}"
        return target_time, user_friendly
    
    if re.match(interval_pattern, text_lower):
        match = re.match(interval_pattern, text_lower)
        start_hour = int(match.group(1))
        start_minute = int(match.group(2)) if match.group(2) else 0
        end_hour = int(match.group(3))
        end_minute = int(match.group(4)) if match.group(4) else 0
        
        now = get_now().replace(tzinfo=MOSCOW_TZ)
        target_time = now.replace(hour=start_hour, minute=start_minute, second=0, microsecond=0)
        # Если время уже прошло сегодня, ставим завтра
        if target_time <= now:
            target_time = target_time + timedelta(days=1)
        # Возвращаем datetime и user_friendly текст с интервалом
        user_friendly = f"с {start_hour:02d}:{start_minute:02d} до {end_hour:02d}:{end_minute:02d}"
        return target_time, user_friendly
    
    if re.match(interval_simple, text_lower):
        match = re.match(interval_simple, text_lower)
        start_hour = int(match.group(1))
        end_hour = int(match.group(2))
        now = get_now().replace(tzinfo=MOSCOW_TZ)
        target_time = now.replace(hour=start_hour, minute=0, second=0, microsecond=0)
        # Если время уже прошло сегодня, ставим завтра
        if target_time <= now:
            target_time = target_time + timedelta(days=1)
        # Возвращаем datetime и user_friendly текст
        user_friendly = f"с {start_hour:02d}:00 до {end_hour:02d}:00"
        return target_time, user_friendly

    # Предобработка для случаев типа "01.11.25" - исправляем на "01.11.2025"
    # Проверяем форматы DD.MM.YY или DD.MM.YY
    short_year_pattern = r'(\d{1,2})\.(\d{1,2})\.(\d{2})$'
    match = re.match(short_year_pattern, text)
    if match:
        day, month, year = match.groups()
        # Проверяем, что год в разумных пределах (00-99)
        year_int = int(year)
        current_year = get_now().year
        
        # Определяем полный год
        # Если год <= текущий год % 100, то это ближайший год
        # Иначе это прошлый век
        current_year_short = current_year % 100
        if year_int <= current_year_short:
            # Это текущий или ближайший год
            full_year = (current_year // 100) * 100 + year_int
        else:
            # Это прошлый век
            full_year = ((current_year // 100) - 1) * 100 + year_int
        
        # Проверяем, что дата не слишком далеко в будущем
        if full_year > current_year + 1:
            full_year = 2000 + year_int
        
        text = f"{day}.{month}.{full_year}"
        logger.debug(f"Исправлена короткая дата '{original_text}' -> '{text}'")

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

        >>> should_parse_as_date("16:00")
        True

        >>> should_parse_as_date("3")
        False

        >>> should_parse_as_date("Набрать клиенту")
        False
    """
    if not text or not text.strip():
        return False

    text_lower = text.lower().strip()

    # Проверка на время в формате HH:MM (например, "16:00")
    has_time_format = re.search(r"^\d{1,2}:\d{2}$", text_lower)
    if has_time_format:
        return True

    # Проверка на интервалы: "с 10 до 16", "до 16:00", "после 18:00"
    # Также "с 12" (начало интервала) - это тоже интервал
    # И "до 12" (конец интервала) - тоже интервал
    interval_patterns = [
        r"^с\s+\d{1,2}(?::\d{2})?\s+до\s+\d{1,2}(?::\d{2})?$",  # "с 10:00 до 16:00"
        r"^с\s+\d{1,2}(?::\d{2})?$",  # "с 12" - начало интервала
        r"^до\s+\d{1,2}(?::\d{2})?$",  # "до 16:00" или "до 12"
        r"^до\s+\d{1,2}[./]\d{1,2}[./]\d{2,4}$",  # "до 01.11.2025" или "до 01.11.25"
        r"^после\s+\d{1,2}(?::\d{2})?$",  # "после 18:00" или "после 12"
        r"^\d{1,2}(?:-\s*|\s+до\s+)\d{1,2}$",  # "10-16"
    ]
    
    for pattern in interval_patterns:
        if re.match(pattern, text_lower):
            return True

    # Если текст состоит только из цифр (1-2 цифры) - не парсим как дату
    if re.match(r"^\d{1,2}$", text_lower):
        return False

    # Ключевые слова для дат/времени
    date_keywords = [
        "завтра",
        "послезавтра",
        "после завтра",  # Вариант через пробел
        "на завтра",  # Вариант с предлогом
        "на послезавтра",
        "на после завтра",
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

    # Проверка на даты в формате DD.MM.YYYY или DD/MM/YYYY
    has_date_format = re.search(r"\d{1,2}[./]\d{1,2}[./]\d{2,4}", text_lower)

    # Если есть хотя бы одно ключевое слово, диапазон, формат даты или времени - пытаемся парсить
    return (
        any(keyword in text_lower for keyword in date_keywords)
        or bool(has_range)
        or bool(has_date_format)
        or bool(has_time_format)
    )

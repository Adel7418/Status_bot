"""
Telegram Parser Service

Сервис для парсинга заявок из Telegram-группы через Telethon.
"""

from .equipment_dict import EQUIPMENT_ABBREVIATIONS, normalize_equipment_type
from .patterns import (
    PHONE_PATTERN,
    TIME_PATTERN,
    TIME_KEYWORDS,
    ADDRESS_KEYWORDS,
    extract_phone,
    contains_time_indicator,
    looks_like_address,
)
from .schemas import ConfirmationData, OrderParsed, ParseResult

__all__ = [
    "EQUIPMENT_ABBREVIATIONS",
    "normalize_equipment_type",
    "PHONE_PATTERN",
    "TIME_PATTERN",
    "TIME_KEYWORDS",
    "ADDRESS_KEYWORDS",
    "extract_phone",
    "contains_time_indicator",
    "looks_like_address",
    "OrderParsed",
    "ParseResult",
    "ConfirmationData",
]

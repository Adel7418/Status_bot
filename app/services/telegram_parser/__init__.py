"""
Telegram Parser Service

Сервис для парсинга заявок из Telegram-группы через Telethon.
"""

from .confirmation_service import OrderConfirmationService
from .equipment_dict import EQUIPMENT_ABBREVIATIONS, normalize_equipment_type
from .parser_service import OrderParserService
from .patterns import (
    ADDRESS_KEYWORDS,
    PHONE_PATTERN,
    TIME_KEYWORDS,
    TIME_PATTERN,
    contains_time_indicator,
    extract_phone,
    looks_like_address,
)
from .schemas import ConfirmationData, OrderParsed, ParseResult
from .telethon_client import TelethonClient


__all__ = [
    "ADDRESS_KEYWORDS",
    "EQUIPMENT_ABBREVIATIONS",
    "PHONE_PATTERN",
    "TIME_KEYWORDS",
    "TIME_PATTERN",
    "ConfirmationData",
    "OrderConfirmationService",
    "OrderParsed",
    "OrderParserService",
    "ParseResult",
    "TelethonClient",
    "contains_time_indicator",
    "extract_phone",
    "looks_like_address",
    "normalize_equipment_type",
]

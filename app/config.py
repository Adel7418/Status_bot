"""
Конфигурация бота (обратная совместимость)

DEPRECATED: Используйте app.core вместо app.config
"""

from app.core.config import Config, Messages, MAX_DESCRIPTION_LENGTH, MAX_NOTES_LENGTH, PHONE_REGEX
from app.core.constants import EquipmentType, OrderStatus, UserRole

__all__ = [
    "Config",
    "Messages",
    "UserRole",
    "OrderStatus",
    "EquipmentType",
    "MAX_DESCRIPTION_LENGTH",
    "MAX_NOTES_LENGTH",
    "PHONE_REGEX",
]

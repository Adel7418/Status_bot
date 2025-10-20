"""
Конфигурация бота (обратная совместимость)

DEPRECATED: Используйте app.core вместо app.config
"""

from app.core.config import MAX_DESCRIPTION_LENGTH, MAX_NOTES_LENGTH, PHONE_REGEX, Config, Messages
from app.core.constants import EquipmentType, OrderStatus, UserRole


__all__ = [
    "MAX_DESCRIPTION_LENGTH",
    "MAX_NOTES_LENGTH",
    "PHONE_REGEX",
    "Config",
    "EquipmentType",
    "Messages",
    "OrderStatus",
    "UserRole",
]

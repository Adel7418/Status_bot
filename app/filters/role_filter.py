"""
Фильтры для проверки ролей пользователей
"""

import logging

from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

from app.config import UserRole


logger = logging.getLogger(__name__)


class RoleFilter(BaseFilter):
    """Фильтр для проверки роли пользователя"""

    def __init__(self, roles: str | list[str]):
        """
        Инициализация

        Args:
            roles: Роль или список ролей
        """
        if isinstance(roles, str):
            self.roles = [roles]
        else:
            self.roles = roles

    async def __call__(self, _event: Message | CallbackQuery, **kwargs) -> bool:
        """
        Проверка роли

        Args:
            _event: Событие (не используется, но требуется для совместимости с aiogram)
            **kwargs: Дополнительные данные, включая user_roles из middleware

        Returns:
            True если роль подходит
        """
        # Получаем список ролей из kwargs (добавляется middleware)
        user_roles = kwargs.get("user_roles", [UserRole.UNKNOWN])

        # Проверяем, есть ли хотя бы одна из требуемых ролей у пользователя
        return any(role in user_roles for role in self.roles)


class IsAdmin(RoleFilter):
    """Фильтр для проверки роли администратора"""

    def __init__(self):
        super().__init__(UserRole.ADMIN)


class IsDispatcher(RoleFilter):
    """Фильтр для проверки роли диспетчера"""

    def __init__(self):
        super().__init__(UserRole.DISPATCHER)


class IsMaster(RoleFilter):
    """Фильтр для проверки роли мастера"""

    def __init__(self):
        super().__init__(UserRole.MASTER)


class IsAdminOrDispatcher(RoleFilter):
    """Фильтр для проверки роли администратора или диспетчера"""

    def __init__(self):
        super().__init__([UserRole.ADMIN, UserRole.DISPATCHER])

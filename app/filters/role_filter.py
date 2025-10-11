"""
Фильтры для проверки ролей пользователей
"""
import logging
from typing import Union, List
from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery
from app.config import UserRole

logger = logging.getLogger(__name__)


class RoleFilter(BaseFilter):
    """Фильтр для проверки роли пользователя"""
    
    def __init__(self, roles: Union[str, List[str]]):
        """
        Инициализация
        
        Args:
            roles: Роль или список ролей
        """
        if isinstance(roles, str):
            self.roles = [roles]
        else:
            self.roles = roles
    
    async def __call__(
        self,
        event: Union[Message, CallbackQuery],
        **kwargs
    ) -> bool:
        """
        Проверка роли
        
        Args:
            event: Событие
            **kwargs: Дополнительные данные, включая user_role из middleware
            
        Returns:
            True если роль подходит
        """
        # Получаем роль из kwargs (добавляется middleware)
        user_role = kwargs.get('user_role', UserRole.UNKNOWN)
        result = user_role in self.roles
        
        return result


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


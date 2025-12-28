"""
Middleware для проверки ролей и регистрации пользователей
"""

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from app.database import Database


logger = logging.getLogger(__name__)


class RoleCheckMiddleware(BaseMiddleware):
    """Middleware для автоматической регистрации пользователей и проверки ролей"""

    def __init__(self, db: Database):
        """
        Инициализация

        Args:
            db: Экземпляр базы данных
        """
        super().__init__()
        self.db = db

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """
        Обработка события

        Args:
            handler: Следующий handler
            event: Событие (Message или CallbackQuery)
            data: Данные

        Returns:
            Результат выполнения handler
        """
        if not isinstance(event, Message | CallbackQuery):
            return await handler(event, data)

        # Получаем пользователя из события
        user = event.from_user

        if user:
            # Получаем или создаем пользователя в БД
            db_user = await self.db.get_or_create_user(
                telegram_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
            )

            # Добавляем пользователя и его роли в данные
            data["user"] = db_user
            primary_role = db_user.get_primary_role()
            all_roles = db_user.get_roles()
            data["user_role"] = primary_role  # Основная роль для обратной совместимости
            data["user_roles"] = all_roles  # Список всех ролей

            logger.info(
                "RoleCheckMiddleware: User %s - db_user.role='%s', primary_role='%s', all_roles=%s, data['user_role']='%s'",
                user.id,
                db_user.role,
                primary_role,
                all_roles,
                data.get("user_role"),
            )

        # Вызываем следующий handler
        return await handler(event, data)

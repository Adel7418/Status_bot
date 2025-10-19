"""
Сервис для работы с пользователями (бизнес-логика)
"""

import logging

from app.config import UserRole
from app.database.models import User
from app.repositories import UserRepository


logger = logging.getLogger(__name__)


class UserService:
    """
    Сервис для управления пользователями
    Инкапсулирует бизнес-логику работы с пользователями
    """

    def __init__(self, user_repo: UserRepository):
        """
        Инициализация сервиса

        Args:
            user_repo: Репозиторий пользователей
        """
        self.user_repo = user_repo

    async def get_or_create_user(
        self,
        telegram_id: int,
        username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> User:
        """
        Получение или создание пользователя

        Args:
            telegram_id: Telegram ID
            username: Username
            first_name: Имя
            last_name: Фамилия

        Returns:
            Объект User
        """
        return await self.user_repo.get_or_create(telegram_id, username, first_name, last_name)

    async def get_user_by_telegram_id(self, telegram_id: int) -> User | None:
        """
        Получение пользователя по Telegram ID

        Args:
            telegram_id: Telegram ID

        Returns:
            Объект User или None
        """
        return await self.user_repo.get_by_telegram_id(telegram_id)

    async def get_users_by_role(self, role: str) -> list[User]:
        """
        Получение всех пользователей с определенной ролью

        Args:
            role: Роль для фильтрации

        Returns:
            Список пользователей
        """
        return await self.user_repo.get_all_by_role(role)

    async def add_role(self, telegram_id: int, role: str) -> bool:
        """
        Добавление роли пользователю

        Args:
            telegram_id: Telegram ID пользователя
            role: Роль для добавления

        Returns:
            True если роль добавлена

        Raises:
            ValueError: Если роль недействительна
        """
        # Валидация роли
        valid_roles = [UserRole.ADMIN, UserRole.DISPATCHER, UserRole.MASTER]
        if role not in valid_roles:
            raise ValueError(
                f"Недействительная роль: {role}. Доступные роли: {', '.join(valid_roles)}"
            )

        success = await self.user_repo.add_role(telegram_id, role)

        if success:
            logger.info(f"Роль {role} добавлена пользователю {telegram_id}")

        return success

    async def remove_role(self, telegram_id: int, role: str) -> bool:
        """
        Удаление роли у пользователя

        Args:
            telegram_id: Telegram ID пользователя
            role: Роль для удаления

        Returns:
            True если роль удалена
        """
        success = await self.user_repo.remove_role(telegram_id, role)

        if success:
            logger.info(f"Роль {role} удалена у пользователя {telegram_id}")

        return success

    async def has_role(self, telegram_id: int, role: str) -> bool:
        """
        Проверка наличия роли у пользователя

        Args:
            telegram_id: Telegram ID пользователя
            role: Роль для проверки

        Returns:
            True если роль есть
        """
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            return False

        return user.has_role(role)

    async def get_user_roles(self, telegram_id: int) -> list[str]:
        """
        Получение списка ролей пользователя

        Args:
            telegram_id: Telegram ID пользователя

        Returns:
            Список ролей
        """
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            return ["UNKNOWN"]

        return user.get_roles()

    async def update_user(self, telegram_id: int, updates: dict) -> bool:
        """
        Обновление данных пользователя

        Args:
            telegram_id: Telegram ID пользователя
            updates: Словарь с полями для обновления

        Returns:
            True если обновление успешно
        """
        return await self.user_repo.update(telegram_id, updates)

"""
Сервис для работы с мастерами (бизнес-логика)
"""

import logging

from app.config import UserRole
from app.database.models import Master
from app.repositories import MasterRepository, UserRepository


logger = logging.getLogger(__name__)


class MasterService:
    """
    Сервис для управления мастерами
    Инкапсулирует бизнес-логику работы с мастерами
    """

    def __init__(self, master_repo: MasterRepository, user_repo: UserRepository):
        """
        Инициализация сервиса

        Args:
            master_repo: Репозиторий мастеров
            user_repo: Репозиторий пользователей
        """
        self.master_repo = master_repo
        self.user_repo = user_repo

    async def register_master(
        self, telegram_id: int, phone: str, specialization: str
    ) -> tuple[Master, bool]:
        """
        Регистрация нового мастера

        Args:
            telegram_id: Telegram ID
            phone: Телефон
            specialization: Специализация

        Returns:
            Кортеж (Master, is_new) - объект мастера и флаг "новый ли мастер"

        Raises:
            ValueError: Если мастер уже зарегистрирован
        """
        # Проверяем, не зарегистрирован ли мастер уже
        existing_master = await self.master_repo.get_by_telegram_id(telegram_id)
        if existing_master:
            logger.warning(f"Мастер {telegram_id} уже зарегистрирован")
            return existing_master, False

        # Создаем или обновляем пользователя
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if user and not user.has_role(UserRole.MASTER):
            # Добавляем роль MASTER, если её нет
            await self.user_repo.add_role(telegram_id, UserRole.MASTER)

        # Создаем мастера
        master = await self.master_repo.create(
            telegram_id=telegram_id,
            phone=phone,
            specialization=specialization,
            is_active=True,
            is_approved=False,  # Требует одобрения админом
        )

        logger.info(f"Мастер #{master.id} зарегистрирован (telegram_id: {telegram_id})")
        return master, True

    async def get_master_by_telegram_id(self, telegram_id: int) -> Master | None:
        """
        Получение мастера по Telegram ID

        Args:
            telegram_id: Telegram ID

        Returns:
            Объект Master или None
        """
        return await self.master_repo.get_by_telegram_id(telegram_id)

    async def get_master_by_id(self, master_id: int) -> Master | None:
        """
        Получение мастера по ID

        Args:
            master_id: ID мастера

        Returns:
            Объект Master или None
        """
        return await self.master_repo.get_by_id(master_id)

    async def get_all_masters(
        self, is_active: bool | None = None, is_approved: bool | None = None
    ) -> list[Master]:
        """
        Получение всех мастеров с фильтрацией

        Args:
            is_active: Фильтр по активности
            is_approved: Фильтр по одобрению

        Returns:
            Список мастеров
        """
        return await self.master_repo.get_all(is_active=is_active, is_approved=is_approved)

    async def approve_master(self, master_id: int, approved_by: int) -> bool:
        """
        Одобрение мастера администратором

        Args:
            master_id: ID мастера
            approved_by: Telegram ID администратора

        Returns:
            True если одобрение успешно

        Raises:
            ValueError: Если мастер не найден или пользователь не админ
        """
        # Проверяем, что пользователь - админ
        admin = await self.user_repo.get_by_telegram_id(approved_by)
        if not admin or not admin.has_role(UserRole.ADMIN):
            raise ValueError(f"Пользователь {approved_by} не является администратором")

        # Проверяем существование мастера
        master = await self.master_repo.get_by_id(master_id)
        if not master:
            raise ValueError(f"Мастер #{master_id} не найден")

        # Одобряем мастера
        success = await self.master_repo.approve(master_id)

        if success:
            logger.info(f"Мастер #{master_id} одобрен администратором {approved_by}")

        return success

    async def set_work_chat(self, master_id: int, work_chat_id: int) -> bool:
        """
        Установка рабочей группы для мастера

        Args:
            master_id: ID мастера
            work_chat_id: ID рабочей группы

        Returns:
            True если установка успешна
        """
        success = await self.master_repo.set_work_chat(master_id, work_chat_id)

        if success:
            logger.info(f"Мастеру #{master_id} установлена рабочая группа {work_chat_id}")

        return success

    async def deactivate_master(self, master_id: int, deactivated_by: int) -> bool:
        """
        Деактивация мастера

        Args:
            master_id: ID мастера
            deactivated_by: Telegram ID пользователя

        Returns:
            True если деактивация успешна

        Raises:
            ValueError: Если пользователь не админ
        """
        # Проверяем, что пользователь - админ
        admin = await self.user_repo.get_by_telegram_id(deactivated_by)
        if not admin or not admin.has_role(UserRole.ADMIN):
            raise ValueError(f"Пользователь {deactivated_by} не является администратором")

        success = await self.master_repo.deactivate(master_id)

        if success:
            logger.info(f"Мастер #{master_id} деактивирован пользователем {deactivated_by}")

        return success

    async def activate_master(self, master_id: int, activated_by: int) -> bool:
        """
        Активация мастера

        Args:
            master_id: ID мастера
            activated_by: Telegram ID пользователя

        Returns:
            True если активация успешна

        Raises:
            ValueError: Если пользователь не админ
        """
        # Проверяем, что пользователь - админ
        admin = await self.user_repo.get_by_telegram_id(activated_by)
        if not admin or not admin.has_role(UserRole.ADMIN):
            raise ValueError(f"Пользователь {activated_by} не является администратором")

        success = await self.master_repo.activate(master_id)

        if success:
            logger.info(f"Мастер #{master_id} активирован пользователем {activated_by}")

        return success

    async def update_master(self, master_id: int, updates: dict) -> bool:
        """
        Обновление данных мастера

        Args:
            master_id: ID мастера
            updates: Словарь с полями для обновления

        Returns:
            True если обновление успешно
        """
        return await self.master_repo.update(master_id, updates)

    async def get_master_by_work_chat(self, work_chat_id: int) -> Master | None:
        """
        Получение мастера по ID рабочей группы

        Args:
            work_chat_id: ID рабочей группы

        Returns:
            Объект Master или None
        """
        return await self.master_repo.get_by_work_chat_id(work_chat_id)

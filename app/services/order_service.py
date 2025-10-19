"""
Сервис для работы с заявками (бизнес-логика)
"""

import logging
from datetime import datetime

from app.config import OrderStatus, UserRole
from app.database.models import Order
from app.domain.order_state_machine import InvalidStateTransitionError, OrderStateMachine
from app.repositories import MasterRepository, OrderRepository, UserRepository


logger = logging.getLogger(__name__)


class OrderService:
    """
    Сервис для управления заявками
    Инкапсулирует бизнес-логику работы с заявками
    """

    def __init__(
        self,
        order_repo: OrderRepository,
        user_repo: UserRepository,
        master_repo: MasterRepository,
        state_machine: OrderStateMachine | None = None,
    ):
        """
        Инициализация сервиса

        Args:
            order_repo: Репозиторий заявок
            user_repo: Репозиторий пользователей
            master_repo: Репозиторий мастеров
            state_machine: State machine для валидации переходов
        """
        self.order_repo = order_repo
        self.user_repo = user_repo
        self.master_repo = master_repo
        self.state_machine = state_machine or OrderStateMachine()

    async def create_order(
        self,
        equipment_type: str,
        description: str,
        client_name: str,
        client_address: str,
        client_phone: str,
        dispatcher_id: int,
        notes: str | None = None,
        scheduled_time: str | None = None,
    ) -> Order:
        """
        Создание новой заявки

        Args:
            equipment_type: Тип техники
            description: Описание проблемы
            client_name: Имя клиента
            client_address: Адрес клиента
            client_phone: Телефон клиента
            dispatcher_id: ID диспетчера
            notes: Заметки
            scheduled_time: Время прибытия к клиенту

        Returns:
            Созданная заявка
        """
        # Проверяем, что диспетчер существует и имеет соответствующую роль
        dispatcher = await self.user_repo.get_by_telegram_id(dispatcher_id)
        if not dispatcher:
            raise ValueError(f"Диспетчер {dispatcher_id} не найден")

        if not dispatcher.has_role(UserRole.DISPATCHER):
            raise ValueError(f"Пользователь {dispatcher_id} не является диспетчером")

        # Создаем заявку
        order = await self.order_repo.create(
            equipment_type=equipment_type,
            description=description,
            client_name=client_name,
            client_address=client_address,
            client_phone=client_phone,
            dispatcher_id=dispatcher_id,
            notes=notes,
            scheduled_time=scheduled_time,
        )

        logger.info(f"Заявка #{order.id} создана диспетчером {dispatcher_id}")
        return order

    async def get_order(self, order_id: int) -> Order | None:
        """
        Получение заявки по ID

        Args:
            order_id: ID заявки

        Returns:
            Заявка или None
        """
        return await self.order_repo.get_by_id(order_id)

    async def get_all_orders(
        self, status: str | None = None, master_id: int | None = None, limit: int | None = None
    ) -> list[Order]:
        """
        Получение всех заявок с фильтрацией

        Args:
            status: Фильтр по статусу
            master_id: Фильтр по ID мастера
            limit: Лимит количества

        Returns:
            Список заявок
        """
        return await self.order_repo.get_all(status=status, master_id=master_id, limit=limit)

    async def assign_master(self, order_id: int, master_id: int, assigned_by: int) -> bool:
        """
        Назначение мастера на заявку

        Args:
            order_id: ID заявки
            master_id: ID мастера
            assigned_by: Telegram ID пользователя, который назначает

        Returns:
            True если назначение успешно

        Raises:
            ValueError: Если мастер не найден или не одобрен
            InvalidStateTransitionError: Если переход статуса невозможен
        """
        # Проверяем существование заявки
        order = await self.order_repo.get_by_id(order_id)
        if not order:
            raise ValueError(f"Заявка #{order_id} не найдена")

        # Проверяем существование мастера
        master = await self.master_repo.get_by_id(master_id)
        if not master:
            raise ValueError(f"Мастер #{master_id} не найден")

        if not master.is_approved:
            raise ValueError(f"Мастер #{master_id} не одобрен администратором")

        # Получаем информацию о пользователе, который назначает
        user = await self.user_repo.get_by_telegram_id(assigned_by)
        if not user:
            raise ValueError(f"Пользователь {assigned_by} не найден")

        user_role = user.get_primary_role()

        # Валидируем переход статуса через state machine
        try:
            self.state_machine.transition(order.status, OrderStatus.ASSIGNED, user_role)
        except InvalidStateTransitionError as e:
            logger.error(f"Невозможно назначить мастера на заявку #{order_id}: {e}")
            raise

        # Назначаем мастера
        success = await self.order_repo.assign_master(order_id, master_id, assigned_by)

        if success:
            logger.info(
                f"Мастер #{master_id} назначен на заявку #{order_id} пользователем {assigned_by}"
            )

        return success

    async def change_status(
        self, order_id: int, new_status: str, changed_by: int, notes: str | None = None
    ) -> bool:
        """
        Изменение статуса заявки

        Args:
            order_id: ID заявки
            new_status: Новый статус
            changed_by: Telegram ID пользователя
            notes: Заметки

        Returns:
            True если статус изменен

        Raises:
            InvalidStateTransitionError: Если переход статуса невозможен
        """
        # Проверяем существование заявки
        order = await self.order_repo.get_by_id(order_id)
        if not order:
            raise ValueError(f"Заявка #{order_id} не найдена")

        # Получаем информацию о пользователе
        user = await self.user_repo.get_by_telegram_id(changed_by)
        if not user:
            raise ValueError(f"Пользователь {changed_by} не найден")

        user_role = user.get_primary_role()

        # Валидируем переход статуса
        try:
            self.state_machine.transition(order.status, new_status, user_role)
        except InvalidStateTransitionError as e:
            logger.error(f"Невозможно изменить статус заявки #{order_id}: {e}")
            raise

        # Изменяем статус
        success = await self.order_repo.update_status(order_id, new_status, changed_by, notes)

        if success:
            logger.info(f"Статус заявки #{order_id} изменен: {order.status} → {new_status}")

        return success

    async def update_order(self, order_id: int, updates: dict) -> bool:
        """
        Обновление данных заявки

        Args:
            order_id: ID заявки
            updates: Словарь с полями для обновления

        Returns:
            True если обновление успешно
        """
        return await self.order_repo.update(order_id, updates)

    async def get_master_orders(self, master_id: int, status: str | None = None) -> list[Order]:
        """
        Получение заявок мастера

        Args:
            master_id: ID мастера
            status: Фильтр по статусу

        Returns:
            Список заявок
        """
        return await self.order_repo.get_by_master(master_id, status)

    async def get_orders_by_period(
        self, start_date: datetime, end_date: datetime, status: str | None = None
    ) -> list[Order]:
        """
        Получение заявок за период

        Args:
            start_date: Начало периода
            end_date: Конец периода
            status: Фильтр по статусу

        Returns:
            Список заявок
        """
        return await self.order_repo.get_by_period(start_date, end_date, status)

    async def get_status_history(self, order_id: int) -> list[dict]:
        """
        Получение истории изменения статусов

        Args:
            order_id: ID заявки

        Returns:
            Список записей истории
        """
        return await self.order_repo.get_status_history(order_id)

    async def can_change_status(
        self, order_id: int, new_status: str, user_telegram_id: int
    ) -> bool:
        """
        Проверка возможности изменения статуса

        Args:
            order_id: ID заявки
            new_status: Новый статус
            user_telegram_id: Telegram ID пользователя

        Returns:
            True если переход возможен
        """
        order = await self.order_repo.get_by_id(order_id)
        if not order:
            return False

        user = await self.user_repo.get_by_telegram_id(user_telegram_id)
        if not user:
            return False

        user_role = user.get_primary_role()

        try:
            self.state_machine.transition(order.status, new_status, user_role)
            return True
        except InvalidStateTransitionError:
            return False

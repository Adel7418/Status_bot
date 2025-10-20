"""
Сервис для расширенного поиска заявок
"""

import logging
from datetime import datetime

from app.database.models import Order
from app.repositories.order_repository_extended import OrderRepositoryExtended


logger = logging.getLogger(__name__)


class SearchService:
    """Сервис для поиска заявок"""

    def __init__(self, order_repo: OrderRepositoryExtended):
        """
        Инициализация сервиса

        Args:
            order_repo: Репозиторий заявок
        """
        self.order_repo = order_repo

    async def search(
        self,
        query: str | None = None,
        filters: dict | None = None,
        include_deleted: bool = False,
        limit: int = 50,
    ) -> list[Order]:
        """
        Универсальный поиск заявок

        Args:
            query: Текстовый поисковый запрос
            filters: Фильтры (status, master_id, date_from, date_to и т.д.)
            include_deleted: Включать удаленные заявки
            limit: Максимальное количество результатов

        Returns:
            Список найденных заявок
        """
        if filters is None:
            filters = {}

        # Вызываем расширенный поиск репозитория
        results = await self.order_repo.search_orders(
            search_query=query,
            status=filters.get("status"),
            master_id=filters.get("master_id"),
            client_name=filters.get("client_name"),
            client_phone=filters.get("client_phone"),
            date_from=filters.get("date_from"),
            date_to=filters.get("date_to"),
            include_deleted=include_deleted,
            limit=limit,
        )

        logger.info(f"Поиск выполнен: query='{query}', filters={filters}, found={len(results)}")
        return results

    async def search_by_id(self, order_id: int, include_deleted: bool = False) -> Order | None:
        """
        Поиск заявки по ID

        Args:
            order_id: ID заявки
            include_deleted: Включать удаленные

        Returns:
            Заявка или None
        """
        return await self.order_repo.get_by_id(order_id, include_deleted=include_deleted)

    async def search_by_client_phone(
        self, phone: str, include_deleted: bool = False
    ) -> list[Order]:
        """
        Поиск всех заявок клиента по телефону

        Args:
            phone: Номер телефона
            include_deleted: Включать удаленные

        Returns:
            Список заявок клиента
        """
        return await self.order_repo.search_orders(
            client_phone=phone, include_deleted=include_deleted, limit=100
        )

    async def search_by_client_name(self, name: str, include_deleted: bool = False) -> list[Order]:
        """
        Поиск заявок по имени клиента

        Args:
            name: Имя клиента
            include_deleted: Включать удаленные

        Returns:
            Список заявок
        """
        return await self.order_repo.search_orders(
            client_name=name, include_deleted=include_deleted, limit=100
        )

    async def search_by_date_range(
        self,
        date_from: datetime,
        date_to: datetime,
        status: str | None = None,
        include_deleted: bool = False,
    ) -> list[Order]:
        """
        Поиск заявок за период

        Args:
            date_from: Начало периода
            date_to: Конец периода
            status: Фильтр по статусу (опционально)
            include_deleted: Включать удаленные

        Returns:
            Список заявок за период
        """
        return await self.order_repo.search_orders(
            date_from=date_from,
            date_to=date_to,
            status=status,
            include_deleted=include_deleted,
            limit=1000,
        )

    async def search_deleted_orders(self, limit: int = 50, offset: int = 0) -> list[Order]:
        """
        Получение списка удаленных заявок

        Args:
            limit: Максимальное количество
            offset: Смещение для пагинации

        Returns:
            Список удаленных заявок
        """
        return await self.order_repo.get_deleted_orders(limit=limit, offset=offset)

    async def get_full_order_history(self, order_id: int) -> dict:
        """
        Получение полной истории заявки

        Args:
            order_id: ID заявки

        Returns:
            Словарь с полной историей заявки
        """
        return await self.order_repo.get_full_history(order_id)

    async def get_statistics(self, include_deleted: bool = False) -> dict:
        """
        Получение статистики по заявкам

        Args:
            include_deleted: Включать удаленные в статистику

        Returns:
            Словарь со статистикой
        """
        return await self.order_repo.get_statistics(include_deleted=include_deleted)

    def format_search_results(self, orders: list[Order]) -> str:
        """
        Форматирование результатов поиска для отображения

        Args:
            orders: Список заявок

        Returns:
            Отформатированная строка
        """
        if not orders:
            return "🔍 Ничего не найдено"

        result = f"🔍 <b>Найдено заявок:</b> {len(orders)}\n\n"

        for order in orders:
            result += f"📋 <b>Заявка #{order.id}</b>\n"
            result += f"📊 Статус: {order.status}\n"
            result += f"🔧 Тип: {order.equipment_type}\n"
            result += f"👤 Клиент: {order.client_name}\n"

            if order.master_name:
                result += f"👨‍🔧 Мастер: {order.master_name}\n"

            if hasattr(order, "deleted_at") and order.deleted_at:
                result += f"🗑 <i>Удалена: {order.deleted_at.strftime('%d.%m.%Y %H:%M')}</i>\n"

            result += "\n"

        return result

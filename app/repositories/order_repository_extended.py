"""
Расширенный репозиторий для работы с заявками
Поддержка: soft delete, полная история, расширенный поиск
"""

import logging
from datetime import datetime
from typing import Any

from app.database.models import Order
from app.repositories.order_repository import OrderRepository
from app.utils.helpers import get_now


logger = logging.getLogger(__name__)


class OrderRepositoryExtended(OrderRepository):
    """Расширенный репозиторий с soft delete и полной историей"""

    # ===== SOFT DELETE =====

    async def soft_delete(
        self, order_id: int, deleted_by: int, reason: str | None = None
    ) -> bool:
        """
        Мягкое удаление заявки

        Args:
            order_id: ID заявки
            deleted_by: Telegram ID пользователя
            reason: Причина удаления

        Returns:
            True если успешно
        """
        now = get_now()

        async with self.transaction():
            # Помечаем заявку как удаленную
            await self._execute(
                "UPDATE orders SET deleted_at = ?, version = version + 1 WHERE id = ?",
                (now.isoformat(), order_id),
            )

            # Логируем в audit_log
            await self._execute(
                """
                INSERT INTO audit_log (user_id, action, details, timestamp)
                VALUES (?, ?, ?, ?)
                """,
                (
                    deleted_by,
                    "ORDER_SOFT_DELETED",
                    f"Order #{order_id} deleted. Reason: {reason or 'Not specified'}",
                    now.isoformat(),
                ),
            )

            # Сохраняем в entity_history
            await self._execute(
                """
                INSERT INTO entity_history
                (table_name, record_id, field_name, old_value, new_value, changed_by, changed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "orders",
                    order_id,
                    "deleted_at",
                    None,
                    now.isoformat(),
                    deleted_by,
                    now.isoformat(),
                ),
            )

        logger.info(f"Заявка #{order_id} мягко удалена пользователем {deleted_by}")
        return True

    async def restore(self, order_id: int, restored_by: int) -> bool:
        """
        Восстановление удаленной заявки

        Args:
            order_id: ID заявки
            restored_by: Telegram ID пользователя

        Returns:
            True если успешно
        """
        now = get_now()

        async with self.transaction():
            await self._execute(
                "UPDATE orders SET deleted_at = NULL, version = version + 1 WHERE id = ?",
                (order_id,),
            )

            await self._execute(
                """
                INSERT INTO audit_log (user_id, action, details, timestamp)
                VALUES (?, ?, ?, ?)
                """,
                (
                    restored_by,
                    "ORDER_RESTORED",
                    f"Order #{order_id} restored",
                    now.isoformat(),
                ),
            )

        logger.info(f"Заявка #{order_id} восстановлена пользователем {restored_by}")
        return True

    # ===== ПОИСК С УЧЕТОМ DELETED =====

    async def get_by_id(self, order_id: int, include_deleted: bool = False) -> Order | None:
        """
        Получение заявки по ID

        Args:
            order_id: ID заявки
            include_deleted: Включать удаленные заявки

        Returns:
            Объект Order или None
        """
        query = """
            SELECT o.*,
                   u1.first_name || ' ' || COALESCE(u1.last_name, '') as dispatcher_name,
                   u2.first_name || ' ' || COALESCE(u2.last_name, '') as master_name
            FROM orders o
            LEFT JOIN users u1 ON o.dispatcher_id = u1.telegram_id
            LEFT JOIN masters m ON o.assigned_master_id = m.id
            LEFT JOIN users u2 ON m.telegram_id = u2.telegram_id
            WHERE o.id = ?
        """

        if not include_deleted:
            query += " AND o.deleted_at IS NULL"

        row = await self._fetch_one(query, (order_id,))
        return self._row_to_order(row) if row else None

    async def get_all(
        self,
        status: str | None = None,
        master_id: int | None = None,
        limit: int | None = None,
        include_deleted: bool = False,
    ) -> list[Order]:
        """
        Получение всех заявок с фильтрацией

        Args:
            status: Фильтр по статусу
            master_id: Фильтр по ID мастера
            limit: Лимит количества
            include_deleted: Включать удаленные заявки

        Returns:
            Список заявок
        """
        query = """
            SELECT o.*,
                   u1.first_name || ' ' || COALESCE(u1.last_name, '') as dispatcher_name,
                   u2.first_name || ' ' || COALESCE(u2.last_name, '') as master_name
            FROM orders o
            LEFT JOIN users u1 ON o.dispatcher_id = u1.telegram_id
            LEFT JOIN masters m ON o.assigned_master_id = m.id
            LEFT JOIN users u2 ON m.telegram_id = u2.telegram_id
            WHERE 1=1
        """
        params: list[Any] = []

        if not include_deleted:
            query += " AND o.deleted_at IS NULL"

        if status:
            query += " AND o.status = ?"
            params.append(status)

        if master_id:
            query += " AND o.assigned_master_id = ?"
            params.append(master_id)

        query += " ORDER BY o.created_at DESC"

        if limit:
            query += " LIMIT ?"
            params.append(limit)

        rows = await self._fetch_all(query, tuple(params) if params else None)
        return [self._row_to_order(row) for row in rows]

    # ===== РАСШИРЕННЫЙ ПОИСК =====

    async def search_orders(
        self,
        search_query: str | None = None,
        status: str | None = None,
        master_id: int | None = None,
        client_name: str | None = None,
        client_phone: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        include_deleted: bool = False,
        limit: int = 100,
    ) -> list[Order]:
        """
        Расширенный поиск заявок

        Args:
            search_query: Поисковый запрос (ищет в описании, адресе, типе техники)
            status: Фильтр по статусу
            master_id: Фильтр по мастеру
            client_name: Фильтр по имени клиента
            client_phone: Фильтр по телефону
            date_from: Дата создания от
            date_to: Дата создания до
            include_deleted: Включать удаленные
            limit: Максимальное количество результатов

        Returns:
            Список найденных заявок
        """
        query = """
            SELECT o.*,
                   u1.first_name || ' ' || COALESCE(u1.last_name, '') as dispatcher_name,
                   u2.first_name || ' ' || COALESCE(u2.last_name, '') as master_name
            FROM orders o
            LEFT JOIN users u1 ON o.dispatcher_id = u1.telegram_id
            LEFT JOIN masters m ON o.assigned_master_id = m.id
            LEFT JOIN users u2 ON m.telegram_id = u2.telegram_id
            WHERE 1=1
        """
        params: list[Any] = []

        if not include_deleted:
            query += " AND o.deleted_at IS NULL"

        if search_query:
            query += """ AND (
                o.description LIKE ? OR
                o.client_address LIKE ? OR
                o.equipment_type LIKE ?
            )"""
            search_pattern = f"%{search_query}%"
            params.extend([search_pattern, search_pattern, search_pattern])

        if status:
            query += " AND o.status = ?"
            params.append(status)

        if master_id:
            query += " AND o.assigned_master_id = ?"
            params.append(master_id)

        if client_name:
            query += " AND o.client_name LIKE ?"
            params.append(f"%{client_name}%")

        if client_phone:
            query += " AND o.client_phone LIKE ?"
            params.append(f"%{client_phone}%")

        if date_from:
            query += " AND o.created_at >= ?"
            params.append(date_from.isoformat())

        if date_to:
            query += " AND o.created_at <= ?"
            params.append(date_to.isoformat())

        query += " ORDER BY o.created_at DESC LIMIT ?"
        params.append(limit)

        rows = await self._fetch_all(query, tuple(params))
        return [self._row_to_order(row) for row in rows]

    # ===== ПОЛУЧЕНИЕ УДАЛЕННЫХ ЗАЯВОК =====

    async def get_deleted_orders(self, limit: int = 50, offset: int = 0) -> list[Order]:
        """
        Получение списка удаленных заявок

        Args:
            limit: Максимальное количество
            offset: Смещение для пагинации

        Returns:
            Список удаленных заявок
        """
        query = """
            SELECT o.*,
                   u1.first_name || ' ' || COALESCE(u1.last_name, '') as dispatcher_name,
                   u2.first_name || ' ' || COALESCE(u2.last_name, '') as master_name
            FROM orders o
            LEFT JOIN users u1 ON o.dispatcher_id = u1.telegram_id
            LEFT JOIN masters m ON o.assigned_master_id = m.id
            LEFT JOIN users u2 ON m.telegram_id = u2.telegram_id
            WHERE o.deleted_at IS NOT NULL
            ORDER BY o.deleted_at DESC
            LIMIT ? OFFSET ?
        """

        rows = await self._fetch_all(query, (limit, offset))
        return [self._row_to_order(row) for row in rows]

    # ===== ПОЛНАЯ ИСТОРИЯ ЗАЯВКИ =====

    async def get_full_history(self, order_id: int) -> dict:
        """
        Получение полной истории заявки

        Args:
            order_id: ID заявки

        Returns:
            Словарь с историей статусов, изменений полей и аудитом
        """
        # История статусов
        status_history = await self.get_status_history(order_id)

        # История изменений полей
        field_history_rows = await self._fetch_all(
            """
            SELECT
                eh.*,
                u.username,
                u.first_name,
                u.last_name
            FROM entity_history eh
            LEFT JOIN users u ON eh.changed_by = u.telegram_id
            WHERE eh.table_name = 'orders' AND eh.record_id = ?
            ORDER BY eh.changed_at DESC
            """,
            (order_id,),
        )

        # Аудит действий
        audit_logs_rows = await self._fetch_all(
            """
            SELECT
                al.*,
                u.username,
                u.first_name,
                u.last_name
            FROM audit_log al
            LEFT JOIN users u ON al.user_id = u.telegram_id
            WHERE al.details LIKE ?
            ORDER BY al.timestamp DESC
            """,
            (f"%Order #{order_id}%",),
        )

        return {
            "order_id": order_id,
            "status_history": status_history,
            "field_history": [dict(row) for row in field_history_rows],
            "audit_logs": [dict(row) for row in audit_logs_rows],
        }

    # ===== СТАТИСТИКА =====

    async def get_statistics(self, include_deleted: bool = False) -> dict:
        """
        Получение статистики по заявкам

        Args:
            include_deleted: Включать удаленные заявки

        Returns:
            Словарь со статистикой
        """
        where_clause = "" if include_deleted else "WHERE deleted_at IS NULL"

        # Общее количество
        total_row = await self._fetch_one(f"SELECT COUNT(*) as total FROM orders {where_clause}")  # nosec B608

        # По статусам
        status_rows = await self._fetch_all(  # nosec B608
            f"""
            SELECT status, COUNT(*) as count
            FROM orders
            {where_clause}
            GROUP BY status
            """
        )

        # Удаленные
        deleted_row = await self._fetch_one(
            "SELECT COUNT(*) as total FROM orders WHERE deleted_at IS NOT NULL"
        )

        return {
            "total": total_row["total"] if total_row else 0,
            "by_status": {row["status"]: row["count"] for row in status_rows},
            "deleted": deleted_row["total"] if deleted_row else 0,
        }

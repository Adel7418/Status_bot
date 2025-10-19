"""
Репозиторий для работы с заявками
"""

import logging
from datetime import datetime

import aiosqlite

from app.config import OrderStatus
from app.database.models import Order
from app.repositories.base import BaseRepository
from app.utils.helpers import MOSCOW_TZ, get_now


logger = logging.getLogger(__name__)


class OrderRepository(BaseRepository[Order]):
    """Репозиторий для работы с заявками"""

    async def create(
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
        Создание заявки

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
            Объект Order
        """
        now = get_now()
        cursor = await self._execute(
            """
            INSERT INTO orders (equipment_type, description, client_name, client_address,
                              client_phone, dispatcher_id, notes, scheduled_time, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                equipment_type,
                description,
                client_name,
                client_address,
                client_phone,
                dispatcher_id,
                notes,
                scheduled_time,
                now.isoformat(),
                now.isoformat(),
            ),
        )
        await self.db.commit()

        order = Order(
            id=cursor.lastrowid,
            equipment_type=equipment_type,
            description=description,
            client_name=client_name,
            client_address=client_address,
            client_phone=client_phone,
            dispatcher_id=dispatcher_id,
            notes=notes,
            scheduled_time=scheduled_time,
            status=OrderStatus.NEW,
            created_at=now,
            updated_at=now,
        )

        logger.info(f"Создана заявка #{order.id}")
        return order

    async def get_by_id(self, order_id: int) -> Order | None:
        """
        Получение заявки по ID

        Args:
            order_id: ID заявки

        Returns:
            Объект Order или None
        """
        row = await self._fetch_one(
            """
            SELECT o.*,
                   u1.first_name || ' ' || COALESCE(u1.last_name, '') as dispatcher_name,
                   u2.first_name || ' ' || COALESCE(u2.last_name, '') as master_name
            FROM orders o
            LEFT JOIN users u1 ON o.dispatcher_id = u1.telegram_id
            LEFT JOIN masters m ON o.assigned_master_id = m.id
            LEFT JOIN users u2 ON m.telegram_id = u2.telegram_id
            WHERE o.id = ?
            """,
            (order_id,),
        )

        if row:
            return self._row_to_order(row)
        return None

    async def get_all(
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
        params = []

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

        rows = await self._fetch_all(query, params)
        return [self._row_to_order(row) for row in rows]

    async def update_status(
        self, order_id: int, new_status: str, changed_by: int, notes: str | None = None
    ) -> bool:
        """
        Обновление статуса заявки

        Args:
            order_id: ID заявки
            new_status: Новый статус
            changed_by: Telegram ID пользователя, который изменил статус
            notes: Заметки

        Returns:
            True если обновление успешно
        """
        # Получаем текущий статус
        order = await self.get_by_id(order_id)
        if not order:
            logger.error(f"Заявка #{order_id} не найдена")
            return False

        old_status = order.status
        now = get_now()

        async with self.transaction():
            # Обновляем статус
            await self._execute(
                """
                UPDATE orders
                SET status = ?, updated_at = ?
                WHERE id = ?
                """,
                (new_status, now.isoformat(), order_id),
            )

            # Добавляем запись в историю
            await self._execute(
                """
                INSERT INTO order_status_history (order_id, old_status, new_status, changed_by, changed_at, notes)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (order_id, old_status, new_status, changed_by, now.isoformat(), notes),
            )

        logger.info(f"Статус заявки #{order_id} изменен: {old_status} → {new_status}")
        return True

    async def assign_master(self, order_id: int, master_id: int | None, changed_by: int) -> bool:
        """
        Назначение мастера на заявку

        Args:
            order_id: ID заявки
            master_id: ID мастера (или None для снятия)
            changed_by: Telegram ID пользователя

        Returns:
            True если назначение успешно
        """
        order = await self.get_by_id(order_id)
        if not order:
            logger.error(f"Заявка #{order_id} не найдена")
            return False

        now = get_now()

        async with self.transaction():
            await self._execute(
                """
                UPDATE orders
                SET assigned_master_id = ?, status = ?, updated_at = ?
                WHERE id = ?
                """,
                (master_id, OrderStatus.ASSIGNED, now.isoformat(), order_id),
            )

            # Добавляем запись в историю статусов
            await self._execute(
                """
                INSERT INTO order_status_history (order_id, old_status, new_status, changed_by, changed_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (order_id, order.status, OrderStatus.ASSIGNED, changed_by, now.isoformat()),
            )

        logger.info(f"Заявка #{order_id} назначена мастеру #{master_id}")
        return True

    async def update(self, order_id: int, updates: dict) -> bool:
        """
        Обновление заявки

        Args:
            order_id: ID заявки
            updates: Словарь с полями для обновления

        Returns:
            True если обновление успешно
        """
        if not updates:
            return False

        # Добавляем updated_at
        updates["updated_at"] = get_now().isoformat()

        # Формируем SET часть запроса
        set_parts = [f"{field} = ?" for field in updates.keys()]
        set_clause = ", ".join(set_parts)

        query = f"UPDATE orders SET {set_clause} WHERE id = ?"
        params = list(updates.values()) + [order_id]

        await self._execute_commit(query, params)
        logger.info(f"Заявка #{order_id} обновлена: {', '.join(updates.keys())}")
        return True

    async def get_by_master(self, master_id: int, status: str | None = None) -> list[Order]:
        """
        Получение заявок мастера

        Args:
            master_id: ID мастера
            status: Фильтр по статусу (опционально)

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
            WHERE o.assigned_master_id = ?
        """
        params = [master_id]

        if status:
            query += " AND o.status = ?"
            params.append(status)

        query += " ORDER BY o.created_at DESC"

        rows = await self._fetch_all(query, params)
        return [self._row_to_order(row) for row in rows]

    async def get_by_period(
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
        query = """
            SELECT o.*,
                   u1.first_name || ' ' || COALESCE(u1.last_name, '') as dispatcher_name,
                   u2.first_name || ' ' || COALESCE(u2.last_name, '') as master_name
            FROM orders o
            LEFT JOIN users u1 ON o.dispatcher_id = u1.telegram_id
            LEFT JOIN masters m ON o.assigned_master_id = m.id
            LEFT JOIN users u2 ON m.telegram_id = u2.telegram_id
            WHERE o.created_at >= ? AND o.created_at <= ?
        """
        params = [start_date.isoformat(), end_date.isoformat()]

        if status:
            query += " AND o.status = ?"
            params.append(status)

        query += " ORDER BY o.created_at DESC"

        rows = await self._fetch_all(query, params)
        return [self._row_to_order(row) for row in rows]

    async def get_status_history(self, order_id: int) -> list[dict]:
        """
        Получение истории изменения статусов заявки

        Args:
            order_id: ID заявки

        Returns:
            Список записей истории
        """
        rows = await self._fetch_all(
            """
            SELECT h.*, u.username, u.first_name, u.last_name
            FROM order_status_history h
            LEFT JOIN users u ON h.changed_by = u.telegram_id
            WHERE h.order_id = ?
            ORDER BY h.changed_at DESC
            """,
            (order_id,),
        )

        history = []
        for row in rows:
            history.append(
                {
                    "old_status": row["old_status"],
                    "new_status": row["new_status"],
                    "changed_by": row["changed_by"],
                    "changed_at": row["changed_at"],
                    "notes": row["notes"],
                    "username": row["username"],
                    "first_name": row["first_name"],
                    "last_name": row["last_name"],
                }
            )

        return history

    def _row_to_order(self, row: aiosqlite.Row) -> Order:
        """
        Преобразование строки БД в объект Order

        Args:
            row: Строка из БД

        Returns:
            Объект Order
        """
        return Order(
            id=row["id"],
            equipment_type=row["equipment_type"],
            description=row["description"],
            client_name=row["client_name"],
            client_address=row["client_address"],
            client_phone=row["client_phone"],
            status=row["status"],
            assigned_master_id=row["assigned_master_id"],
            dispatcher_id=row["dispatcher_id"],
            notes=row["notes"],
            scheduled_time=row["scheduled_time"],
            total_amount=(
                row["total_amount"]
                if "total_amount" in row.keys() and row["total_amount"] is not None
                else None
            ),
            materials_cost=(
                row["materials_cost"]
                if "materials_cost" in row.keys() and row["materials_cost"] is not None
                else None
            ),
            master_profit=(
                row["master_profit"]
                if "master_profit" in row.keys() and row["master_profit"] is not None
                else None
            ),
            company_profit=(
                row["company_profit"]
                if "company_profit" in row.keys() and row["company_profit"] is not None
                else None
            ),
            has_review=(
                bool(row["has_review"])
                if "has_review" in row.keys() and row["has_review"] is not None
                else None
            ),
            out_of_city=(
                bool(row["out_of_city"])
                if "out_of_city" in row.keys() and row["out_of_city"] is not None
                else None
            ),
            estimated_completion_date=(
                row["estimated_completion_date"]
                if "estimated_completion_date" in row.keys()
                and row["estimated_completion_date"] is not None
                else None
            ),
            prepayment_amount=(
                row["prepayment_amount"]
                if "prepayment_amount" in row.keys() and row["prepayment_amount"] is not None
                else None
            ),
            rescheduled_count=row.get("rescheduled_count", 0),
            last_rescheduled_at=(
                datetime.fromisoformat(row["last_rescheduled_at"]).replace(tzinfo=MOSCOW_TZ)
                if row.get("last_rescheduled_at")
                else None
            ),
            reschedule_reason=row.get("reschedule_reason"),
            created_at=(
                datetime.fromisoformat(row["created_at"]).replace(tzinfo=MOSCOW_TZ)
                if row["created_at"]
                else None
            ),
            updated_at=(
                datetime.fromisoformat(row["updated_at"]).replace(tzinfo=MOSCOW_TZ)
                if row["updated_at"]
                else None
            ),
            dispatcher_name=row.get("dispatcher_name"),
            master_name=row.get("master_name"),
        )

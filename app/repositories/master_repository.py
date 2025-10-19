"""
Репозиторий для работы с мастерами
"""

import logging
from datetime import datetime

import aiosqlite

from app.database.models import Master
from app.repositories.base import BaseRepository
from app.utils.helpers import MOSCOW_TZ, get_now


logger = logging.getLogger(__name__)


class MasterRepository(BaseRepository[Master]):
    """Репозиторий для работы с мастерами"""

    async def create(
        self,
        telegram_id: int,
        phone: str,
        specialization: str,
        is_active: bool = True,
        is_approved: bool = False,
    ) -> Master:
        """
        Создание мастера

        Args:
            telegram_id: Telegram ID
            phone: Телефон
            specialization: Специализация
            is_active: Активен ли мастер
            is_approved: Одобрен ли мастер

        Returns:
            Объект Master
        """
        now = get_now()
        cursor = await self._execute(
            """
            INSERT INTO masters (telegram_id, phone, specialization, is_active, is_approved, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (telegram_id, phone, specialization, is_active, is_approved, now.isoformat()),
        )
        await self.db.commit()

        master = Master(
            id=cursor.lastrowid,
            telegram_id=telegram_id,
            phone=phone,
            specialization=specialization,
            is_active=is_active,
            is_approved=is_approved,
            created_at=now,
        )

        logger.info(f"Создан мастер #{master.id} (telegram_id: {telegram_id})")
        return master

    async def get_by_telegram_id(self, telegram_id: int) -> Master | None:
        """
        Получение мастера по Telegram ID

        Args:
            telegram_id: Telegram ID

        Returns:
            Объект Master или None
        """
        row = await self._fetch_one(
            """
            SELECT m.*, u.username, u.first_name, u.last_name
            FROM masters m
            LEFT JOIN users u ON m.telegram_id = u.telegram_id
            WHERE m.telegram_id = ?
            """,
            (telegram_id,),
        )

        if row:
            return self._row_to_master(row)
        return None

    async def get_by_id(self, master_id: int) -> Master | None:
        """
        Получение мастера по ID

        Args:
            master_id: ID мастера

        Returns:
            Объект Master или None
        """
        row = await self._fetch_one(
            """
            SELECT m.*, u.username, u.first_name, u.last_name
            FROM masters m
            LEFT JOIN users u ON m.telegram_id = u.telegram_id
            WHERE m.id = ?
            """,
            (master_id,),
        )

        if row:
            return self._row_to_master(row)
        return None

    async def get_by_work_chat_id(self, work_chat_id: int) -> Master | None:
        """
        Получение мастера по ID рабочей группы

        Args:
            work_chat_id: ID рабочей группы

        Returns:
            Объект Master или None
        """
        row = await self._fetch_one(
            """
            SELECT m.*, u.username, u.first_name, u.last_name
            FROM masters m
            LEFT JOIN users u ON m.telegram_id = u.telegram_id
            WHERE m.work_chat_id = ?
            """,
            (work_chat_id,),
        )

        if row:
            return self._row_to_master(row)
        return None

    async def get_all(
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
        query = """
            SELECT m.*, u.username, u.first_name, u.last_name
            FROM masters m
            LEFT JOIN users u ON m.telegram_id = u.telegram_id
            WHERE 1=1
        """
        params = []

        if is_active is not None:
            query += " AND m.is_active = ?"
            params.append(1 if is_active else 0)

        if is_approved is not None:
            query += " AND m.is_approved = ?"
            params.append(1 if is_approved else 0)

        query += " ORDER BY m.created_at DESC"

        rows = await self._fetch_all(query, params)
        return [self._row_to_master(row) for row in rows]

    async def update(self, master_id: int, updates: dict) -> bool:
        """
        Обновление данных мастера

        Args:
            master_id: ID мастера
            updates: Словарь с полями для обновления

        Returns:
            True если обновление успешно
        """
        if not updates:
            return False

        # Формируем SET часть запроса
        set_parts = [f"{field} = ?" for field in updates.keys()]
        set_clause = ", ".join(set_parts)

        query = f"UPDATE masters SET {set_clause} WHERE id = ?"
        params = list(updates.values()) + [master_id]

        await self._execute_commit(query, params)
        logger.info(f"Мастер #{master_id} обновлен: {', '.join(updates.keys())}")
        return True

    async def update_by_telegram_id(self, telegram_id: int, updates: dict) -> bool:
        """
        Обновление данных мастера по Telegram ID

        Args:
            telegram_id: Telegram ID мастера
            updates: Словарь с полями для обновления

        Returns:
            True если обновление успешно
        """
        if not updates:
            return False

        # Формируем SET часть запроса
        set_parts = [f"{field} = ?" for field in updates.keys()]
        set_clause = ", ".join(set_parts)

        query = f"UPDATE masters SET {set_clause} WHERE telegram_id = ?"
        params = list(updates.values()) + [telegram_id]

        await self._execute_commit(query, params)
        logger.info(f"Мастер (telegram_id: {telegram_id}) обновлен: {', '.join(updates.keys())}")
        return True

    async def set_work_chat(self, master_id: int, work_chat_id: int) -> bool:
        """
        Установка рабочей группы для мастера

        Args:
            master_id: ID мастера
            work_chat_id: ID рабочей группы

        Returns:
            True если установка успешна
        """
        await self._execute_commit(
            """
            UPDATE masters
            SET work_chat_id = ?
            WHERE id = ?
            """,
            (work_chat_id, master_id),
        )

        logger.info(f"Мастеру #{master_id} установлена рабочая группа {work_chat_id}")
        return True

    async def approve(self, master_id: int) -> bool:
        """
        Одобрение мастера

        Args:
            master_id: ID мастера

        Returns:
            True если одобрение успешно
        """
        return await self.update(master_id, {"is_approved": 1})

    async def deactivate(self, master_id: int) -> bool:
        """
        Деактивация мастера

        Args:
            master_id: ID мастера

        Returns:
            True если деактивация успешна
        """
        return await self.update(master_id, {"is_active": 0})

    async def activate(self, master_id: int) -> bool:
        """
        Активация мастера

        Args:
            master_id: ID мастера

        Returns:
            True если активация успешна
        """
        return await self.update(master_id, {"is_active": 1})

    def _row_to_master(self, row: aiosqlite.Row) -> Master:
        """
        Преобразование строки БД в объект Master

        Args:
            row: Строка из БД

        Returns:
            Объект Master
        """
        return Master(
            id=row["id"],
            telegram_id=row["telegram_id"],
            phone=row["phone"],
            specialization=row["specialization"],
            is_active=bool(row["is_active"]),
            is_approved=bool(row["is_approved"]),
            work_chat_id=row["work_chat_id"] if row.get("work_chat_id") else None,
            created_at=(
                datetime.fromisoformat(row["created_at"]).replace(tzinfo=MOSCOW_TZ)
                if row["created_at"]
                else None
            ),
            username=row.get("username"),
            first_name=row.get("first_name"),
            last_name=row.get("last_name"),
        )

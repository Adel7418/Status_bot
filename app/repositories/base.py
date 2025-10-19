"""
Базовый репозиторий для работы с базой данных
"""

import logging
from contextlib import asynccontextmanager
from typing import Generic, TypeVar

import aiosqlite


logger = logging.getLogger(__name__)

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """
    Базовый класс для всех репозиториев
    Предоставляет общую функциональность для работы с БД
    """

    def __init__(self, db_connection: aiosqlite.Connection):
        """
        Инициализация репозитория

        Args:
            db_connection: Подключение к базе данных
        """
        self.db = db_connection

    @asynccontextmanager
    async def transaction(self):
        """
        Контекстный менеджер для транзакций

        Yields:
            aiosqlite.Connection: Подключение к БД
        """
        if not self.db:
            raise RuntimeError("База данных не подключена")

        await self.db.execute("BEGIN IMMEDIATE")
        try:
            yield self.db
            await self.db.commit()
            logger.debug("✅ Транзакция успешно завершена (commit)")
        except Exception as e:
            await self.db.rollback()
            logger.error(f"❌ Транзакция отменена (rollback): {e}")
            raise

    async def _execute(self, query: str, params: tuple | dict | None = None) -> aiosqlite.Cursor:
        """
        Выполнение SQL запроса

        Args:
            query: SQL запрос
            params: Параметры запроса

        Returns:
            Cursor с результатом
        """
        if params:
            return await self.db.execute(query, params)
        return await self.db.execute(query)

    async def _fetch_one(
        self, query: str, params: tuple | dict | None = None
    ) -> aiosqlite.Row | None:
        """
        Получение одной записи

        Args:
            query: SQL запрос
            params: Параметры запроса

        Returns:
            Строка результата или None
        """
        cursor = await self._execute(query, params)
        return await cursor.fetchone()

    async def _fetch_all(
        self, query: str, params: tuple | dict | None = None
    ) -> list[aiosqlite.Row]:
        """
        Получение всех записей

        Args:
            query: SQL запрос
            params: Параметры запроса

        Returns:
            Список строк результата
        """
        cursor = await self._execute(query, params)
        return await cursor.fetchall()

    async def _execute_commit(self, query: str, params: tuple | dict | None = None) -> int:
        """
        Выполнение запроса с коммитом (INSERT, UPDATE, DELETE)

        Args:
            query: SQL запрос
            params: Параметры запроса

        Returns:
            ID последней вставленной записи или количество измененных строк
        """
        cursor = await self._execute(query, params)
        await self.db.commit()
        return cursor.lastrowid if cursor.lastrowid else cursor.rowcount

"""
Репозиторий для работы с пользователями
"""

import logging
from datetime import datetime

import aiosqlite

from app.database.models import User
from app.repositories.base import BaseRepository
from app.utils.helpers import MOSCOW_TZ, get_now


logger = logging.getLogger(__name__)


class UserRepository(BaseRepository[User]):
    """Репозиторий для работы с пользователями"""

    async def get_or_create(
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
        # Проверяем существование пользователя
        user = await self.get_by_telegram_id(telegram_id)

        if user:
            # Обновляем данные при изменении
            updates_needed = False
            if username and user.username != username:
                user.username = username
                updates_needed = True
            if first_name and user.first_name != first_name:
                user.first_name = first_name
                updates_needed = True
            if last_name and user.last_name != last_name:
                user.last_name = last_name
                updates_needed = True

            if updates_needed:
                await self._execute_commit(
                    """
                    UPDATE users
                    SET username = ?, first_name = ?, last_name = ?
                    WHERE telegram_id = ?
                    """,
                    (user.username, user.first_name, user.last_name, telegram_id),
                )
            return user

        # Создаем нового пользователя
        now = get_now()
        cursor = await self._execute(
            """
            INSERT INTO users (telegram_id, username, first_name, last_name, role, created_at)
            VALUES (?, ?, ?, ?, 'UNKNOWN', ?)
            """,
            (telegram_id, username, first_name, last_name, now.isoformat()),
        )
        await self.db.commit()

        user = User(
            id=cursor.lastrowid,
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            role="UNKNOWN",
            created_at=now,
        )

        logger.info(f"Создан пользователь: {telegram_id}")
        return user

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        """
        Получение пользователя по Telegram ID

        Args:
            telegram_id: Telegram ID

        Returns:
            Объект User или None
        """
        row = await self._fetch_one(
            """
            SELECT * FROM users WHERE telegram_id = ?
            """,
            (telegram_id,),
        )

        if row:
            return self._row_to_user(row)
        return None

    async def get_by_id(self, user_id: int) -> User | None:
        """
        Получение пользователя по ID

        Args:
            user_id: ID пользователя

        Returns:
            Объект User или None
        """
        row = await self._fetch_one(
            """
            SELECT * FROM users WHERE id = ?
            """,
            (user_id,),
        )

        if row:
            return self._row_to_user(row)
        return None

    async def get_all_by_role(self, role: str) -> list[User]:
        """
        Получение всех пользователей с определенной ролью

        Args:
            role: Роль для фильтрации

        Returns:
            Список пользователей
        """
        rows = await self._fetch_all(
            """
            SELECT * FROM users WHERE role LIKE ?
            """,
            (f"%{role}%",),
        )

        return [self._row_to_user(row) for row in rows]

    async def add_role(self, telegram_id: int, role: str) -> bool:
        """
        Добавление роли пользователю

        Args:
            telegram_id: Telegram ID пользователя
            role: Роль для добавления

        Returns:
            True если роль добавлена
        """
        user = await self.get_by_telegram_id(telegram_id)
        if not user:
            logger.error(f"Пользователь {telegram_id} не найден")
            return False

        # Используем метод модели для добавления роли
        new_roles = user.add_role(role)

        async with self.transaction():
            await self._execute(
                """
                UPDATE users
                SET role = ?
                WHERE telegram_id = ?
                """,
                (new_roles, telegram_id),
            )

        logger.info(f"Роль {role} добавлена пользователю {telegram_id}")
        return True

    async def remove_role(self, telegram_id: int, role: str) -> bool:
        """
        Удаление роли у пользователя

        Args:
            telegram_id: Telegram ID пользователя
            role: Роль для удаления

        Returns:
            True если роль удалена
        """
        user = await self.get_by_telegram_id(telegram_id)
        if not user:
            logger.error(f"Пользователь {telegram_id} не найден")
            return False

        # Используем метод модели для удаления роли
        new_roles = user.remove_role(role)

        async with self.transaction():
            await self._execute(
                """
                UPDATE users
                SET role = ?
                WHERE telegram_id = ?
                """,
                (new_roles, telegram_id),
            )

        logger.info(f"Роль {role} удалена у пользователя {telegram_id}")
        return True

    async def update(self, telegram_id: int, updates: dict) -> bool:
        """
        Обновление данных пользователя

        Args:
            telegram_id: Telegram ID пользователя
            updates: Словарь с полями для обновления

        Returns:
            True если обновление успешно
        """
        if not updates:
            return False

        # Формируем SET часть запроса
        set_parts = [f"{field} = ?" for field in updates]
        set_clause = ", ".join(set_parts)

        query = f"UPDATE users SET {set_clause} WHERE telegram_id = ?"  # nosec B608
        params = [*list(updates.values()), telegram_id]

        await self._execute_commit(query, tuple(params))
        logger.info(f"Пользователь {telegram_id} обновлен: {', '.join(updates.keys())}")
        return True

    def _row_to_user(self, row: aiosqlite.Row) -> User:
        """
        Преобразование строки БД в объект User

        Args:
            row: Строка из БД

        Returns:
            Объект User
        """
        return User(
            id=row["id"],
            telegram_id=row["telegram_id"],
            username=row["username"],
            first_name=row["first_name"],
            last_name=row["last_name"],
            role=row["role"],
            created_at=(
                datetime.fromisoformat(row["created_at"]).replace(tzinfo=MOSCOW_TZ)
                if row["created_at"]
                else None
            ),
        )

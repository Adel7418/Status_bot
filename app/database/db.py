"""
Работа с базой данных
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import TYPE_CHECKING, Any, cast

import aiosqlite

from app.config import Config, OrderStatus, UserRole
from app.database.models import (
    AuditLog,
    FinancialReport,
    Master,
    MasterFinancialReport,
    Order,
    User,
)
from app.domain.order_state_machine import InvalidStateTransitionError, OrderStateMachine
from app.utils.helpers import MOSCOW_TZ, get_now


if TYPE_CHECKING:
    from app.services.service_factory import ServiceFactory


logger = logging.getLogger(__name__)


class Database:
    """Класс для работы с базой данных"""

    def __init__(self, db_path: str | None = None):
        """
        Инициализация

        Args:
            db_path: Путь к файлу базы данных
        """
        self.db_path = db_path or Config.DATABASE_PATH
        self.connection: aiosqlite.Connection | None = None
        self._service_factory: ServiceFactory | None = None

    def _get_connection(self) -> aiosqlite.Connection:
        """
        Внутренний помощник для получения активного соединения.

        Гарантирует, что соединение инициализировано, чтобы mypy не видел None.
        """
        if self.connection is None:
            raise RuntimeError("База данных не подключена")
        return self.connection

    def get_connection(self) -> aiosqlite.Connection:
        """
        Публичный accessor для безопасного доступа к соединению.

        Используется сервисами/репозиториями вместо обращения к self.connection напрямую.
        """
        return self._get_connection()

    async def connect(self):
        """Подключение к базе данных"""
        connection = await aiosqlite.connect(self.db_path)
        connection.row_factory = aiosqlite.Row
        # Устанавливаем isolation_level для правильной работы транзакций
        await connection.execute("PRAGMA journal_mode=WAL")
        self.connection = connection
        logger.info("Подключено к базе данных: %s", self.db_path)

    async def disconnect(self):
        """Отключение от базы данных"""
        connection = self.connection
        if connection:
            await connection.close()
            logger.info("Отключено от базы данных")

    @property
    def services(self):
        """
        Получение Service Factory для доступа к сервисам

        Returns:
            ServiceFactory: Фабрика сервисов
        """
        if self._service_factory is None:
            from app.services.service_factory import ServiceFactory

            connection = self._get_connection()
            self._service_factory = ServiceFactory(connection)
        return self._service_factory

    @asynccontextmanager
    async def transaction(self):
        """
        Context manager для транзакционной изоляции

        Использует BEGIN IMMEDIATE для предотвращения race conditions в SQLite.
        Автоматически делает commit при успехе или rollback при ошибке.

        Usage:
            async with db.transaction():
                # Все операции внутри этого блока атомарны
                await db.connection.execute(...)
                await db.connection.execute(...)
                # commit выполнится автоматически

        Raises:
            Exception: Любая ошибка внутри транзакции вызовет rollback
        """
        connection = self._get_connection()

        # BEGIN IMMEDIATE получает эксклюзивную блокировку сразу
        # Это предотвращает race conditions в SQLite
        await connection.execute("BEGIN IMMEDIATE")
        try:
            yield connection
            await connection.commit()
            logger.debug("✅ Транзакция успешно завершена (commit)")
        except Exception as e:
            await connection.rollback()
            logger.error(f"❌ Транзакция отменена (rollback): {e}")
            raise

    async def init_db(self):
        """
        Инициализация базы данных

        ВАЖНО: Схема БД управляется через Alembic миграции!
        Этот метод только проверяет существование таблиц для обратной совместимости.

        Для применения миграций используйте:
        $ alembic upgrade head
        """
        if not self.connection:
            await self.connect()

        connection = self._get_connection()

        # Проверяем существование основной таблицы users
        cursor = await connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
        )
        table_exists = await cursor.fetchone()

        if not table_exists:
            logger.warning("⚠️  Таблицы БД не найдены! " "Запустите миграции: alembic upgrade head")
            # Создаем базовую схему для обратной совместимости
            await self._create_legacy_schema()
        else:
            logger.info("[OK] База данных инициализирована (схема существует)")

        # Создание индексов для оптимизации запросов
        await self._create_indexes()

    async def _create_legacy_schema(self):
        """
        Создание базовой схемы для обратной совместимости
        DEPRECATED: Используйте Alembic миграции!
        """
        logger.warning("⚠️  Создание legacy схемы. Рекомендуется использовать Alembic!")

        # Минимальная схема для работы
        connection = self._get_connection()

        await connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                role TEXT DEFAULT 'UNKNOWN',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        await connection.execute(
            """
            CREATE TABLE IF NOT EXISTS masters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                phone TEXT NOT NULL,
                specialization TEXT NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                is_approved BOOLEAN DEFAULT 0,
                work_chat_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
            )
        """
        )

        await connection.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                equipment_type TEXT NOT NULL,
                description TEXT NOT NULL,
                client_name TEXT NOT NULL,
                client_address TEXT NOT NULL,
                client_phone TEXT NOT NULL,
                status TEXT DEFAULT 'NEW',
                assigned_master_id INTEGER,
                dispatcher_id INTEGER,
                notes TEXT,
                scheduled_time TEXT,
                total_amount REAL,
                materials_cost REAL,
                master_profit REAL,
                company_profit REAL,
                has_review INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (assigned_master_id) REFERENCES masters(id),
                FOREIGN KEY (dispatcher_id) REFERENCES users(telegram_id)
            )
        """
        )

        await connection.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT NOT NULL,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(telegram_id)
            )
        """
        )

        await connection.execute(
            """
            CREATE TABLE IF NOT EXISTS order_status_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                old_status TEXT,
                new_status TEXT NOT NULL,
                changed_by INTEGER,
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT,
                FOREIGN KEY (order_id) REFERENCES orders(id),
                FOREIGN KEY (changed_by) REFERENCES users(telegram_id)
            )
        """
        )

        await connection.commit()
        logger.info("[OK] Legacy схема создана")

    async def _create_indexes(self):
        """Создание индексов для оптимизации"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id)",
            "CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)",
            "CREATE INDEX IF NOT EXISTS idx_masters_telegram_id ON masters(telegram_id)",
            "CREATE INDEX IF NOT EXISTS idx_masters_is_approved ON masters(is_approved)",
            "CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)",
            "CREATE INDEX IF NOT EXISTS idx_orders_assigned_master_id ON orders(assigned_master_id)",
            "CREATE INDEX IF NOT EXISTS idx_orders_dispatcher_id ON orders(dispatcher_id)",
            "CREATE INDEX IF NOT EXISTS idx_audit_user_id ON audit_log(user_id)",
        ]

        connection = self._get_connection()

        for index_sql in indexes:
            await connection.execute(index_sql)

        await connection.commit()

    # ==================== USERS ====================

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
        connection = self._get_connection()

        # Проверяем существование пользователя
        user = await self.get_user_by_telegram_id(telegram_id)

        if user:
            # Обновляем информацию если изменилась
            if (
                user.username != username
                or user.first_name != first_name
                or user.last_name != last_name
            ):
                await connection.execute(
                    """
                    UPDATE users
                    SET username = ?, first_name = ?, last_name = ?
                    WHERE telegram_id = ?
                    """,
                    (username, first_name, last_name, telegram_id),
                )
                await connection.commit()
                user.username = username
                user.first_name = first_name
                user.last_name = last_name

            # Проверяем и обновляем роль на основе конфигурации
            roles_updated = False
            current_roles = user.get_roles()
            logger.info(
                f"Проверка ролей для пользователя {telegram_id}: "
                f"текущие роли={current_roles}, "
                f"ADMIN_IDS={Config.ADMIN_IDS}, "
                f"DISPATCHER_IDS={Config.DISPATCHER_IDS}"
            )

            # Добавляем роль ADMIN, если пользователь в ADMIN_IDS
            if telegram_id in Config.ADMIN_IDS and not user.has_role(UserRole.ADMIN):
                user.add_role(UserRole.ADMIN)
                roles_updated = True
                logger.info(f"Автоматически добавлена роль ADMIN пользователю {telegram_id}")
            # Убираем роль ADMIN, если пользователя нет в ADMIN_IDS
            elif telegram_id not in Config.ADMIN_IDS and user.has_role(UserRole.ADMIN):
                user.remove_role(UserRole.ADMIN)
                roles_updated = True
                logger.info(f"Автоматически удалена роль ADMIN у пользователя {telegram_id}")

            # Добавляем роль DISPATCHER, если пользователь в DISPATCHER_IDS
            if telegram_id in Config.DISPATCHER_IDS and not user.has_role(UserRole.DISPATCHER):
                user.add_role(UserRole.DISPATCHER)
                roles_updated = True
                logger.info(
                    f"Автоматически добавлена роль DISPATCHER пользователю {telegram_id} "
                    f"(ID найден в DISPATCHER_IDS={Config.DISPATCHER_IDS})"
                )
            # Убираем роль DISPATCHER, если пользователя нет в DISPATCHER_IDS
            elif telegram_id not in Config.DISPATCHER_IDS and user.has_role(UserRole.DISPATCHER):
                user.remove_role(UserRole.DISPATCHER)
                roles_updated = True
                logger.info(
                    f"Автоматически удалена роль DISPATCHER у пользователя {telegram_id} "
                    f"(ID не найден в DISPATCHER_IDS={Config.DISPATCHER_IDS})"
                )
            else:
                logger.info(
                    f"Роль DISPATCHER для пользователя {telegram_id} не изменилась: "
                    f"в DISPATCHER_IDS={telegram_id in Config.DISPATCHER_IDS}, "
                    f"имеет роль={user.has_role(UserRole.DISPATCHER)}"
                )

            # Обновляем роль в базе данных, если она изменилась
            if roles_updated:
                await connection.execute(
                    "UPDATE users SET role = ? WHERE telegram_id = ?",
                    (user.role, telegram_id),
                )
                await connection.commit()
                final_roles = user.get_roles()
                logger.info(
                    f"Роль пользователя {telegram_id} обновлена: {current_roles} -> {final_roles}"
                )
                logger.info(
                    f"Проверка сохранения роли для пользователя {telegram_id}: "
                    f"role в БД='{user.role}', roles={final_roles}, "
                    f"has DISPATCHER={user.has_role(UserRole.DISPATCHER)}"
                )
                # Перезагружаем пользователя из БД для проверки
                reloaded_user = await self.get_user_by_telegram_id(telegram_id)
                if reloaded_user:
                    logger.info(
                        f"Проверка после перезагрузки для пользователя {telegram_id}: "
                        f"role в БД='{reloaded_user.role}', roles={reloaded_user.get_roles()}"
                    )
                    # Используем перезагруженного пользователя
                    user = reloaded_user

            return user

        # Определяем роли (может быть несколько ролей)
        roles = []
        if telegram_id in Config.ADMIN_IDS:
            roles.append(UserRole.ADMIN)
        if telegram_id in Config.DISPATCHER_IDS:
            roles.append(UserRole.DISPATCHER)
        if not roles:
            roles = [UserRole.UNKNOWN]

        # Формируем строку ролей
        role_str = ",".join(sorted(roles))

        # Создаем нового пользователя
        cursor = await connection.execute(
            """
            INSERT INTO users (telegram_id, username, first_name, last_name, role)
            VALUES (?, ?, ?, ?, ?)
            """,
            (telegram_id, username, first_name, last_name, role_str),
        )
        await connection.commit()

        user = User(
            id=cursor.lastrowid,
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            role=role_str,
            created_at=get_now(),
        )

        logger.info("Создан новый пользователь: %s с ролями %s", telegram_id, roles)
        return user

    async def get_user_by_telegram_id(self, telegram_id: int) -> User | None:
        """
        Получение пользователя по Telegram ID

        Args:
            telegram_id: Telegram ID

        Returns:
            Объект User или None
        """
        connection = self._get_connection()

        cursor = await connection.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        )
        row = await cursor.fetchone()

        if row:
            return User(
                id=row["id"],
                telegram_id=row["telegram_id"],
                username=row["username"],
                first_name=row["first_name"],
                last_name=row["last_name"],
                role=row["role"],
                created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
            )
        return None

    async def update_user_role(self, telegram_id: int, role: str) -> bool:
        """
        Обновление роли пользователя (устанавливает одну роль, заменяя все существующие)

        Args:
            telegram_id: Telegram ID
            role: Новая роль

        Returns:
            True если успешно
        """
        connection = self._get_connection()

        await connection.execute(
            "UPDATE users SET role = ? WHERE telegram_id = ?", (role, telegram_id)
        )
        await connection.commit()
        logger.info("Роль пользователя %s изменена на %s", telegram_id, role)
        return True

    async def add_user_role(self, telegram_id: int, role: str) -> bool:
        """
        Добавление роли пользователю (не удаляя существующие)

        Использует транзакционную изоляцию для предотвращения race conditions.

        Args:
            telegram_id: Telegram ID
            role: Роль для добавления

        Returns:
            True если успешно
        """
        async with self.transaction():
            connection = self._get_connection()
            user = await self.get_user_by_telegram_id(telegram_id)
            if not user:
                logger.error(f"Пользователь {telegram_id} не найден")
                return False

            # Используем метод модели для добавления роли
            new_roles = user.add_role(role)

            await connection.execute(
                "UPDATE users SET role = ? WHERE telegram_id = ?", (new_roles, telegram_id)
            )
            # commit() выполнится автоматически

        logger.info("Роль %s добавлена пользователю %s. Роли: %s", role, telegram_id, new_roles)
        return True

    async def remove_user_role(self, telegram_id: int, role: str) -> bool:
        """
        Удаление роли у пользователя

        Использует транзакционную изоляцию для предотвращения race conditions.

        Args:
            telegram_id: Telegram ID
            role: Роль для удаления

        Returns:
            True если успешно
        """
        async with self.transaction():
            connection = self._get_connection()
            user = await self.get_user_by_telegram_id(telegram_id)
            if not user:
                logger.error(f"Пользователь {telegram_id} не найден")
                return False

            # Используем метод модели для удаления роли
            new_roles = user.remove_role(role)

            await connection.execute(
                "UPDATE users SET role = ? WHERE telegram_id = ?", (new_roles, telegram_id)
            )
            # commit() выполнится автоматически

        logger.info(f"Роль {role} удалена у пользователя {telegram_id}. Роли: {new_roles}")
        return True

    async def set_user_roles(self, telegram_id: int, roles: list[str]) -> bool:
        """
        Установка списка ролей пользователю (заменяет все существующие)

        Args:
            telegram_id: Telegram ID
            roles: Список ролей

        Returns:
            True если успешно
        """
        if not roles:
            roles = ["UNKNOWN"]

        roles_str = ",".join(sorted(set(roles)))

        connection = self._get_connection()

        await connection.execute(
            "UPDATE users SET role = ? WHERE telegram_id = ?", (roles_str, telegram_id)
        )
        await connection.commit()
        logger.info(f"Роли пользователя {telegram_id} установлены: {roles_str}")
        return True

    async def get_all_users(self) -> list[User]:
        """
        Получение всех пользователей

        Returns:
            Список пользователей
        """
        connection = self._get_connection()

        cursor = await connection.execute("SELECT * FROM users ORDER BY created_at DESC")
        rows = await cursor.fetchall()

        users = []
        for row in rows:
            users.append(
                User(
                    id=row["id"],
                    telegram_id=row["telegram_id"],
                    username=row["username"],
                    first_name=row["first_name"],
                    last_name=row["last_name"],
                    role=row["role"],
                    created_at=(
                        datetime.fromisoformat(row["created_at"]) if row["created_at"] else None
                    ),
                )
            )
        return users

    async def get_users_by_role(self, role: str) -> list[User]:
        """
        Получение всех пользователей с определенной ролью

        Args:
            role: Роль для фильтрации (например, "ADMIN", "DISPATCHER", "MASTER")

        Returns:
            Список пользователей с указанной ролью
        """
        users = await self.get_all_users()
        result = []

        for user in users:
            if user.has_role(role):
                result.append(user)

        return result

    async def get_admins_and_dispatchers(self, exclude_user_id: int | None = None) -> list[User]:
        """
        Получение всех админов и диспетчеров

        Args:
            exclude_user_id: ID пользователя для исключения (например, создателя заявки)

        Returns:
            Список пользователей с ролями ADMIN или DISPATCHER
        """
        users = await self.get_all_users()
        result = []

        for user in users:
            # Проверяем, есть ли у пользователя роль админа или диспетчера
            if user.has_role(UserRole.ADMIN) or user.has_role(UserRole.DISPATCHER):
                # Исключаем указанного пользователя если нужно
                if exclude_user_id and user.telegram_id == exclude_user_id:
                    continue
                result.append(user)

        return result

    # ==================== MASTERS ====================

    async def create_master(
        self, telegram_id: int, phone: str, specialization: str, is_approved: bool = False
    ) -> Master:
        """
        Создание мастера

        Args:
            telegram_id: Telegram ID
            phone: Телефон
            specialization: Специализация
            is_approved: Одобрен ли

        Returns:
            Объект Master
        """
        connection = self._get_connection()

        cursor = await connection.execute(
            """
            INSERT INTO masters (telegram_id, phone, specialization, is_approved)
            VALUES (?, ?, ?, ?)
            """,
            (telegram_id, phone, specialization, is_approved),
        )
        await connection.commit()

        master = Master(
            id=cursor.lastrowid,
            telegram_id=telegram_id,
            phone=phone,
            specialization=specialization,
            is_approved=is_approved,
            created_at=get_now(),
        )

        logger.info(f"Создан мастер: {telegram_id}")
        return master

    async def get_master_by_telegram_id(self, telegram_id: int) -> Master | None:
        """
        Получение мастера по Telegram ID

        Args:
            telegram_id: Telegram ID

        Returns:
            Объект Master или None
        """
        connection = self._get_connection()

        cursor = await connection.execute(
            """
            SELECT m.*, u.username, u.first_name, u.last_name
            FROM masters m
            LEFT JOIN users u ON m.telegram_id = u.telegram_id
            WHERE m.telegram_id = ?
            """,
            (telegram_id,),
        )
        row = await cursor.fetchone()

        if row:
            return Master(
                id=row["id"],
                telegram_id=row["telegram_id"],
                phone=row["phone"],
                specialization=row["specialization"],
                is_active=bool(row["is_active"]),
                is_approved=bool(row["is_approved"]),
                work_chat_id=(row["work_chat_id"] if row["work_chat_id"] is not None else None),
                created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
                username=row["username"],
                first_name=row["first_name"],
                last_name=row["last_name"],
            )
        return None

    async def get_master_by_id(self, master_id: int) -> Master | None:
        """
        Получение мастера по ID

        Args:
            master_id: ID мастера

        Returns:
            Объект Master или None
        """
        connection = self._get_connection()

        cursor = await connection.execute(
            """
            SELECT m.*, u.username, u.first_name, u.last_name
            FROM masters m
            LEFT JOIN users u ON m.telegram_id = u.telegram_id
            WHERE m.id = ?
            """,
            (master_id,),
        )
        row = await cursor.fetchone()

        if row:
            return Master(
                id=row["id"],
                telegram_id=row["telegram_id"],
                phone=row["phone"],
                specialization=row["specialization"],
                is_active=bool(row["is_active"]),
                is_approved=bool(row["is_approved"]),
                work_chat_id=(row["work_chat_id"] if row["work_chat_id"] is not None else None),
                created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
                username=row["username"],
                first_name=row["first_name"],
                last_name=row["last_name"],
            )
        return None

    async def get_master_by_work_chat_id(self, work_chat_id: int) -> Master | None:
        """
        Получение мастера по ID рабочей группы

        Args:
            work_chat_id: ID рабочей группы

        Returns:
            Объект Master или None
        """
        connection = self._get_connection()

        cursor = await connection.execute(
            """
            SELECT m.*, u.username, u.first_name, u.last_name
            FROM masters m
            LEFT JOIN users u ON m.telegram_id = u.telegram_id
            WHERE m.work_chat_id = ?
            """,
            (work_chat_id,),
        )
        row = await cursor.fetchone()

        if row:
            return Master(
                id=row["id"],
                telegram_id=row["telegram_id"],
                phone=row["phone"],
                specialization=row["specialization"],
                is_active=bool(row["is_active"]),
                is_approved=bool(row["is_approved"]),
                work_chat_id=(row["work_chat_id"] if row["work_chat_id"] is not None else None),
                created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
                username=row["username"],
                first_name=row["first_name"],
                last_name=row["last_name"],
            )
        return None

    async def get_all_masters(
        self, only_approved: bool = False, only_active: bool = False
    ) -> list[Master]:
        """
        Получение всех мастеров

        Args:
            only_approved: Только одобренные
            only_active: Только активные

        Returns:
            Список мастеров
        """
        query = """
            SELECT m.*, u.username, u.first_name, u.last_name
            FROM masters m
            LEFT JOIN users u ON m.telegram_id = u.telegram_id
            WHERE 1=1
        """
        params: list[Any] = []

        if only_approved:
            query += " AND m.is_approved = 1"
        if only_active:
            query += " AND m.is_active = 1"

        query += " ORDER BY m.created_at DESC"

        connection = self._get_connection()

        cursor = await connection.execute(query, params)
        rows = await cursor.fetchall()

        masters = []
        for row in rows:
            masters.append(
                Master(
                    id=row["id"],
                    telegram_id=row["telegram_id"],
                    phone=row["phone"],
                    specialization=row["specialization"],
                    is_active=bool(row["is_active"]),
                    is_approved=bool(row["is_approved"]),
                    work_chat_id=(row["work_chat_id"] if row["work_chat_id"] is not None else None),
                    created_at=(
                        datetime.fromisoformat(row["created_at"]) if row["created_at"] else None
                    ),
                    username=row["username"],
                    first_name=row["first_name"],
                    last_name=row["last_name"],
                )
            )
        return masters

    async def update_master_status(self, telegram_id: int, is_active: bool) -> bool:
        """
        Обновление статуса активности мастера

        Args:
            telegram_id: Telegram ID мастера
            is_active: Статус активности

        Returns:
            True если успешно
        """
        connection = self._get_connection()

        await connection.execute(
            "UPDATE masters SET is_active = ? WHERE telegram_id = ?", (is_active, telegram_id)
        )
        await connection.commit()

        logger.info(
            f"Статус мастера {telegram_id} изменен на {'активный' if is_active else 'неактивный'}"
        )
        return True

    async def update_master_work_chat(self, telegram_id: int, work_chat_id: int | None) -> bool:
        """
        Обновление ID рабочей группы мастера

        Args:
            telegram_id: Telegram ID мастера
            work_chat_id: ID рабочей группы (None для сброса)

        Returns:
            True если успешно
        """
        # Логируем перед обновлением
        logger.info(f"Updating work_chat_id for master {telegram_id} to {work_chat_id}")

        connection = self._get_connection()

        await connection.execute(
            "UPDATE masters SET work_chat_id = ? WHERE telegram_id = ?", (work_chat_id, telegram_id)
        )
        await connection.commit()

        # Проверяем результат обновления
        cursor = await connection.execute(
            "SELECT work_chat_id FROM masters WHERE telegram_id = ?", (telegram_id,)
        )
        result = await cursor.fetchone()
        actual_work_chat_id = result["work_chat_id"] if result else None

        logger.info(
            f"Work chat для мастера {telegram_id} установлен: {work_chat_id}, фактически в БД: {actual_work_chat_id}"
        )
        return True

    # ==================== ORDERS ====================

    async def create_order(
        self,
        equipment_type: str,
        description: str,
        client_name: str,
        client_address: str,
        client_phone: str,
        dispatcher_id: int,
        master_lead_name: str | None = None,
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
            master_lead_name: Имя мастера-источника лида
            notes: Заметки
            scheduled_time: Время прибытия к клиенту

        Returns:
            Объект Order
        """
        connection = self._get_connection()

        now = get_now()
        cursor = await connection.execute(
            """
            INSERT INTO orders (equipment_type, description, client_name, client_address,
                              client_phone, master_lead_name, dispatcher_id, notes, scheduled_time, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                equipment_type,
                description,
                client_name,
                client_address,
                client_phone,
                master_lead_name,
                dispatcher_id,
                notes,
                scheduled_time,
                now.isoformat(),
                now.isoformat(),
            ),
        )
        await connection.commit()

        order = Order(
            id=cursor.lastrowid,
            equipment_type=equipment_type,
            description=description,
            client_name=client_name,
            client_address=client_address,
            client_phone=client_phone,
            master_lead_name=master_lead_name,
            dispatcher_id=dispatcher_id,
            notes=notes,
            scheduled_time=scheduled_time,
            status=OrderStatus.NEW,
            created_at=now,
            updated_at=now,
        )

        logger.info(f"Создана заявка #{order.id}")

        return order

    async def get_order_by_id(self, order_id: int) -> Order | None:
        """
        Получение заявки по ID

        Args:
            order_id: ID заявки

        Returns:
            Объект Order или None
        """
        connection = self._get_connection()

        cursor = await connection.execute(
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
        row = await cursor.fetchone()

        if row:
            return Order(
                id=row["id"],
                equipment_type=row["equipment_type"],
                description=row["description"],
                client_name=row["client_name"],
                client_address=row["client_address"],
                client_phone=row["client_phone"],
                master_lead_name=(
                    row["master_lead_name"]
                    if "master_lead_name" in row and row["master_lead_name"] is not None
                    else None
                ),
                status=row["status"],
                assigned_master_id=row["assigned_master_id"],
                dispatcher_id=row["dispatcher_id"],
                notes=row["notes"],
                scheduled_time=row["scheduled_time"],
                total_amount=(
                    row["total_amount"]
                    if "total_amount" in row and row["total_amount"] is not None
                    else None
                ),
                materials_cost=(
                    row["materials_cost"]
                    if "materials_cost" in row and row["materials_cost"] is not None
                    else None
                ),
                master_profit=(
                    row["master_profit"]
                    if "master_profit" in row and row["master_profit"] is not None
                    else None
                ),
                company_profit=(
                    row["company_profit"]
                    if "company_profit" in row and row["company_profit"] is not None
                    else None
                ),
                has_review=(
                    bool(row["has_review"])
                    if "has_review" in row and row["has_review"] is not None
                    else None
                ),
                out_of_city=(
                    bool(row["out_of_city"])
                    if "out_of_city" in row and row["out_of_city"] is not None
                    else None
                ),
                estimated_completion_date=(
                    row["estimated_completion_date"]
                    if "estimated_completion_date" in row
                    and row["estimated_completion_date"] is not None
                    else None
                ),
                prepayment_amount=(
                    row["prepayment_amount"]
                    if "prepayment_amount" in row and row["prepayment_amount"] is not None
                    else None
                ),
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
                dispatcher_name=row["dispatcher_name"],
                master_name=row["master_name"],
            )
        return None

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
        query = """
            SELECT o.*,
                   u1.first_name || ' ' || COALESCE(u1.last_name, '') as dispatcher_name,
                   u2.first_name || ' ' || COALESCE(u2.last_name, '') as master_name
            FROM orders o
            LEFT JOIN users u1 ON o.dispatcher_id = u1.telegram_id
            LEFT JOIN masters m ON o.assigned_master_id = m.id
            LEFT JOIN users u2 ON m.telegram_id = u2.telegram_id
            WHERE o.deleted_at IS NULL
        """
        params: list[Any] = []

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

        connection = self._get_connection()

        cursor = await connection.execute(query, params)
        rows = await cursor.fetchall()

        orders = []
        for row in rows:
            orders.append(
                Order(
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
                    scheduled_time=(
                        row["scheduled_time"]
                        if row["scheduled_time"] is not None
                        and str(row["scheduled_time"]).strip() != "None"
                        else None
                    ),
                    total_amount=(
                        row["total_amount"]
                        if "total_amount" in row and row["total_amount"] is not None
                        else None
                    ),
                    materials_cost=(
                        row["materials_cost"]
                        if "materials_cost" in row and row["materials_cost"] is not None
                        else None
                    ),
                    master_profit=(
                        row["master_profit"]
                        if "master_profit" in row and row["master_profit"] is not None
                        else None
                    ),
                    company_profit=(
                        row["company_profit"]
                        if "company_profit" in row and row["company_profit"] is not None
                        else None
                    ),
                    has_review=(
                        bool(row["has_review"])
                        if "has_review" in row and row["has_review"] is not None
                        else None
                    ),
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
                    dispatcher_name=row["dispatcher_name"],
                    master_name=row["master_name"],
                )
            )
        return orders

    async def update_order_status(
        self,
        order_id: int,
        status: str,
        changed_by: int | None = None,
        notes: str | None = None,
        user_roles: list[str] | None = None,
        skip_validation: bool = False,
    ) -> bool:
        """
        Обновление статуса заявки с валидацией переходов и логированием изменений

        Использует транзакционную изоляцию для предотвращения race conditions.

        Args:
            order_id: ID заявки
            status: Новый статус
            changed_by: ID пользователя, который изменил статус
            notes: Дополнительные заметки об изменении
            user_roles: Роли пользователя для проверки прав
            skip_validation: Пропустить валидацию (для миграций/admin)

        Returns:
            True если успешно

        Raises:
            InvalidStateTransitionError: Если переход недопустим
        """
        async with self.transaction():
            # Получаем текущий статус перед изменением с блокировкой
            connection = self._get_connection()

            cursor = await connection.execute("SELECT status FROM orders WHERE id = ?", (order_id,))
            row = await cursor.fetchone()
            if not row:
                logger.error(f"Заявка #{order_id} не найдена")
                return False

            old_status = row["status"]

            # Валидация перехода статуса (если не пропущена)
            if not skip_validation:
                try:
                    OrderStateMachine.validate_transition(
                        from_state=old_status,
                        to_state=status,
                        user_roles=user_roles,
                        raise_exception=True,
                    )
                    logger.info(f"✅ Валидация перехода пройдена: {old_status} → {status}")
                except InvalidStateTransitionError as e:
                    logger.error(f"❌ Недопустимый переход статуса для заявки #{order_id}: {e}")
                    raise  # Пробрасываем исключение выше

            # Обновляем статус заявки
            await connection.execute(
                "UPDATE orders SET status = ?, updated_at = ? WHERE id = ?",
                (status, get_now().isoformat(), order_id),
            )

            # Логируем изменение статуса в историю
            transition_description = OrderStateMachine.get_transition_description(
                old_status, status
            )
            history_notes = notes or transition_description

            await connection.execute(
                """
                INSERT INTO order_status_history (order_id, old_status, new_status, changed_by, notes)
                VALUES (?, ?, ?, ?, ?)
                """,
                (order_id, old_status, status, changed_by, history_notes),
            )
            # commit() выполнится автоматически при выходе из context manager

        logger.info(
            f"Статус заявки #{order_id} изменен с {old_status} на {status}"
            f"{f' пользователем {changed_by}' if changed_by else ''}"
        )

        return True

    async def get_order_status_history(self, order_id: int) -> list[dict]:
        """
        Получение истории изменений статусов заявки

        Args:
            order_id: ID заявки

        Returns:
            Список изменений статусов
        """
        connection = self._get_connection()

        cursor = await connection.execute(
            """
            SELECT
                h.id,
                h.order_id,
                h.old_status,
                h.new_status,
                h.changed_by,
                u.first_name || ' ' || COALESCE(u.last_name, '') as changed_by_name,
                h.changed_at,
                h.notes
            FROM order_status_history h
            LEFT JOIN users u ON h.changed_by = u.telegram_id
            WHERE h.order_id = ?
            ORDER BY h.changed_at ASC
            """,
            (order_id,),
        )
        rows = await cursor.fetchall()

        history = []
        for row in rows:
            history.append(
                {
                    "id": row["id"],
                    "order_id": row["order_id"],
                    "old_status": row["old_status"],
                    "new_status": row["new_status"],
                    "changed_by": row["changed_by"],
                    "changed_by_name": (
                        row["changed_by_name"].strip() if row["changed_by_name"] else None
                    ),
                    "changed_at": row["changed_at"],
                    "notes": row["notes"],
                }
            )

        return history

    async def update_order_field(self, order_id: int, field: str, value: Any) -> bool:
        """
        Обновление отдельного поля заявки

        Args:
            order_id: ID заявки
            field: Название поля
            value: Новое значение

        Returns:
            True если успешно обновлено

        Raises:
            ValueError: Если поле не может быть обновлено
        """
        # Список разрешенных для обновления полей
        allowed_fields = {
            "equipment_type",
            "description",
            "client_name",
            "client_address",
            "client_phone",
            "notes",
            "scheduled_time",
            "estimated_completion_date",
            "prepayment_amount",
        }

        if field not in allowed_fields:
            raise ValueError(f"Поле {field} не может быть обновлено через этот метод")

        connection = self._get_connection()

        await connection.execute(
            f"UPDATE orders SET {field} = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",  # nosec B608 - field из контролируемого enum, не из пользовательского ввода
            (value, order_id),
        )
        await connection.commit()

        logger.info("Order #%d: field '%s' updated", order_id, field)
        return True

    async def assign_master_to_order(
        self, order_id: int, master_id: int, user_roles: list[str] | None = None
    ) -> bool:
        """
        Назначение мастера на заявку с валидацией перехода статуса

        Использует транзакционную изоляцию для предотвращения race conditions.

        Args:
            order_id: ID заявки
            master_id: ID мастера
            user_roles: Роли пользователя (для валидации)

        Returns:
            True если успешно

        Raises:
            InvalidStateTransitionError: Если переход в ASSIGNED недопустим
        """
        async with self.transaction() as connection:
            # Получаем текущий статус с блокировкой
            cursor = await connection.execute("SELECT status FROM orders WHERE id = ?", (order_id,))
            row = await cursor.fetchone()
            if not row:
                logger.error(f"Заявка #{order_id} не найдена")
                return False

            current_status = row["status"]

            # Валидация перехода в ASSIGNED
            OrderStateMachine.validate_transition(
                from_state=current_status,
                to_state=OrderStatus.ASSIGNED,
                user_roles=user_roles or [UserRole.ADMIN, UserRole.DISPATCHER],
                raise_exception=True,
            )

            # Обновляем заявку
            await connection.execute(
                """
                UPDATE orders
                SET assigned_master_id = ?, status = ?, updated_at = ?
                WHERE id = ?
                """,
                (master_id, OrderStatus.ASSIGNED, get_now().isoformat(), order_id),
            )
            # commit() выполнится автоматически при выходе из context manager

        logger.info(f"Мастер {master_id} назначен на заявку #{order_id}")
        return True

    async def update_order(
        self,
        order_id: int,
        equipment_type: str | None = None,
        description: str | None = None,
        client_name: str | None = None,
        client_address: str | None = None,
        client_phone: str | None = None,
        notes: str | None = None,
    ) -> bool:
        """
        Обновление информации о заявке

        Args:
            order_id: ID заявки
            equipment_type: Тип техники
            description: Описание
            client_name: Имя клиента
            client_address: Адрес клиента
            client_phone: Телефон клиента
            notes: Заметки

        Returns:
            True если успешно
        """
        updates = []
        params: list[Any] = []

        if equipment_type:
            updates.append("equipment_type = ?")
            params.append(equipment_type)
        if description:
            updates.append("description = ?")
            params.append(description)
        if client_name:
            updates.append("client_name = ?")
            params.append(client_name)
        if client_address:
            updates.append("client_address = ?")
            params.append(client_address)
        if client_phone:
            updates.append("client_phone = ?")
            params.append(client_phone)
        if notes is not None:
            updates.append("notes = ?")
            params.append(notes)

        if not updates:
            return False

        updates.append("updated_at = ?")
        params.append(get_now().isoformat())  # Добавляем дату в конец
        params.append(order_id)

        query = f"UPDATE orders SET {', '.join(updates)} WHERE id = ?"  # nosec B608 - updates формируется из контролируемых полей, не из пользовательского ввода
        connection = self._get_connection()
        await connection.execute(query, params)
        await connection.commit()

        logger.info(f"Заявка #{order_id} обновлена")
        return True

    async def get_orders_by_master(
        self, master_id: int, exclude_closed: bool = True
    ) -> list[Order]:
        """
        Получение заявок мастера

        Args:
            master_id: ID мастера
            exclude_closed: Исключить закрытые заявки

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
            WHERE o.assigned_master_id = ? AND o.deleted_at IS NULL
        """
        params: list[Any] = [master_id]

        if exclude_closed:
            query += " AND o.status NOT IN (?, ?)"
            params.extend([OrderStatus.CLOSED, OrderStatus.REFUSED])

        query += " ORDER BY o.created_at DESC"

        connection = self._get_connection()
        cursor = await connection.execute(query, params)
        rows = await cursor.fetchall()

        orders = []
        for row in rows:
            orders.append(
                Order(
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
                    scheduled_time=(
                        row["scheduled_time"]
                        if row["scheduled_time"] is not None
                        and str(row["scheduled_time"]).strip() != "None"
                        else None
                    ),
                    total_amount=(
                        row["total_amount"]
                        if "total_amount" in row and row["total_amount"] is not None
                        else None
                    ),
                    materials_cost=(
                        row["materials_cost"]
                        if "materials_cost" in row and row["materials_cost"] is not None
                        else None
                    ),
                    master_profit=(
                        row["master_profit"]
                        if "master_profit" in row and row["master_profit"] is not None
                        else None
                    ),
                    company_profit=(
                        row["company_profit"]
                        if "company_profit" in row and row["company_profit"] is not None
                        else None
                    ),
                    has_review=(
                        bool(row["has_review"])
                        if "has_review" in row and row["has_review"] is not None
                        else None
                    ),
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
                    dispatcher_name=row["dispatcher_name"],
                    master_name=row["master_name"],
                )
            )
        return orders

    async def update_order_amounts(
        self,
        order_id: int,
        total_amount: float | None = None,
        materials_cost: float | None = None,
        master_profit: float | None = None,
        company_profit: float | None = None,
        has_review: bool | None = None,
        out_of_city: bool | None = None,
    ) -> bool:
        """
        Обновление сумм заказа

        Args:
            order_id: ID заявки
            total_amount: Общая сумма заказа
            materials_cost: Сумма расходного материала
            master_profit: Прибыль мастера
            company_profit: Прибыль компании
            has_review: Взял ли мастер отзыв
            out_of_city: Был ли выезд за город

        Returns:
            True если успешно
        """
        updates = []
        params: list[Any] = []

        if total_amount is not None:
            updates.append("total_amount = ?")
            params.append(total_amount)

        if materials_cost is not None:
            updates.append("materials_cost = ?")
            params.append(materials_cost)

        if master_profit is not None:
            updates.append("master_profit = ?")
            params.append(master_profit)

        if company_profit is not None:
            updates.append("company_profit = ?")
            params.append(company_profit)

        if has_review is not None:
            updates.append("has_review = ?")
            params.append(1 if has_review else 0)

        if out_of_city is not None:
            updates.append("out_of_city = ?")
            params.append(1 if out_of_city else 0)

        if not updates:
            return False

        updates.append("updated_at = ?")
        params.append(get_now().isoformat())  # Добавляем дату в конец
        params.append(order_id)

        query = f"UPDATE orders SET {', '.join(updates)} WHERE id = ?"  # nosec B608 - updates формируется из контролируемых полей, не из пользовательского ввода
        connection = self._get_connection()
        await connection.execute(query, params)
        await connection.commit()

        logger.info(f"Суммы заявки #{order_id} обновлены")
        return True

    # ==================== AUDIT LOG ====================

    async def add_audit_log(self, user_id: int, action: str, details: str | None = None):
        """
        Добавление записи в лог аудита

        Args:
            user_id: ID пользователя
            action: Действие
            details: Детали
        """
        connection = self._get_connection()

        await connection.execute(
            "INSERT INTO audit_log (user_id, action, details) VALUES (?, ?, ?)",
            (user_id, action, details),
        )
        await connection.commit()

    async def get_audit_logs(self, limit: int = 100) -> list[AuditLog]:
        """
        Получение логов аудита

        Args:
            limit: Лимит записей

        Returns:
            Список логов
        """
        connection = self._get_connection()

        cursor = await connection.execute(
            "SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT ?", (limit,)
        )
        rows = await cursor.fetchall()

        logs = []
        for row in rows:
            logs.append(
                AuditLog(
                    id=row["id"],
                    user_id=row["user_id"],
                    action=row["action"],
                    details=row["details"],
                    timestamp=(
                        datetime.fromisoformat(row["timestamp"]) if row["timestamp"] else None
                    ),
                )
            )
        return logs

    # ==================== STATISTICS ====================

    async def get_statistics(self) -> dict[str, Any]:
        """
        Получение статистики

        Returns:
            Словарь со статистикой
        """
        stats: dict[str, Any] = {}
        connection = self._get_connection()

        # Количество пользователей по ролям
        cursor = await connection.execute("SELECT role, COUNT(*) as count FROM users GROUP BY role")
        roles_stats = await cursor.fetchall()
        stats["users_by_role"] = {row["role"]: row["count"] for row in roles_stats}

        # Количество заявок по статусам
        cursor = await connection.execute(
            "SELECT status, COUNT(*) as count FROM orders GROUP BY status"
        )
        orders_stats = await cursor.fetchall()
        stats["orders_by_status"] = {row["status"]: row["count"] for row in orders_stats}

        # Количество активных мастеров
        cursor = await connection.execute(
            "SELECT COUNT(*) as count FROM masters WHERE is_active = 1 AND is_approved = 1"
        )
        row = await cursor.fetchone()
        if row is not None:
            stats["active_masters"] = cast(int, row["count"])
        else:
            stats["active_masters"] = 0

        # Общее количество заявок
        cursor = await connection.execute("SELECT COUNT(*) as count FROM orders")
        row = await cursor.fetchone()
        if row is not None:
            stats["total_orders"] = cast(int, row["count"])
        else:
            stats["total_orders"] = 0

        return stats

    # ==================== FINANCIAL REPORTS ====================

    async def get_orders_by_period(
        self, start_date: datetime, end_date: datetime, status: str | None = None
    ) -> list[Order]:
        """
        Получение заказов за период (по дате закрытия!)

        Args:
            start_date: Начало периода
            end_date: Конец периода
            status: Фильтр по статусу (опционально)

        Returns:
            Список заказов
        """
        query = """
            SELECT o.*,
                   mu.first_name as master_first_name,
                   mu.last_name as master_last_name,
                   mu.username as master_username,
                   d.first_name as dispatcher_first_name,
                   d.last_name as dispatcher_last_name,
                   d.username as dispatcher_username
            FROM orders o
            LEFT JOIN masters m ON o.assigned_master_id = m.id
            LEFT JOIN users mu ON m.telegram_id = mu.telegram_id
            LEFT JOIN users d ON o.dispatcher_id = d.telegram_id
            WHERE o.updated_at >= ? AND o.updated_at < ?
                  AND o.status = 'CLOSED'
                  AND o.total_amount IS NOT NULL
        """
        params = [start_date.isoformat(), end_date.isoformat()]

        if status:
            query += " AND o.status = ?"
            params.append(status)

        query += " ORDER BY o.updated_at DESC"

        connection = self._get_connection()
        cursor = await connection.execute(query, params)
        rows = await cursor.fetchall()

        orders = []
        for row in rows:
            order = Order(
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
                total_amount=row["total_amount"],
                materials_cost=row["materials_cost"],
                master_profit=row["master_profit"],
                company_profit=row["company_profit"],
                has_review=bool(row["has_review"]) if row["has_review"] is not None else None,
                out_of_city=bool(row["out_of_city"]) if row["out_of_city"] is not None else None,
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
            )

            # Добавляем имена мастеров и диспетчеров
            if row["master_first_name"]:
                master_name = row["master_first_name"]
                if row["master_last_name"]:
                    master_name += f" {row['master_last_name']}"
                order.master_name = master_name
            elif row["master_username"]:
                order.master_name = f"@{row['master_username']}"

            if row["dispatcher_first_name"]:
                dispatcher_name = row["dispatcher_first_name"]
                if row["dispatcher_last_name"]:
                    dispatcher_name += f" {row['dispatcher_last_name']}"
                order.dispatcher_name = dispatcher_name
            elif row["dispatcher_username"]:
                order.dispatcher_name = f"@{row['dispatcher_username']}"

            orders.append(order)

        return orders

    async def create_financial_report(self, report: FinancialReport) -> int:
        """
        Создание финансового отчета

        Args:
            report: Объект отчета

        Returns:
            ID созданного отчета
        """
        connection = self._get_connection()

        cursor = await connection.execute(
            """
            INSERT INTO financial_reports (
                report_type, period_start, period_end, total_orders,
                total_amount, total_materials_cost, total_net_profit,
                total_company_profit, total_master_profit, average_check, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                report.report_type,
                report.period_start.isoformat() if report.period_start else None,
                report.period_end.isoformat() if report.period_end else None,
                report.total_orders,
                report.total_amount,
                report.total_materials_cost,
                report.total_net_profit,
                report.total_company_profit,
                report.total_master_profit,
                report.average_check,
                report.created_at.isoformat() if report.created_at else None,
            ),
        )
        await connection.commit()
        if cursor.lastrowid is None:
            raise ValueError("Failed to insert financial report: lastrowid is None")
        return int(cursor.lastrowid)

    async def get_financial_report_by_id(self, report_id: int) -> FinancialReport | None:
        """
        Получение финансового отчета по ID

        Args:
            report_id: ID отчета

        Returns:
            Объект отчета или None
        """
        connection = self._get_connection()

        cursor = await connection.execute(
            "SELECT * FROM financial_reports WHERE id = ?", (report_id,)
        )
        row = await cursor.fetchone()

        if not row:
            return None

        return FinancialReport(
            id=row["id"],
            report_type=row["report_type"],
            period_start=(
                datetime.fromisoformat(row["period_start"]) if row["period_start"] else None
            ),
            period_end=datetime.fromisoformat(row["period_end"]) if row["period_end"] else None,
            total_orders=row["total_orders"],
            total_amount=row["total_amount"],
            total_materials_cost=row["total_materials_cost"],
            total_net_profit=row["total_net_profit"],
            total_company_profit=row["total_company_profit"],
            total_master_profit=row["total_master_profit"],
            average_check=row["average_check"],
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
        )

    async def create_master_financial_report(self, master_report: MasterFinancialReport) -> int:
        """
        Создание отчета по мастеру

        Args:
            master_report: Объект отчета по мастеру

        Returns:
            ID созданного отчета
        """
        connection = self._get_connection()

        cursor = await connection.execute(
            """
            INSERT INTO master_financial_reports (
                report_id, master_id, master_name, orders_count,
                total_amount, total_materials_cost, total_net_profit,
                total_master_profit, total_company_profit, average_check,
                reviews_count, out_of_city_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                master_report.report_id,
                master_report.master_id,
                master_report.master_name,
                master_report.orders_count,
                master_report.total_amount,
                master_report.total_materials_cost,
                master_report.total_net_profit,
                master_report.total_master_profit,
                master_report.total_company_profit,
                master_report.average_check,
                master_report.reviews_count,
                master_report.out_of_city_count,
            ),
        )
        await connection.commit()
        if cursor.lastrowid is None:
            raise ValueError("Failed to insert financial report: lastrowid is None")
        return int(cursor.lastrowid)

    async def get_master_reports_by_report_id(self, report_id: int) -> list[MasterFinancialReport]:
        """
        Получение отчетов по мастерам для основного отчета

        Args:
            report_id: ID основного отчета

        Returns:
            Список отчетов по мастерам
        """
        connection = self._get_connection()

        cursor = await connection.execute(
            "SELECT * FROM master_financial_reports WHERE report_id = ? ORDER BY total_master_profit DESC",
            (report_id,),
        )
        rows = await cursor.fetchall()

        master_reports = []
        for row in rows:
            master_report = MasterFinancialReport(
                id=row["id"],
                report_id=row["report_id"],
                master_id=row["master_id"],
                master_name=row["master_name"],
                orders_count=row["orders_count"],
                total_amount=row["total_amount"],
                total_materials_cost=row["total_materials_cost"],
                total_net_profit=row["total_net_profit"],
                total_master_profit=row["total_master_profit"],
                total_company_profit=row["total_company_profit"],
                average_check=row["average_check"],
                reviews_count=row["reviews_count"],
                out_of_city_count=row["out_of_city_count"],
            )
            master_reports.append(master_report)

        return master_reports

    async def get_latest_reports(self, limit: int = 10) -> list[FinancialReport]:
        """
        Получение последних отчетов

        Args:
            limit: Количество отчетов

        Returns:
            Список отчетов
        """
        connection = self._get_connection()

        cursor = await connection.execute(
            "SELECT * FROM financial_reports ORDER BY created_at DESC LIMIT ?", (limit,)
        )
        rows = await cursor.fetchall()

        reports = []
        for row in rows:
            report = FinancialReport(
                id=row["id"],
                report_type=row["report_type"],
                period_start=(
                    datetime.fromisoformat(row["period_start"]) if row["period_start"] else None
                ),
                period_end=datetime.fromisoformat(row["period_end"]) if row["period_end"] else None,
                total_orders=row["total_orders"],
                total_amount=row["total_amount"],
                total_materials_cost=row["total_materials_cost"],
                total_net_profit=row["total_net_profit"],
                total_company_profit=row["total_company_profit"],
                total_master_profit=row["total_master_profit"],
                average_check=row["average_check"],
                created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
            )
            reports.append(report)

        return reports

    # ==================== АРХИВНЫЕ ОТЧЕТЫ МАСТЕРОВ ====================

    async def save_master_report_archive(self, report: "MasterReportArchive") -> int:  # type: ignore[name-defined]  # noqa: F821
        """
        Сохранение архивного отчета мастера

        Args:
            report: Данные отчета

        Returns:
            ID созданной записи
        """

        connection = self._get_connection()

        cursor = await connection.execute(
            """
            INSERT INTO master_reports_archive (
                master_id, period_start, period_end, file_path, file_name,
                file_size, total_orders, active_orders, completed_orders,
                total_revenue, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                report.master_id,
                report.period_start.isoformat() if report.period_start else None,
                report.period_end.isoformat() if report.period_end else None,
                report.file_path,
                report.file_name,
                report.file_size,
                report.total_orders,
                report.active_orders,
                report.completed_orders,
                report.total_revenue,
                report.notes,
            ),
        )
        await connection.commit()
        if cursor.lastrowid is None:
            raise ValueError("Failed to insert financial report: lastrowid is None")
        return int(cursor.lastrowid)

    async def get_master_archived_reports(
        self, master_id: int, limit: int = 10
    ) -> list["MasterReportArchive"]:  # type: ignore[name-defined]  # noqa: F821
        """
        Получение списка архивных отчетов мастера

        Args:
            master_id: ID мастера
            limit: Лимит записей

        Returns:
            Список архивных отчетов
        """
        from app.database.models import MasterReportArchive

        connection = self._get_connection()

        cursor = await connection.execute(
            """
            SELECT * FROM master_reports_archive
            WHERE master_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (master_id, limit),
        )
        rows = await cursor.fetchall()

        reports = []
        for row in rows:
            report = MasterReportArchive(
                id=row["id"],
                master_id=row["master_id"],
                period_start=(
                    datetime.fromisoformat(row["period_start"]) if row["period_start"] else None
                ),
                period_end=datetime.fromisoformat(row["period_end"]) if row["period_end"] else None,
                file_path=row["file_path"],
                file_name=row["file_name"],
                file_size=row["file_size"],
                total_orders=row["total_orders"],
                active_orders=row["active_orders"],
                completed_orders=row["completed_orders"],
                total_revenue=row["total_revenue"],
                created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
                notes=row["notes"],
            )
            reports.append(report)

        return reports

    async def get_master_report_archive_by_id(self, report_id: int) -> "MasterReportArchive | None":  # type: ignore[name-defined]  # noqa: F821
        """
        Получение архивного отчета по ID

        Args:
            report_id: ID отчета

        Returns:
            Архивный отчет или None
        """
        from app.database.models import MasterReportArchive

        connection = self._get_connection()

        cursor = await connection.execute(
            "SELECT * FROM master_reports_archive WHERE id = ?",
            (report_id,),
        )
        row = await cursor.fetchone()

        if not row:
            return None

        return MasterReportArchive(
            id=row["id"],
            master_id=row["master_id"],
            period_start=(
                datetime.fromisoformat(row["period_start"]) if row["period_start"] else None
            ),
            period_end=datetime.fromisoformat(row["period_end"]) if row["period_end"] else None,
            file_path=row["file_path"],
            file_name=row["file_name"],
            file_size=row["file_size"],
            total_orders=row["total_orders"],
            active_orders=row["active_orders"],
            completed_orders=row["completed_orders"],
            total_revenue=row["total_revenue"],
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
            notes=row["notes"],
        )

    async def delete_master(self, telegram_id: int) -> bool:
        """
        Удаление мастера из системы

        Args:
            telegram_id: Telegram ID мастера

        Returns:
            True если успешно
        """
        connection = self._get_connection()

        try:
            # Сначала получаем ID мастера
            cursor = await connection.execute(
                "SELECT id FROM masters WHERE telegram_id = ?", (telegram_id,)
            )
            row = await cursor.fetchone()

            if not row:
                logger.warning(f"Master with telegram_id {telegram_id} not found")
                return False

            master_id = row["id"]

            # Удаляем мастера (каскадное удаление удалит связанные записи)
            await connection.execute("DELETE FROM masters WHERE telegram_id = ?", (telegram_id,))
            await connection.commit()

            logger.info(f"Master {telegram_id} (ID: {master_id}) deleted from system")
            return True

        except Exception as e:
            logger.error(f"Error deleting master {telegram_id}: {e}")
            await connection.rollback()
            return False

    async def get_orders_by_client_phone(self, phone: str) -> list[Order]:
        """
        Поиск заявок по номеру телефона клиента

        Args:
            phone: Номер телефона клиента

        Returns:
            Список заявок клиента, отсортированный по дате создания (новые первые)
        """
        if not self.connection:
            await self.connect()

        connection = self._get_connection()

        cursor = await connection.execute(
            """
            SELECT o.*,
                   m.first_name as master_first_name, m.last_name as master_last_name, m.username as master_username,
                   u.first_name as dispatcher_first_name, u.last_name as dispatcher_last_name, u.username as dispatcher_username
            FROM orders o
            LEFT JOIN masters m ON o.assigned_master_id = m.id
            LEFT JOIN users u ON o.dispatcher_id = u.telegram_id
            WHERE o.client_phone = ? AND o.deleted_at IS NULL
            ORDER BY o.created_at DESC
            """,
            (phone,),
        )
        rows = await cursor.fetchall()

        orders = []
        for row in rows:
            order = Order(
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
                total_amount=row["total_amount"],
                materials_cost=row["materials_cost"],
                master_profit=row["master_profit"],
                company_profit=row["company_profit"],
                has_review=bool(row["has_review"]) if row["has_review"] is not None else None,
                out_of_city=bool(row["out_of_city"]) if row["out_of_city"] is not None else None,
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
            )

            # Добавляем имена мастеров и диспетчеров
            if row["master_first_name"]:
                master_name = row["master_first_name"]
                if row["master_last_name"]:
                    master_name += f" {row['master_last_name']}"
                order.master_name = master_name
            elif row["master_username"]:
                order.master_name = f"@{row['master_username']}"

            if row["dispatcher_first_name"]:
                dispatcher_name = row["dispatcher_first_name"]
                if row["dispatcher_last_name"]:
                    dispatcher_name += f" {row['dispatcher_last_name']}"
                order.dispatcher_name = dispatcher_name
            elif row["dispatcher_username"]:
                order.dispatcher_name = f"@{row['dispatcher_username']}"

            orders.append(order)

        return orders

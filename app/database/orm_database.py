"""
SQLAlchemy ORM Database класс
"""

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import joinedload, selectinload

from app.config import Config, OrderStatus, UserRole
from app.database.orm_models import (
    AuditLog,
    Base,
    FinancialReport,
    Master,
    MasterFinancialReport,
    MasterReportArchive,
    Order,
    OrderGroupMessage,
    OrderStatusHistory,
    User,
)
from app.domain.order_state_machine import InvalidStateTransitionError, OrderStateMachine
from app.utils.helpers import get_now


logger = logging.getLogger(__name__)


class ORMDatabase:
    """Класс для работы с базой данных через SQLAlchemy ORM"""

    def __init__(self, database_url: str | None = None):
        """
        Инициализация ORM Database

        Args:
            database_url: URL базы данных (SQLite или PostgreSQL)
        """
        self.database_url = database_url or self._get_database_url()
        self.engine: AsyncEngine | None = None
        self.session_factory: async_sessionmaker[AsyncSession] | None = None
        self._is_sqlite = self.database_url.startswith("sqlite")

    def _get_database_url(self) -> str:
        """Получение URL базы данных из переменных окружения"""
        # Проверяем переменную окружения
        if database_url := os.getenv("DATABASE_URL"):
            return database_url

        # Fallback на SQLite
        db_path = Config.DATABASE_PATH
        return f"sqlite+aiosqlite:///{db_path}"

    async def connect(self):
        """Подключение к базе данных"""
        try:
            logger.info(f"🔧 Инициализация подключения к БД...")
            logger.info(f"   Database URL: {self.database_url}")
            logger.info(f"   Is SQLite: {self._is_sqlite}")
            
            # Создаем async engine
            self.engine = create_async_engine(
                self.database_url,
                echo=False,  # Устанавливаем True для отладки SQL
                pool_pre_ping=True,  # Проверка соединения перед использованием
                pool_recycle=3600,  # Переподключение каждый час
                # Настройки для SQLite
                connect_args={"check_same_thread": False} if self._is_sqlite else {},
            )

            # Создаем session factory
            self.session_factory = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False,  # Важно для async работы
            )

            logger.info("🔧 Создание таблиц...")
            # Создаем таблицы если их нет
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            logger.info(f"✅ Подключено к базе данных: {self.database_url}")
            logger.info("✅ Таблицы созданы/проверены")

        except Exception as e:
            logger.error(f"❌ Ошибка подключения к БД: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            raise

    async def disconnect(self):
        """Отключение от базы данных"""
        if self.engine:
            await self.engine.dispose()
            logger.info("Отключено от базы данных")

    @asynccontextmanager
    async def get_session(self):
        """
        Context manager для получения сессии

        Usage:
            async with db.get_session() as session:
                user = await session.get(User, user_id)
                # Автоматический commit/rollback
        """
        if not self.session_factory:
            raise RuntimeError("База данных не подключена")

        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
                logger.debug("✅ Транзакция успешно завершена (commit)")
            except Exception as e:
                await session.rollback()
                logger.error(f"❌ Транзакция отменена (rollback): {e}")
                raise

    # ==================== USERS ====================

    async def get_or_create_user(
        self,
        telegram_id: int,
        username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> User:
        """Получение или создание пользователя"""
        async with self.get_session() as session:
            # Ищем существующего пользователя
            stmt = select(User).where(
                and_(User.telegram_id == telegram_id, User.deleted_at.is_(None))
            )
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            if user:
                # Обновляем информацию если изменилась
                updated = False
                if user.username != username:
                    user.username = username
                    updated = True
                if user.first_name != first_name:
                    user.first_name = first_name
                    updated = True
                if user.last_name != last_name:
                    user.last_name = last_name
                    updated = True

                if updated:
                    user.version += 1
                    await session.commit()

                return user

            # Определяем роль
            role = UserRole.UNKNOWN
            if telegram_id in Config.ADMIN_IDS:
                role = UserRole.ADMIN
            elif telegram_id in Config.DISPATCHER_IDS:
                role = UserRole.DISPATCHER

            # Создаем нового пользователя
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                role=role,
                created_at=get_now(),
            )

            session.add(user)
            await session.flush()  # Получаем ID

            logger.info(f"Создан новый пользователь: {telegram_id} с ролью {role}")
            return user

    async def get_user_by_telegram_id(self, telegram_id: int) -> User | None:
        """Получение пользователя по Telegram ID"""
        async with self.get_session() as session:
            stmt = select(User).where(
                and_(User.telegram_id == telegram_id, User.deleted_at.is_(None))
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def update_user_role(self, telegram_id: int, role: str) -> bool:
        """Обновление роли пользователя"""
        async with self.get_session() as session:
            stmt = select(User).where(
                and_(User.telegram_id == telegram_id, User.deleted_at.is_(None))
            )
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                logger.error(f"Пользователь {telegram_id} не найден")
                return False

            user.role = role
            user.version += 1
            await session.commit()

            logger.info(f"Роль пользователя {telegram_id} изменена на {role}")
            return True

    async def add_user_role(self, telegram_id: int, role: str) -> bool:
        """Добавление роли пользователю"""
        async with self.get_session() as session:
            stmt = select(User).where(
                and_(User.telegram_id == telegram_id, User.deleted_at.is_(None))
            )
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                logger.error(f"Пользователь {telegram_id} не найден")
                return False

            new_roles = user.add_role(role)
            user.version += 1
            await session.commit()

            logger.info(f"Роль {role} добавлена пользователю {telegram_id}. Роли: {new_roles}")
            return True

    async def remove_user_role(self, telegram_id: int, role: str) -> bool:
        """Удаление роли у пользователя"""
        async with self.get_session() as session:
            stmt = select(User).where(
                and_(User.telegram_id == telegram_id, User.deleted_at.is_(None))
            )
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                logger.error(f"Пользователь {telegram_id} не найден")
                return False

            new_roles = user.remove_role(role)
            user.version += 1
            await session.commit()

            logger.info(f"Роль {role} удалена у пользователя {telegram_id}. Роли: {new_roles}")
            return True

    async def set_user_roles(self, telegram_id: int, roles: list[str]) -> bool:
        """Установка списка ролей пользователю"""
        async with self.get_session() as session:
            stmt = select(User).where(
                and_(User.telegram_id == telegram_id, User.deleted_at.is_(None))
            )
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                logger.error(f"Пользователь {telegram_id} не найден")
                return False

            # Устанавливаем роли
            if not roles:
                user.role = UserRole.UNKNOWN
            else:
                user.role = ",".join(sorted(roles))
            user.version += 1
            await session.commit()

            logger.info(f"Роли пользователя {telegram_id} установлены: {user.role}")
            return True

    async def get_all_users(self) -> list[User]:
        """Получение всех пользователей"""
        async with self.get_session() as session:
            stmt = select(User).order_by(User.created_at.desc())
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def get_admins_and_dispatchers(self, exclude_user_id: int | None = None) -> list[User]:
        """
        Получение всех админов и диспетчеров

        Args:
            exclude_user_id: ID пользователя, которого нужно исключить из результатов

        Returns:
            List[User]: Список пользователей с ролями ADMIN или DISPATCHER
        """
        async with self.get_session() as session:
            stmt = select(User).where(
                and_(
                    User.deleted_at.is_(None),
                    or_(
                        User.role.contains(UserRole.ADMIN), User.role.contains(UserRole.DISPATCHER)
                    ),
                )
            )

            if exclude_user_id:
                stmt = stmt.where(User.telegram_id != exclude_user_id)

            stmt = stmt.order_by(User.created_at.desc())
            result = await session.execute(stmt)
            return list(result.scalars().all())

    # ==================== MASTERS ====================

    async def create_master(
        self, telegram_id: int, phone: str, specialization: str, is_approved: bool = False
    ) -> Master:
        """Создание мастера"""
        async with self.get_session() as session:
            master = Master(
                telegram_id=telegram_id,
                phone=phone,
                specialization=specialization,
                is_approved=is_approved,
                created_at=get_now(),
            )

            session.add(master)
            await session.flush()

            logger.info(f"Создан мастер: {telegram_id}")
            return master

    async def get_master_by_telegram_id(self, telegram_id: int) -> Master | None:
        """Получение мастера по Telegram ID с загрузкой связанного пользователя"""
        async with self.get_session() as session:
            stmt = (
                select(Master)
                .options(joinedload(Master.user))
                .where(and_(Master.telegram_id == telegram_id))
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_all_masters(
        self, only_approved: bool = False, only_active: bool = False
    ) -> list[Master]:
        """Получение всех мастеров с фильтрацией"""
        async with self.get_session() as session:
            stmt = select(Master).options(joinedload(Master.user))

            if only_approved:
                stmt = stmt.where(Master.is_approved is True)
            if only_active:
                stmt = stmt.where(Master.is_active is True)

            stmt = stmt.order_by(Master.created_at.desc())
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def get_master_by_id(self, master_id: int) -> Master | None:
        """Получение мастера по ID"""
        async with self.get_session() as session:
            stmt = select(Master).options(joinedload(Master.user)).where(Master.id == master_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_master_by_work_chat_id(self, work_chat_id: int) -> Master | None:
        """Получение мастера по ID рабочего чата"""
        async with self.get_session() as session:
            stmt = (
                select(Master)
                .options(joinedload(Master.user))
                .where(Master.work_chat_id == work_chat_id)
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    # ==================== ORDER GROUP MESSAGES ====================

    async def save_order_group_message(
        self, order_id: int, master_id: int, chat_id: int, message_id: int
    ) -> int:
        """Сохранение сообщения заявки в рабочей группе"""
        async with self.get_session() as session:
            record = OrderGroupMessage(
                order_id=order_id,
                master_id=master_id,
                chat_id=chat_id,
                message_id=message_id,
                is_active=True,
            )
            session.add(record)
            await session.flush()
            return record.id

    async def get_active_group_messages_by_order(self, order_id: int) -> list[OrderGroupMessage]:
        """Получение активных групповых сообщений по заявке"""
        async with self.get_session() as session:
            stmt = select(OrderGroupMessage).where(
                and_(OrderGroupMessage.order_id == order_id, OrderGroupMessage.is_active.is_(True))
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def deactivate_group_messages(self, order_id: int) -> int:
        """Пометить сообщения заявки как неактивные (после удаления из чата)"""
        async with self.get_session() as session:
            stmt = select(OrderGroupMessage).where(
                and_(OrderGroupMessage.order_id == order_id, OrderGroupMessage.is_active.is_(True))
            )
            result = await session.execute(stmt)
            messages = list(result.scalars().all())
            for m in messages:
                m.is_active = False
                m.deleted_at = get_now()
            await session.commit()
            return len(messages)

    async def update_master_status(self, telegram_id: int, is_active: bool) -> bool:
        """Обновление статуса мастера (активен/неактивен)"""
        async with self.get_session() as session:
            stmt = select(Master).where(Master.telegram_id == telegram_id)
            result = await session.execute(stmt)
            master = result.scalar_one_or_none()

            if not master:
                logger.error(f"Мастер {telegram_id} не найден")
                return False

            master.is_active = is_active
            master.version += 1
            await session.commit()

            status_text = "активен" if is_active else "неактивен"
            logger.info(f"Мастер {telegram_id} теперь {status_text}")
            return True

    async def update_master_work_chat(self, telegram_id: int, work_chat_id: int | None) -> bool:
        """Обновление рабочего чата мастера"""
        async with self.get_session() as session:
            stmt = select(Master).where(Master.telegram_id == telegram_id)
            result = await session.execute(stmt)
            master = result.scalar_one_or_none()

            if not master:
                logger.error(f"Мастер {telegram_id} не найден")
                return False

            master.work_chat_id = work_chat_id
            master.version += 1
            await session.commit()

            logger.info(f"Рабочий чат мастера {telegram_id} обновлен на {work_chat_id}")
            return True

    async def approve_master(self, telegram_id: int) -> bool:
        """Одобрение заявки мастера"""
        async with self.get_session() as session:
            stmt = select(Master).where(Master.telegram_id == telegram_id)
            result = await session.execute(stmt)
            master = result.scalar_one_or_none()

            if not master:
                logger.error(f"Мастер {telegram_id} не найден")
                return False

            master.is_approved = True
            master.version += 1
            await session.commit()

            logger.info(f"Мастер {telegram_id} одобрен")
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
        notes: str | None = None,
        scheduled_time: str | None = None,
    ) -> Order:
        """Создание заявки"""
        async with self.get_session() as session:
            now = get_now()
            order = Order(
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

            session.add(order)
            await session.flush()

            logger.info(f"Создана заявка #{order.id}")
            return order

    async def get_order_by_id(self, order_id: int) -> Order | None:
        """Получение заявки по ID с загрузкой связанных данных"""
        async with self.get_session() as session:
            stmt = (
                select(Order)
                .options(
                    joinedload(Order.assigned_master).joinedload(Master.user),
                    joinedload(Order.dispatcher),
                )
                .where(and_(Order.id == order_id))
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_all_orders(
        self, status: str | None = None, master_id: int | None = None, limit: int | None = None
    ) -> list[Order]:
        """Получение всех заявок с фильтрацией"""
        async with self.get_session() as session:
            stmt = select(Order).options(
                joinedload(Order.assigned_master).joinedload(Master.user),
                joinedload(Order.dispatcher),
            )

            if status:
                stmt = stmt.where(Order.status == status)
            if master_id:
                stmt = stmt.where(Order.assigned_master_id == master_id)

            stmt = stmt.order_by(Order.created_at.desc())

            if limit:
                stmt = stmt.limit(limit)

            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def update_order_status(
        self,
        order_id: int,
        status: str,
        changed_by: int | None = None,
        notes: str | None = None,
        user_roles: list[str] | None = None,
        skip_validation: bool = False,
    ) -> bool:
        """Обновление статуса заявки с валидацией переходов"""
        async with self.get_session() as session:
            # Получаем текущий статус
            stmt = select(Order).where(and_(Order.id == order_id))
            result = await session.execute(stmt)
            order = result.scalar_one_or_none()

            if not order:
                logger.error(f"Заявка #{order_id} не найдена")
                return False

            old_status = order.status

            # Валидация перехода статуса
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
                    raise

            # Обновляем статус заявки
            order.status = status
            order.updated_at = get_now()
            order.version += 1

            # Логируем изменение статуса в историю
            transition_description = OrderStateMachine.get_transition_description(
                old_status, status
            )
            history_notes = notes or transition_description

            status_history = OrderStatusHistory(
                order_id=order_id,
                old_status=old_status,
                new_status=status,
                changed_by=changed_by,
                notes=history_notes,
                changed_at=get_now(),
            )

            session.add(status_history)
            await session.commit()

            logger.info(
                f"Статус заявки #{order_id} изменен с {old_status} на {status}"
                + (f" пользователем {changed_by}" if changed_by else "")
            )
            return True

    async def assign_master_to_order(
        self, order_id: int, master_id: int, user_roles: list[str] | None = None
    ) -> bool:
        """Назначение мастера на заявку с валидацией перехода статуса"""
        async with self.get_session() as session:
            # Получаем заявку
            stmt = select(Order).where(and_(Order.id == order_id))
            result = await session.execute(stmt)
            order = result.scalar_one_or_none()

            if not order:
                logger.error(f"Заявка #{order_id} не найдена")
                return False

            current_status = order.status

            # Валидация перехода в ASSIGNED
            OrderStateMachine.validate_transition(
                from_state=current_status,
                to_state=OrderStatus.ASSIGNED,
                user_roles=user_roles or [UserRole.ADMIN, UserRole.DISPATCHER],
                raise_exception=True,
            )

            # Обновляем заявку
            order.assigned_master_id = master_id
            order.status = OrderStatus.ASSIGNED
            order.updated_at = get_now()
            order.version += 1

            await session.commit()

            logger.info(f"Мастер {master_id} назначен на заявку #{order_id}")
            return True

    async def unassign_master_from_order(self, order_id: int) -> bool:
        """Снятие мастера с заявки"""
        async with self.get_session() as session:
            # Получаем заявку
            stmt = select(Order).where(Order.id == order_id)
            result = await session.execute(stmt)
            order = result.scalar_one_or_none()

            if not order:
                logger.error(f"Заявка #{order_id} не найдена")
                return False

            # Снимаем мастера и возвращаем в NEW
            order.assigned_master_id = None
            order.status = OrderStatus.NEW
            order.updated_at = get_now()
            order.version += 1

            await session.commit()

            logger.info(f"Мастер снят с заявки #{order_id}")
            return True

    async def get_order_status_history(self, order_id: int) -> list[OrderStatusHistory]:
        """Получение истории изменений статусов заявки"""
        async with self.get_session() as session:
            stmt = (
                select(OrderStatusHistory)
                .options(joinedload(OrderStatusHistory.changed_by_user))
                .where(OrderStatusHistory.order_id == order_id)
                .order_by(OrderStatusHistory.changed_at.desc())
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def update_order(
        self,
        order_id: int,
        equipment_type: str | None = None,
        description: str | None = None,
        client_name: str | None = None,
        client_address: str | None = None,
        client_phone: str | None = None,
        notes: str | None = None,
        scheduled_time: str | None = None,
    ) -> bool:
        """Обновление данных заявки"""
        async with self.get_session() as session:
            stmt = select(Order).where(Order.id == order_id)
            result = await session.execute(stmt)
            order = result.scalar_one_or_none()

            if not order:
                logger.error(f"Заявка #{order_id} не найдена")
                return False

            # Обновляем только переданные поля
            if equipment_type is not None:
                order.equipment_type = equipment_type
            if description is not None:
                order.description = description
            if client_name is not None:
                order.client_name = client_name
            if client_address is not None:
                order.client_address = client_address
            if client_phone is not None:
                order.client_phone = client_phone
            if notes is not None:
                order.notes = notes
            if scheduled_time is not None:
                order.scheduled_time = scheduled_time

            order.updated_at = get_now()
            order.version += 1
            await session.commit()

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
        async with self.get_session() as session:
            stmt = (
                select(Order)
                .options(
                    joinedload(Order.assigned_master).joinedload(Master.user),
                    joinedload(Order.dispatcher),
                )
                .where(Order.assigned_master_id == master_id)
            )

            # Исключаем закрытые и отказанные заявки, если указано
            if exclude_closed:
                stmt = stmt.where(Order.status.notin_([OrderStatus.CLOSED, OrderStatus.REFUSED]))

            stmt = stmt.order_by(Order.created_at.desc())

            result = await session.execute(stmt)
            return list(result.scalars().all())

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
        """Обновление финансовых сумм и бонусов заявки"""
        async with self.get_session() as session:
            stmt = select(Order).where(Order.id == order_id)
            result = await session.execute(stmt)
            order = result.scalar_one_or_none()

            if not order:
                logger.error(f"Заявка #{order_id} не найдена")
                return False

            # Обновляем финансовые поля
            if total_amount is not None:
                order.total_amount = total_amount
            if materials_cost is not None:
                order.materials_cost = materials_cost
            if master_profit is not None:
                order.master_profit = master_profit
            if company_profit is not None:
                order.company_profit = company_profit

            # Обновляем бонусы
            if has_review is not None:
                order.has_review = has_review
            if out_of_city is not None:
                order.out_of_city = out_of_city

            order.updated_at = get_now()
            order.version += 1
            await session.commit()

            logger.info(f"Финансовые данные заявки #{order_id} обновлены")
            return True

    async def get_orders_by_period(
        self,
        start_date: datetime,
        end_date: datetime,
        status: str | None = None,
        master_id: int | None = None,
    ) -> list[Order]:
        """Получение заявок за период"""
        async with self.get_session() as session:
            stmt = (
                select(Order)
                .options(
                    joinedload(Order.assigned_master).joinedload(Master.user),
                    joinedload(Order.dispatcher),
                )
                .where(and_(Order.created_at >= start_date, Order.created_at <= end_date))
            )

            if status:
                stmt = stmt.where(Order.status == status)
            if master_id:
                stmt = stmt.where(Order.assigned_master_id == master_id)

            stmt = stmt.order_by(Order.created_at.desc())
            result = await session.execute(stmt)
            return list(result.scalars().all())

    # ==================== AUDIT LOG ====================

    async def add_audit_log(self, user_id: int, action: str, details: str | None = None):
        """Добавление записи в лог аудита"""
        async with self.get_session() as session:
            audit_log = AuditLog(
                user_id=user_id,
                action=action,
                details=details,
                timestamp=get_now(),
            )

            session.add(audit_log)
            await session.commit()

    async def get_audit_logs(self, limit: int = 100) -> list[AuditLog]:
        """Получение логов аудита"""
        async with self.get_session() as session:
            stmt = (
                select(AuditLog)
                .options(joinedload(AuditLog.user))
                .order_by(AuditLog.timestamp.desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    # ==================== STATISTICS ====================

    async def get_statistics(self) -> dict[str, Any]:
        """Получение статистики"""
        async with self.get_session() as session:
            stats = {}

            # Количество пользователей по ролям
            stmt = select(User.role, func.count(User.id).label("count")).group_by(User.role)
            result = await session.execute(stmt)
            stats["users_by_role"] = {row.role: row.count for row in result}

            # Количество заявок по статусам
            stmt = select(Order.status, func.count(Order.id).label("count")).group_by(Order.status)
            result = await session.execute(stmt)
            stats["orders_by_status"] = {row.status: row.count for row in result}

            # Количество активных мастеров
            stmt = select(func.count(Master.id).label("count")).where(
                and_(Master.is_active is True, Master.is_approved is True)
            )
            result = await session.execute(stmt)
            stats["active_masters"] = result.scalar()

            # Общее количество заявок
            stmt = select(func.count(Order.id).label("count"))
            result = await session.execute(stmt)
            stats["total_orders"] = result.scalar()

            return stats

    # ==================== FINANCIAL REPORTS ====================

    async def create_financial_report(self, report: FinancialReport) -> int:
        """Создание финансового отчета"""
        async with self.get_session() as session:
            new_report = FinancialReport(
                report_type=report.report_type,
                period_start=report.period_start,
                period_end=report.period_end,
                total_orders=report.total_orders,
                total_amount=report.total_amount,
                total_materials_cost=report.total_materials_cost,
                total_net_profit=report.total_net_profit,
                total_company_profit=report.total_company_profit,
                total_master_profit=report.total_master_profit,
                average_check=report.average_check,
                created_at=get_now(),
            )

            session.add(new_report)
            await session.flush()

            logger.info(f"Создан финансовый отчет #{new_report.id} типа {report.report_type}")
            return new_report.id

    async def get_financial_report_by_id(self, report_id: int) -> FinancialReport | None:
        """Получение финансового отчета по ID"""
        async with self.get_session() as session:
            stmt = (
                select(FinancialReport)
                .options(selectinload(FinancialReport.master_reports))
                .where(FinancialReport.id == report_id)
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def create_master_financial_report(self, master_report: MasterFinancialReport) -> int:
        """Создание отчета по мастеру"""
        async with self.get_session() as session:
            new_master_report = MasterFinancialReport(
                report_id=master_report.report_id,
                master_id=master_report.master_id,
                master_name=master_report.master_name,
                orders_count=master_report.orders_count,
                total_amount=master_report.total_amount,
                total_materials_cost=master_report.total_materials_cost,
                total_net_profit=master_report.total_net_profit,
                total_master_profit=master_report.total_master_profit,
                total_company_profit=master_report.total_company_profit,
                average_check=master_report.average_check,
                reviews_count=master_report.reviews_count,
                out_of_city_count=master_report.out_of_city_count,
            )

            session.add(new_master_report)
            await session.flush()

            logger.info(
                f"Создан отчет по мастеру #{new_master_report.id} "
                f"для отчета #{master_report.report_id}"
            )
            return new_master_report.id

    async def get_master_reports_by_report_id(self, report_id: int) -> list[MasterFinancialReport]:
        """Получение отчетов по мастерам для конкретного отчета"""
        async with self.get_session() as session:
            stmt = (
                select(MasterFinancialReport)
                .options(joinedload(MasterFinancialReport.master).joinedload(Master.user))
                .where(MasterFinancialReport.report_id == report_id)
                .order_by(MasterFinancialReport.total_amount.desc())
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def get_latest_reports(self, limit: int = 10) -> list[FinancialReport]:
        """Получение последних финансовых отчетов"""
        async with self.get_session() as session:
            stmt = select(FinancialReport).order_by(FinancialReport.created_at.desc()).limit(limit)
            result = await session.execute(stmt)
            return list(result.scalars().all())

    # ==================== SOFT DELETE ====================

    async def soft_delete_user(self, telegram_id: int) -> bool:
        """Мягкое удаление пользователя"""
        async with self.get_session() as session:
            stmt = select(User).where(
                and_(User.telegram_id == telegram_id, User.deleted_at.is_(None))
            )
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                return False
            user.deleted_at = get_now()
            user.version += 1
            await session.commit()

            logger.info(f"Пользователь {telegram_id} мягко удален")
            return True

    async def soft_delete_order(self, order_id: int) -> bool:
        """Мягкое удаление заявки"""
        async with self.get_session() as session:
            stmt = select(Order).where(and_(Order.id == order_id))
            result = await session.execute(stmt)
            order = result.scalar_one_or_none()

            if not order:
                return False
            order.deleted_at = get_now()
            order.version += 1
            await session.commit()

            logger.info(f"Заявка #{order_id} мягко удалена")
            return True

    # ==================== МЕТОДЫ ДЛЯ АРХИВОВ ОТЧЕТОВ ====================

    async def save_master_report_archive(self, archive_data: dict[str, Any]) -> int:
        """
        Сохранение архивного отчета мастера

        Args:
            archive_data: Данные архива

        Returns:
            ID созданной записи
        """
        async with self.get_session() as session:
            archive = MasterReportArchive(**archive_data)
            session.add(archive)
            await session.commit()
            await session.refresh(archive)

            logger.info(
                f"Архивный отчет для мастера {archive.master_id} сохранен (ID: {archive.id})"
            )
            return archive.id

    async def get_master_archived_reports(
        self, master_id: int, limit: int = 10
    ) -> list[MasterReportArchive]:
        """
        Получение списка архивных отчетов мастера

        Args:
            master_id: ID мастера
            limit: Максимальное количество записей

        Returns:
            Список архивных отчетов
        """
        async with self.get_session() as session:
            stmt = (
                select(MasterReportArchive)
                .where(MasterReportArchive.master_id == master_id)
                .order_by(MasterReportArchive.created_at.desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def get_master_report_archive_by_id(self, report_id: int) -> MasterReportArchive | None:
        """
        Получение архивного отчета по ID

        Args:
            report_id: ID отчета

        Returns:
            Архивный отчет или None
        """
        async with self.get_session() as session:
            stmt = select(MasterReportArchive).where(MasterReportArchive.id == report_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

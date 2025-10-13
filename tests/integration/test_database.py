"""
Тесты для модуля database
"""

import pytest

from app.config import OrderStatus, UserRole
from app.database import Database


class TestDatabase:
    """Тесты для класса Database"""

    @pytest.mark.asyncio
    async def test_database_connection(self, db: Database):
        """Тест подключения к базе данных"""
        assert db.connection is not None
        assert db.connection.row_factory is not None

    @pytest.mark.asyncio
    async def test_create_and_get_user(self, db: Database):
        """Тест создания и получения пользователя"""
        telegram_id = 123456789
        username = "test_user"
        first_name = "Test"
        last_name = "User"

        # Создаём пользователя
        user = await db.get_or_create_user(
            telegram_id=telegram_id, username=username, first_name=first_name, last_name=last_name
        )

        assert user is not None
        assert user.telegram_id == telegram_id
        assert user.username == username
        assert user.first_name == first_name
        assert user.last_name == last_name
        assert user.role == UserRole.UNKNOWN

        # Получаем того же пользователя
        user2 = await db.get_user_by_telegram_id(telegram_id)
        assert user2 is not None
        assert user2.telegram_id == telegram_id

    @pytest.mark.asyncio
    async def test_update_user_role(self, db: Database):
        """Тест обновления роли пользователя"""
        telegram_id = 123456789

        # Создаём пользователя
        await db.get_or_create_user(telegram_id=telegram_id)

        # Обновляем роль
        await db.update_user_role(telegram_id, UserRole.ADMIN)

        # Проверяем
        user = await db.get_user_by_telegram_id(telegram_id)
        assert user.role == UserRole.ADMIN

    @pytest.mark.asyncio
    async def test_add_multiple_roles(self, db: Database):
        """Тест добавления множественных ролей"""
        telegram_id = 123456789

        # Создаём пользователя
        await db.get_or_create_user(telegram_id=telegram_id)

        # Добавляем роли
        await db.add_user_role(telegram_id, UserRole.DISPATCHER)
        await db.add_user_role(telegram_id, UserRole.MASTER)

        # Проверяем
        user = await db.get_user_by_telegram_id(telegram_id)
        roles = user.get_roles()
        assert UserRole.DISPATCHER in roles
        assert UserRole.MASTER in roles

    @pytest.mark.asyncio
    async def test_create_and_get_master(self, db: Database):
        """Тест создания и получения мастера"""
        telegram_id = 987654321
        phone = "+79991234567"
        specialization = "Стиральные машины"

        # Создаём пользователя
        await db.get_or_create_user(telegram_id=telegram_id)

        # Создаём мастера
        master = await db.create_master(
            telegram_id=telegram_id, phone=phone, specialization=specialization, is_approved=True
        )

        assert master is not None
        assert master.telegram_id == telegram_id
        assert master.phone == phone
        assert master.specialization == specialization
        assert master.is_approved is True

        # Получаем мастера
        master2 = await db.get_master_by_telegram_id(telegram_id)
        assert master2 is not None
        assert master2.telegram_id == telegram_id

    @pytest.mark.asyncio
    async def test_create_and_get_order(self, db: Database):
        """Тест создания и получения заявки"""
        dispatcher_id = 111222333

        # Создаём диспетчера
        await db.get_or_create_user(telegram_id=dispatcher_id)

        # Создаём заявку
        order = await db.create_order(
            equipment_type="Стиральные машины",
            description="Не включается",
            client_name="Иван Иванов",
            client_address="ул. Ленина, 1",
            client_phone="+79991234567",
            dispatcher_id=dispatcher_id,
            notes="Срочно",
        )

        assert order is not None
        assert order.equipment_type == "Стиральные машины"
        assert order.status == OrderStatus.NEW
        assert order.dispatcher_id == dispatcher_id

        # Получаем заявку
        order2 = await db.get_order_by_id(order.id)
        assert order2 is not None
        assert order2.id == order.id

    @pytest.mark.asyncio
    async def test_assign_master_to_order(self, db: Database):
        """Тест назначения мастера на заявку"""
        dispatcher_id = 111222333
        master_telegram_id = 444555666

        # Создаём пользователей
        await db.get_or_create_user(telegram_id=dispatcher_id)
        await db.get_or_create_user(telegram_id=master_telegram_id)

        # Создаём мастера
        master = await db.create_master(
            telegram_id=master_telegram_id,
            phone="+79991234567",
            specialization="Стиральные машины",
            is_approved=True,
        )

        # Создаём заявку
        order = await db.create_order(
            equipment_type="Стиральные машины",
            description="Не включается",
            client_name="Иван Иванов",
            client_address="ул. Ленина, 1",
            client_phone="+79991234567",
            dispatcher_id=dispatcher_id,
        )

        # Назначаем мастера
        await db.assign_master_to_order(order.id, master.id)

        # Проверяем
        order2 = await db.get_order_by_id(order.id)
        assert order2.assigned_master_id == master.id
        assert order2.status == OrderStatus.ASSIGNED

    @pytest.mark.asyncio
    async def test_update_order_status(self, db: Database):
        """Тест обновления статуса заявки"""
        dispatcher_id = 111222333

        # Создаём пользователя
        await db.get_or_create_user(telegram_id=dispatcher_id)

        # Создаём заявку
        order = await db.create_order(
            equipment_type="Стиральные машины",
            description="Не включается",
            client_name="Иван Иванов",
            client_address="ул. Ленина, 1",
            client_phone="+79991234567",
            dispatcher_id=dispatcher_id,
        )

        # Обновляем статус
        await db.update_order_status(order.id, OrderStatus.CLOSED)

        # Проверяем
        order2 = await db.get_order_by_id(order.id)
        assert order2.status == OrderStatus.CLOSED

    @pytest.mark.asyncio
    async def test_get_all_users(self, db: Database):
        """Тест получения всех пользователей"""
        # Создаём несколько пользователей
        await db.get_or_create_user(telegram_id=111)
        await db.get_or_create_user(telegram_id=222)
        await db.get_or_create_user(telegram_id=333)

        # Получаем всех
        users = await db.get_all_users()
        assert len(users) >= 3

    @pytest.mark.asyncio
    async def test_get_all_masters(self, db: Database):
        """Тест получения всех мастеров"""
        # Создаём несколько мастеров
        for i in range(3):
            telegram_id = 1000 + i
            await db.get_or_create_user(telegram_id=telegram_id)
            await db.create_master(
                telegram_id=telegram_id,
                phone=f"+7999123456{i}",
                specialization="Стиральные машины",
                is_approved=True,
            )

        # Получаем всех
        masters = await db.get_all_masters(only_approved=True)
        assert len(masters) >= 3

    @pytest.mark.asyncio
    async def test_get_statistics(self, db: Database):
        """Тест получения статистики"""
        # Создаём данные
        dispatcher_id = 111
        await db.get_or_create_user(telegram_id=dispatcher_id)

        # Создаём несколько заявок
        for i in range(5):
            await db.create_order(
                equipment_type="Стиральные машины",
                description=f"Проблема {i}",
                client_name="Клиент",
                client_address="Адрес",
                client_phone="+79991234567",
                dispatcher_id=dispatcher_id,
            )

        # Получаем статистику
        stats = await db.get_statistics()
        assert "total_orders" in stats
        assert stats["total_orders"] >= 5

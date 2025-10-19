"""
Тесты для OrderRepository
"""


import aiosqlite
import pytest

from app.config import OrderStatus
from app.database.models import Order
from app.repositories.order_repository import OrderRepository


@pytest.fixture()
async def db_connection():
    """Фикстура для создания тестовой БД в памяти"""
    connection = await aiosqlite.connect(":memory:")
    connection.row_factory = aiosqlite.Row

    # Создаем схему
    await connection.execute(
        """
        CREATE TABLE users (
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
        CREATE TABLE masters (
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
        CREATE TABLE orders (
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
            out_of_city INTEGER DEFAULT 0,
            estimated_completion_date TEXT,
            prepayment_amount REAL,
            rescheduled_count INTEGER DEFAULT 0,
            last_rescheduled_at TIMESTAMP,
            reschedule_reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (assigned_master_id) REFERENCES masters(id),
            FOREIGN KEY (dispatcher_id) REFERENCES users(telegram_id)
        )
    """
    )

    await connection.execute(
        """
        CREATE TABLE order_status_history (
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

    yield connection

    await connection.close()


@pytest.fixture()
async def order_repository(db_connection):
    """Фикстура для OrderRepository"""
    return OrderRepository(db_connection)


@pytest.fixture()
async def sample_dispatcher(db_connection):
    """Создание тестового диспетчера"""
    await db_connection.execute(
        "INSERT INTO users (telegram_id, username, first_name, role) VALUES (?, ?, ?, ?)",
        (123456, "dispatcher1", "Иван", "DISPATCHER"),
    )
    await db_connection.commit()
    return 123456


@pytest.mark.asyncio()
async def test_create_order(order_repository, sample_dispatcher):
    """Тест создания заявки"""
    order = await order_repository.create(
        equipment_type="Холодильник",
        description="Не работает",
        client_name="Иван Иванов",
        client_address="ул. Ленина 1",
        client_phone="79991234567",
        dispatcher_id=sample_dispatcher,
        notes="Срочно",
        scheduled_time="14:00",
    )

    assert order.id is not None
    assert order.equipment_type == "Холодильник"
    assert order.description == "Не работает"
    assert order.client_name == "Иван Иванов"
    assert order.status == OrderStatus.NEW
    assert order.dispatcher_id == sample_dispatcher


@pytest.mark.asyncio()
async def test_get_order_by_id(order_repository, sample_dispatcher):
    """Тест получения заявки по ID"""
    # Создаем заявку
    created_order = await order_repository.create(
        equipment_type="Духовой шкаф",
        description="Не включается",
        client_name="Петр Петров",
        client_address="ул. Пушкина 10",
        client_phone="79991234567",
        dispatcher_id=sample_dispatcher,
    )

    # Получаем заявку
    fetched_order = await order_repository.get_by_id(created_order.id)

    assert fetched_order is not None
    assert fetched_order.id == created_order.id
    assert fetched_order.equipment_type == "Духовой шкаф"
    assert fetched_order.client_name == "Петр Петров"


@pytest.mark.asyncio()
async def test_get_order_by_id_not_found(order_repository):
    """Тест получения несуществующей заявки"""
    order = await order_repository.get_by_id(99999)
    assert order is None


@pytest.mark.asyncio()
async def test_get_all_orders(order_repository, sample_dispatcher):
    """Тест получения всех заявок"""
    # Создаем несколько заявок
    await order_repository.create(
        equipment_type="Холодильник",
        description="Не работает",
        client_name="Иван Иванов",
        client_address="ул. Ленина 1",
        client_phone="79991234567",
        dispatcher_id=sample_dispatcher,
    )

    await order_repository.create(
        equipment_type="Духовой шкаф",
        description="Не включается",
        client_name="Петр Петров",
        client_address="ул. Пушкина 10",
        client_phone="79991234567",
        dispatcher_id=sample_dispatcher,
    )

    # Получаем все заявки
    orders = await order_repository.get_all()

    assert len(orders) == 2
    assert all(isinstance(order, Order) for order in orders)


@pytest.mark.asyncio()
async def test_get_all_orders_with_status_filter(order_repository, sample_dispatcher):
    """Тест получения заявок с фильтром по статусу"""
    # Создаем заявки с разными статусами
    order1 = await order_repository.create(
        equipment_type="Холодильник",
        description="Не работает",
        client_name="Иван Иванов",
        client_address="ул. Ленина 1",
        client_phone="79991234567",
        dispatcher_id=sample_dispatcher,
    )

    order2 = await order_repository.create(
        equipment_type="Духовой шкаф",
        description="Не включается",
        client_name="Петр Петров",
        client_address="ул. Пушкина 10",
        client_phone="79991234567",
        dispatcher_id=sample_dispatcher,
    )

    # Изменяем статус одной заявки
    await order_repository.update_status(order2.id, OrderStatus.ASSIGNED, sample_dispatcher)

    # Получаем только NEW заявки
    new_orders = await order_repository.get_all(status=OrderStatus.NEW)
    assert len(new_orders) == 1
    assert new_orders[0].id == order1.id

    # Получаем только ASSIGNED заявки
    assigned_orders = await order_repository.get_all(status=OrderStatus.ASSIGNED)
    assert len(assigned_orders) == 1
    assert assigned_orders[0].id == order2.id


@pytest.mark.asyncio()
async def test_update_status(order_repository, sample_dispatcher):
    """Тест обновления статуса заявки"""
    # Создаем заявку
    order = await order_repository.create(
        equipment_type="Холодильник",
        description="Не работает",
        client_name="Иван Иванов",
        client_address="ул. Ленина 1",
        client_phone="79991234567",
        dispatcher_id=sample_dispatcher,
    )

    # Обновляем статус
    success = await order_repository.update_status(
        order.id,
        OrderStatus.ASSIGNED,
        sample_dispatcher,
        notes="Назначен мастер",
    )

    assert success is True

    # Проверяем, что статус изменился
    updated_order = await order_repository.get_by_id(order.id)
    assert updated_order.status == OrderStatus.ASSIGNED


@pytest.mark.asyncio()
async def test_update(order_repository, sample_dispatcher):
    """Тест обновления данных заявки"""
    # Создаем заявку
    order = await order_repository.create(
        equipment_type="Холодильник",
        description="Не работает",
        client_name="Иван Иванов",
        client_address="ул. Ленина 1",
        client_phone="79991234567",
        dispatcher_id=sample_dispatcher,
    )

    # Обновляем данные
    success = await order_repository.update(
        order.id,
        {
            "notes": "Дополнительная информация",
            "scheduled_time": "15:00",
        },
    )

    assert success is True

    # Проверяем, что данные обновились
    updated_order = await order_repository.get_by_id(order.id)
    assert updated_order.notes == "Дополнительная информация"
    assert updated_order.scheduled_time == "15:00"


@pytest.mark.asyncio()
async def test_get_status_history(order_repository, sample_dispatcher):
    """Тест получения истории статусов"""
    # Создаем заявку
    order = await order_repository.create(
        equipment_type="Холодильник",
        description="Не работает",
        client_name="Иван Иванов",
        client_address="ул. Ленина 1",
        client_phone="79991234567",
        dispatcher_id=sample_dispatcher,
    )

    # Меняем статус несколько раз
    await order_repository.update_status(
        order.id, OrderStatus.ASSIGNED, sample_dispatcher, "Назначен мастер"
    )
    await order_repository.update_status(
        order.id, OrderStatus.ACCEPTED, sample_dispatcher, "Мастер принял"
    )

    # Получаем историю
    history = await order_repository.get_status_history(order.id)

    assert len(history) == 2
    assert history[0]["new_status"] == OrderStatus.ACCEPTED
    assert history[1]["new_status"] == OrderStatus.ASSIGNED


@pytest.mark.asyncio()
async def test_transaction_rollback(order_repository, db_connection):
    """Тест отката транзакции при ошибке"""
    # Начинаем транзакцию
    try:
        async with order_repository.transaction():
            # Выполняем операцию
            await db_connection.execute(
                "INSERT INTO orders (equipment_type, description, client_name, client_address, client_phone, dispatcher_id) VALUES (?, ?, ?, ?, ?, ?)",
                ("Холодильник", "Тест", "Тест", "Тест", "123", 999999),
            )

            # Искусственно вызываем ошибку
            raise ValueError("Test error")
    except ValueError:
        pass

    # Проверяем, что транзакция откатилась
    cursor = await db_connection.execute("SELECT COUNT(*) FROM orders")
    row = await cursor.fetchone()
    assert row[0] == 0

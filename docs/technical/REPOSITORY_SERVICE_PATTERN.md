# Repository + Service Layer Pattern

## 📋 Обзор

В проекте реализован паттерн **Repository + Service** для улучшения архитектуры и тестируемости кода.

### Преимущества:
- ✅ **Разделение ответственности**: бизнес-логика отделена от работы с БД
- ✅ **Тестируемость**: легко мокировать репозитории в тестах
- ✅ **Переиспользование**: общие операции инкапсулированы в сервисах
- ✅ **Гибкость**: легко поменять БД (SQLite → PostgreSQL)
- ✅ **Clean Architecture**: следование SOLID принципам

---

## 🏗️ Архитектура

```
┌─────────────────────────────────────────┐
│           Handlers (UI Layer)           │
│  ├── admin.py                           │
│  ├── dispatcher.py                      │
│  └── master.py                          │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│        Services (Business Logic)        │
│  ├── OrderService                       │
│  ├── UserService                        │
│  └── MasterService                      │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│       Repositories (Data Access)        │
│  ├── OrderRepository                    │
│  ├── UserRepository                     │
│  └── MasterRepository                   │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│         Database (aiosqlite)            │
└─────────────────────────────────────────┘
```

---

## 📦 Структура проекта

```
app/
├── repositories/              # Слой доступа к данным
│   ├── __init__.py
│   ├── base.py               # Базовый репозиторий
│   ├── order_repository.py   # Работа с заявками
│   ├── user_repository.py    # Работа с пользователями
│   └── master_repository.py  # Работа с мастерами
│
├── services/                 # Бизнес-логика
│   ├── __init__.py
│   ├── service_factory.py    # Фабрика сервисов
│   ├── order_service.py      # Управление заявками
│   ├── user_service.py       # Управление пользователями
│   └── master_service.py     # Управление мастерами
│
└── handlers/                 # UI слой (обработчики Telegram)
    ├── admin.py
    ├── dispatcher.py
    └── master.py
```

---

## 🚀 Использование в handlers

### Старый подход (direct DB access):

```python
from aiogram import Router, F
from aiogram.types import Message
from app.database.db import Database

router = Router()

@router.message(F.text == "Создать заявку")
async def create_order(message: Message, db: Database):
    # Прямое обращение к БД - плохо!
    order = await db.create_order(
        equipment_type="Холодильник",
        description="Не работает",
        client_name="Иван Иванов",
        client_address="ул. Ленина 1",
        client_phone="79991234567",
        dispatcher_id=message.from_user.id,
    )
    await message.answer(f"Заявка #{order.id} создана")
```

### Новый подход (Service Layer):

```python
from aiogram import Router, F
from aiogram.types import Message
from app.database.db import Database

router = Router()

@router.message(F.text == "Создать заявку")
async def create_order(message: Message, db: Database):
    # Используем сервис - хорошо!
    order_service = db.services.order_service

    try:
        order = await order_service.create_order(
            equipment_type="Холодильник",
            description="Не работает",
            client_name="Иван Иванов",
            client_address="ул. Ленина 1",
            client_phone="79991234567",
            dispatcher_id=message.from_user.id,
        )
        await message.answer(f"Заявка #{order.id} создана")
    except ValueError as e:
        await message.answer(f"Ошибка: {e}")
```

---

## 💡 Примеры использования

### 1. OrderService

#### Создание заявки с валидацией диспетчера:

```python
order_service = db.services.order_service

order = await order_service.create_order(
    equipment_type="Духовой шкаф",
    description="Не включается",
    client_name="Петр Петров",
    client_address="ул. Пушкина 10",
    client_phone="79991234567",
    dispatcher_id=telegram_id,
)
```

#### Назначение мастера с валидацией статусов:

```python
order_service = db.services.order_service

try:
    await order_service.assign_master(
        order_id=123,
        master_id=5,
        assigned_by=admin_telegram_id,
    )
except InvalidStateTransitionError as e:
    await message.answer(f"Невозможно назначить мастера: {e}")
```

#### Изменение статуса с проверкой прав:

```python
order_service = db.services.order_service

try:
    await order_service.change_status(
        order_id=123,
        new_status=OrderStatus.ACCEPTED,
        changed_by=master_telegram_id,
        notes="Мастер выехал к клиенту",
    )
except InvalidStateTransitionError as e:
    await message.answer(f"Невозможно изменить статус: {e}")
```

#### Проверка возможности изменения статуса:

```python
order_service = db.services.order_service

can_close = await order_service.can_change_status(
    order_id=123,
    new_status=OrderStatus.CLOSED,
    user_telegram_id=master_telegram_id,
)

if can_close:
    # Показать кнопку "Закрыть заявку"
    ...
```

---

### 2. UserService

#### Получение или создание пользователя:

```python
user_service = db.services.user_service

user = await user_service.get_or_create_user(
    telegram_id=message.from_user.id,
    username=message.from_user.username,
    first_name=message.from_user.first_name,
    last_name=message.from_user.last_name,
)
```

#### Управление ролями:

```python
user_service = db.services.user_service

# Добавление роли
await user_service.add_role(telegram_id, UserRole.MASTER)

# Удаление роли
await user_service.remove_role(telegram_id, UserRole.DISPATCHER)

# Проверка роли
has_admin = await user_service.has_role(telegram_id, UserRole.ADMIN)

# Получение всех ролей
roles = await user_service.get_user_roles(telegram_id)
```

#### Получение пользователей по роли:

```python
user_service = db.services.user_service

# Все диспетчеры
dispatchers = await user_service.get_users_by_role(UserRole.DISPATCHER)

# Все мастера
masters = await user_service.get_users_by_role(UserRole.MASTER)
```

---

### 3. MasterService

#### Регистрация мастера:

```python
master_service = db.services.master_service

master, is_new = await master_service.register_master(
    telegram_id=message.from_user.id,
    phone="79991234567",
    specialization="Холодильное оборудование",
)

if is_new:
    await message.answer("Заявка на регистрацию отправлена администратору")
else:
    await message.answer("Вы уже зарегистрированы как мастер")
```

#### Одобрение мастера (только админ):

```python
master_service = db.services.master_service

try:
    await master_service.approve_master(
        master_id=5,
        approved_by=admin_telegram_id,
    )
except ValueError as e:
    await message.answer(f"Ошибка: {e}")
```

#### Получение всех мастеров:

```python
master_service = db.services.master_service

# Все одобренные и активные мастера
active_masters = await master_service.get_all_masters(
    is_active=True,
    is_approved=True,
)

# Мастера на одобрении
pending_masters = await master_service.get_all_masters(
    is_approved=False,
)
```

---

## 🧪 Тестирование

### Пример unit теста для OrderService:

```python
import pytest
from unittest.mock import AsyncMock
from app.services.order_service import OrderService
from app.database.models import User, Master, Order
from app.config import UserRole, OrderStatus

@pytest.mark.asyncio
async def test_create_order_success():
    # Mock репозиториев
    order_repo = AsyncMock()
    user_repo = AsyncMock()
    master_repo = AsyncMock()

    # Подготовка данных
    dispatcher = User(
        telegram_id=123,
        username="dispatcher",
        role=UserRole.DISPATCHER,
    )
    user_repo.get_by_telegram_id.return_value = dispatcher

    order = Order(
        id=1,
        equipment_type="Холодильник",
        description="Не работает",
        client_name="Иван",
        client_address="ул. Ленина 1",
        client_phone="79991234567",
        dispatcher_id=123,
        status=OrderStatus.NEW,
    )
    order_repo.create.return_value = order

    # Создание сервиса с моками
    service = OrderService(order_repo, user_repo, master_repo)

    # Вызов метода
    result = await service.create_order(
        equipment_type="Холодильник",
        description="Не работает",
        client_name="Иван",
        client_address="ул. Ленина 1",
        client_phone="79991234567",
        dispatcher_id=123,
    )

    # Проверки
    assert result.id == 1
    assert result.status == OrderStatus.NEW
    user_repo.get_by_telegram_id.assert_called_once_with(123)
    order_repo.create.assert_called_once()

@pytest.mark.asyncio
async def test_assign_master_invalid_transition():
    order_repo = AsyncMock()
    user_repo = AsyncMock()
    master_repo = AsyncMock()

    # Заявка уже закрыта
    order = Order(id=1, status=OrderStatus.CLOSED)
    order_repo.get_by_id.return_value = order

    master = Master(id=5, is_approved=True)
    master_repo.get_by_id.return_value = master

    user = User(telegram_id=123, role=UserRole.DISPATCHER)
    user_repo.get_by_telegram_id.return_value = user

    service = OrderService(order_repo, user_repo, master_repo)

    # Должна быть ошибка перехода статуса
    with pytest.raises(InvalidStateTransitionError):
        await service.assign_master(1, 5, 123)
```

---

## 📝 Руководство по миграции

### Шаг 1: Определить, какая операция нужна

- **Работа с заявками** → `db.services.order_service`
- **Работа с пользователями** → `db.services.user_service`
- **Работа с мастерами** → `db.services.master_service`

### Шаг 2: Заменить прямые вызовы БД на сервисы

**Было:**
```python
order = await db.create_order(...)
```

**Стало:**
```python
order = await db.services.order_service.create_order(...)
```

### Шаг 3: Обработать исключения

Сервисы выбрасывают исключения при бизнес-ошибках:
- `ValueError` - некорректные данные
- `InvalidStateTransitionError` - недопустимый переход статуса

```python
try:
    await db.services.order_service.assign_master(...)
except ValueError as e:
    await message.answer(f"❌ {e}")
except InvalidStateTransitionError as e:
    await message.answer(f"⚠️ Невозможно выполнить действие: {e}")
```

---

## 🔧 Совместимость

**Важно:** Старые методы `Database` класса (например, `db.create_order()`) **продолжают работать** для обратной совместимости.

Миграция может происходить постепенно:
1. Новые фичи - используют сервисы
2. Старый код - продолжает работать
3. Постепенный рефакторинг - по возможности

---

## 🎯 Best Practices

1. **Всегда используйте сервисы в handlers**
   ```python
   order_service = db.services.order_service
   ```

2. **Не обращайтесь к репозиториям напрямую из handlers**
   ```python
   # ❌ Плохо
   order_repo = OrderRepository(db.connection)

   # ✅ Хорошо
   order_service = db.services.order_service
   ```

3. **Обрабатывайте исключения**
   ```python
   try:
       await order_service.change_status(...)
   except (ValueError, InvalidStateTransitionError) as e:
       await message.answer(f"Ошибка: {e}")
   ```

4. **Используйте type hints**
   ```python
   from app.database.models import Order

   order: Order = await order_service.get_order(order_id)
   ```

---

## 📚 Дополнительные материалы

- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Repository Pattern](https://martinfowler.com/eaaCatalog/repository.html)
- [Service Layer](https://martinfowler.com/eaaCatalog/serviceLayer.html)

---

**Версия:** 1.0.0
**Дата:** 20 октября 2025

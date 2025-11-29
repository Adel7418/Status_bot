# Технические рекомендации: Telegram Repair Bot

**Дата:** 19 октября 2025
**Версия проекта:** 1.1.0
**Статус:** Critical Review - Production Readiness Assessment

---

## 🔑 Ключевые технологии и их версии

### Основной стек (используется)

| Библиотека | Версия | Trust Score | Snippets | Статус |
|-----------|--------|-------------|----------|--------|
| **aiogram** | 3.16.0 | 7.5/10 | 4423 | ✅ Актуальная |
| **pydantic** | 2.10.3 | 9.6/10 | 530 | ✅ Актуальная (v2) |
| **alembic** | 1.13.1 | - | 363 | ✅ Актуальная |
| **aiosqlite** | 0.20.0 | - | - | ✅ Актуальная |
| **APScheduler** | 3.11.0 | - | - | ⚠️ Stable (v4 breaking) |
| **openpyxl** | 3.1.5 | - | - | ✅ Актуальная |

### Рекомендуемые дополнения

| Библиотека | Версия | Назначение | Приоритет |
|-----------|--------|------------|----------|
| **Redis** | 5.2.1+ | FSM Storage (персистентность) | P0 |
| **PostgreSQL** | 14+ | Production БД | P0 |
| **asyncpg** | 0.29.0 | Async PostgreSQL driver | P0 |
| **SQLAlchemy** | 2.0+ | ORM (вместо raw SQL) | P1 |
| **Sentry** | 2.19.0+ | Error tracking | P1 |
| **Prometheus** | - | Метрики | P1 |
| **pytest** | 8.3.0+ | Расширение тестов | P1 |

---

## 📚 Документация библиотек (Context7)

### Aiogram 3.x

**Library ID:** `/websites/aiogram_dev_en_v3_22_0`
**Trust Score:** 7.5/10
**Code Snippets:** 4423

**Ключевые возможности:**
- ✅ Async/await нативная поддержка
- ✅ FSM (Finite State Machine) для диалогов
- ✅ Middleware chain
- ✅ Webhook и Long polling
- ✅ Type hints и Pydantic integration

**Критичные улучшения для проекта:**
1. **Rate limiting:** Использовать `aiogram.utils.token_bucket.TokenBucket`
   ```python
   from aiogram.utils.token_bucket import TokenBucket

   rate_limiter = TokenBucket(rate=3, capacity=10)  # 3 req/sec, burst 10
   ```

2. **Redis Storage:** Переход с MemoryStorage
   ```python
   from aiogram.fsm.storage.redis import RedisStorage

   storage = RedisStorage.from_url("redis://localhost:6379")
   dp = Dispatcher(storage=storage)
   ```

3. **Webhook mode:** Для production (вместо long polling)
   ```python
   # bot.py
   await bot.set_webhook(
       url=f"{WEBHOOK_URL}/webhook",
       allowed_updates=["message", "callback_query"]
   )
   ```

**Ссылки:**
- Официальная документация: https://docs.aiogram.dev/en/v3.22.0/
- Миграция v2→v3: https://docs.aiogram.dev/en/v3.22.0/migration_2_to_3.html
- Best practices: https://mastergroosha.github.io/aiogram-3-guide/ (Trust: 9.4/10)

---

### Pydantic 2.x

**Library ID:** `/pydantic/pydantic`
**Trust Score:** 9.6/10
**Code Snippets:** 530

**Ключевые возможности:**
- ✅ Type-safe валидация
- ✅ Автоматическая сериализация/десериализация
- ✅ Custom validators
- ✅ Field constraints
- ✅ Performance (Pydantic Core в Rust)

**Текущее использование в проекте:**
- ✅ `app/schemas/order.py` - OrderCreateSchema
- ✅ `app/schemas/master.py` - MasterApplicationSchema
- ✅ `app/schemas/user.py` - UserSchema

**Рекомендации:**
1. **Расширить схемы для всех операций:**
   ```python
   # app/schemas/order.py
   from pydantic import BaseModel, Field, field_validator

   class OrderUpdateSchema(BaseModel):
       equipment_type: str | None = None
       description: str | None = Field(None, max_length=500)
       client_name: str | None = None

       @field_validator('client_phone')
       @classmethod
       def validate_phone(cls, v):
           if not re.match(r'^\+?[0-9]{10,15}$', v):
               raise ValueError('Invalid phone format')
           return v
   ```

2. **Callback data валидация:**
   ```python
   from pydantic import BaseModel

   class AssignMasterCallback(BaseModel):
       action: str = "assign_master"
       order_id: int
       master_id: int

   # Usage
   data = AssignMasterCallback(order_id=123, master_id=456)
   await callback.answer(callback_data=data.model_dump_json())
   ```

3. **Config валидация:**
   ```python
   # app/core/config.py
   from pydantic_settings import BaseSettings

   class Settings(BaseSettings):
       bot_token: str = Field(..., min_length=46)
       admin_ids: list[int]
       database_url: str

       model_config = {
           "env_file": ".env",
           "case_sensitive": False
       }

   settings = Settings()
   ```

**Ссылки:**
- Документация: https://docs.pydantic.dev/
- Migration v1→v2: https://docs.pydantic.dev/latest/migration/

---

### Alembic (SQLAlchemy)

**Library ID:** `/sqlalchemy/alembic`
**Code Snippets:** 363

**Текущее состояние:**
- ✅ 5 миграций создано
- ✅ `alembic.ini` настроен
- ✅ Используется для версионирования схемы

**Рекомендации:**

1. **Автогенерация миграций:**
   ```bash
   # Вместо ручного написания
   alembic revision --autogenerate -m "Add new field"
   ```

2. **Offline mode для production:**
   ```python
   # migrations/env.py
   def run_migrations_offline():
       context.configure(
           url=url,
           target_metadata=target_metadata,
           literal_binds=True,
           dialect_opts={"paramstyle": "named"},
       )
   ```

3. **Downgrade стратегия:**
   ```bash
   # Всегда тестировать rollback
   alembic downgrade -1
   alembic upgrade head
   ```

4. **Миграция на PostgreSQL:**
   ```ini
   # alembic.ini
   sqlalchemy.url = postgresql+asyncpg://user:pass@localhost/repairbot
   ```

**Ссылки:**
- Документация: https://alembic.sqlalchemy.org/
- Best practices: https://alembic.sqlalchemy.org/en/latest/cookbook.html

---

## 🔧 Архитектурные рефакторинги

### 1. Миграция на SQLAlchemy ORM (P1)

**Проблема:** Raw SQL в `app/database/db.py` - риск SQL injection, сложность поддержки

**Решение:**
```python
# app/database/models_orm.py
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, ForeignKey

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(unique=True)
    username: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(100), default="UNKNOWN")

    # Relationships
    orders: Mapped[list["Order"]] = relationship(back_populates="dispatcher")

# app/database/repository.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def create(self, user_data: dict) -> User:
        user = User(**user_data)
        self.session.add(user)
        await self.session.commit()
        return user
```

**Преимущества:**
- ✅ Type safety
- ✅ Автоматическая защита от SQL injection
- ✅ Relationships (lazy loading, eager loading)
- ✅ Query composition

---

### 2. Repository Pattern (P2)

**Проблема:** Handlers напрямую работают с Database

**Решение:**
```python
# app/repositories/order_repository.py
class OrderRepository:
    def __init__(self, db: Database):
        self.db = db

    async def create(self, data: OrderCreateSchema) -> Order:
        # Бизнес-логика + валидация
        return await self.db.create_order(**data.model_dump())

    async def get_by_id(self, order_id: int) -> Order | None:
        return await self.db.get_order_by_id(order_id)

    async def assign_master(self, order_id: int, master_id: int) -> bool:
        # Транзакционная логика
        async with self.db.transaction():
            order = await self.get_by_id(order_id)
            if not order:
                raise OrderNotFound(order_id)

            # Validate state transition
            if order.status not in [OrderStatus.NEW, OrderStatus.REFUSED]:
                raise InvalidStateTransition(order.status, OrderStatus.ASSIGNED)

            return await self.db.assign_master_to_order(order_id, master_id)

# app/handlers/dispatcher.py
@router.callback_query(F.data.startswith("assign_master_"))
async def assign_master_handler(
    callback: CallbackQuery,
    order_repo: OrderRepository = Depends()  # DI
):
    _, _, order_id, master_id = callback.data.split("_")
    try:
        await order_repo.assign_master(int(order_id), int(master_id))
        await callback.answer("✅ Мастер назначен")
    except OrderNotFound:
        await callback.answer("❌ Заявка не найдена", show_alert=True)
    except InvalidStateTransition as e:
        await callback.answer(f"❌ {e}", show_alert=True)
```

---

### 3. State Machine для Order (P0)

**Проблема:** Нет валидации переходов статусов

**Решение:**
```python
# app/domain/order_state_machine.py
from enum import Enum
from typing import Set

class OrderStatus(str, Enum):
    NEW = "NEW"
    ASSIGNED = "ASSIGNED"
    ACCEPTED = "ACCEPTED"
    ONSITE = "ONSITE"
    CLOSED = "CLOSED"
    REFUSED = "REFUSED"
    DR = "DR"

class OrderStateMachine:
    TRANSITIONS: dict[OrderStatus, Set[OrderStatus]] = {
        OrderStatus.NEW: {OrderStatus.ASSIGNED, OrderStatus.REFUSED},
        OrderStatus.ASSIGNED: {OrderStatus.ACCEPTED, OrderStatus.REFUSED},
        OrderStatus.ACCEPTED: {OrderStatus.ONSITE, OrderStatus.DR},
        OrderStatus.ONSITE: {OrderStatus.CLOSED, OrderStatus.DR},
        OrderStatus.DR: {OrderStatus.CLOSED},
        OrderStatus.REFUSED: {OrderStatus.NEW},  # Reopen
        OrderStatus.CLOSED: set(),  # Terminal state
    }

    @classmethod
    def can_transition(cls, from_state: OrderStatus, to_state: OrderStatus) -> bool:
        return to_state in cls.TRANSITIONS.get(from_state, set())

    @classmethod
    def validate_transition(cls, from_state: OrderStatus, to_state: OrderStatus):
        if not cls.can_transition(from_state, to_state):
            raise InvalidStateTransition(
                f"Cannot transition from {from_state} to {to_state}"
            )

# Usage in repository
async def update_status(self, order_id: int, new_status: OrderStatus):
    order = await self.get_by_id(order_id)
    OrderStateMachine.validate_transition(order.status, new_status)
    await self.db.update_order_status(order_id, new_status)
```

---

### 4. Dependency Injection (P2)

**Проблема:** Глобальные зависимости, сложность тестирования

**Решение:**
```python
# app/di.py (Dependency Injector)
from aiogram import Dispatcher
from collections.abc import AsyncGenerator

async def get_db() -> AsyncGenerator[Database, None]:
    db = Database()
    await db.connect()
    try:
        yield db
    finally:
        await db.disconnect()

async def get_order_repo(db: Database = Depends(get_db)) -> OrderRepository:
    return OrderRepository(db)

# Register in dispatcher
def setup_di(dp: Dispatcher):
    dp["db"] = Database()
    dp["order_repo"] = OrderRepository(dp["db"])

# Usage in handlers
@router.message(Command("create_order"))
async def create_order_cmd(
    message: Message,
    state: FSMContext,
    order_repo: OrderRepository = Depends(get_order_repo)
):
    # Handler logic
    pass
```

---

## 🔒 Безопасность

### 1. Секреты (P0)

**Текущее состояние:** `.env` файл с plaintext токенами

**Решение:**

**Docker Secrets:**
```yaml
# docker-compose.yml
version: '3.8'
services:
  bot:
    secrets:
      - bot_token
      - database_url
    environment:
      BOT_TOKEN_FILE: /run/secrets/bot_token
      DATABASE_URL_FILE: /run/secrets/database_url

secrets:
  bot_token:
    external: true
  database_url:
    external: true
```

```python
# app/core/config.py
import os

def read_secret(name: str) -> str:
    secret_file = os.getenv(f"{name}_FILE")
    if secret_file and os.path.exists(secret_file):
        with open(secret_file) as f:
            return f.read().strip()
    return os.getenv(name, "")

class Config:
    BOT_TOKEN = read_secret("BOT_TOKEN")
    DATABASE_URL = read_secret("DATABASE_URL")
```

**HashiCorp Vault (для enterprise):**
```python
import hvac

client = hvac.Client(url='https://vault:8200')
client.token = os.getenv('VAULT_TOKEN')

secrets = client.secrets.kv.v2.read_secret_version(path='repairbot')
BOT_TOKEN = secrets['data']['data']['bot_token']
```

---

### 2. Rate Limiting (P0)

**Решение:**
```python
# app/middlewares/rate_limit.py
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from cachetools import TTLCache

class RateLimitMiddleware(BaseMiddleware):
    def __init__(self, rate: int = 3, period: int = 1):
        self.cache = TTLCache(maxsize=10000, ttl=period)
        self.rate = rate

    async def __call__(self, handler, event, data):
        user_id = event.from_user.id

        # Check rate
        requests = self.cache.get(user_id, 0)
        if requests >= self.rate:
            if isinstance(event, Message):
                await event.answer("⚠️ Слишком много запросов. Подождите.")
            else:
                await event.answer("⚠️ Rate limit", show_alert=True)
            return

        # Increment counter
        self.cache[user_id] = requests + 1

        return await handler(event, data)

# Register
dp.message.middleware(RateLimitMiddleware(rate=3, period=1))
```

---

### 3. PII Masking (P1)

**Решение:**
```python
# app/utils/logging.py
import re
import logging

class PIIMaskingFilter(logging.Filter):
    PATTERNS = {
        'phone': (r'\+?\d{10,15}', lambda m: m.group()[:3] + '*' * 7),
        'address': (r'ул\.\s+[\w\s,]+\d+', lambda m: '***адрес***'),
        'name': (r'[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+', lambda m: '***ФИО***'),
    }

    def filter(self, record):
        message = record.getMessage()
        for pattern, replacer in self.PATTERNS.values():
            message = re.sub(pattern, replacer, message)
        record.msg = message
        return True

# Setup
logger = logging.getLogger(__name__)
logger.addFilter(PIIMaskingFilter())
```

---

## 📊 Мониторинг и observability

### 1. Sentry Integration (P1)

```python
# app/utils/sentry.py
import sentry_sdk
from sentry_sdk.integrations.asyncio import AsyncioIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

def init_sentry():
    if not Config.SENTRY_DSN:
        return

    sentry_sdk.init(
        dsn=Config.SENTRY_DSN,
        environment=Config.ENVIRONMENT,
        traces_sample_rate=0.1,  # 10% transactions
        profiles_sample_rate=0.1,
        integrations=[
            AsyncioIntegration(),
            LoggingIntegration(level=logging.INFO, event_level=logging.ERROR)
        ],
        before_send=before_send_filter,
    )

def before_send_filter(event, hint):
    # Маскируем PII в Sentry
    if 'request' in event:
        if 'data' in event['request']:
            # Mask sensitive fields
            pass
    return event
```

---

### 2. Prometheus Metrics (P1)

```python
# app/utils/metrics.py
from prometheus_client import Counter, Histogram, Gauge
from prometheus_client import start_http_server

# Metrics
orders_created = Counter('orders_created_total', 'Total orders created')
orders_by_status = Gauge('orders_by_status', 'Orders by status', ['status'])
handler_duration = Histogram('handler_duration_seconds', 'Handler duration', ['handler'])

# Export
start_http_server(8000)  # Prometheus scrape endpoint

# Usage in handlers
@handler_duration.labels(handler='create_order').time()
async def create_order_handler(message: Message):
    # ...
    orders_created.inc()
    orders_by_status.labels(status='NEW').inc()
```

---

## 🧪 Тестирование

### Расширение coverage (P1)

**Цель:** 80% coverage

**Стратегия:**

1. **Unit тесты (handlers):**
```python
# tests/unit/test_order_handlers.py
import pytest
from aiogram.test_utils.mocked_bot import MockedBot
from app.handlers.dispatcher import create_order_handler

@pytest.mark.asyncio
async def test_create_order_success(mock_db, mock_order_repo):
    bot = MockedBot()
    message = bot.get_message(text="/create_order", from_user=bot.user)

    await create_order_handler(message, state=FSMContext())

    assert message.answer.called
    assert "выберите тип техники" in message.answer.call_args[0][0].lower()
```

2. **Integration тесты (database):**
```python
# tests/integration/test_order_flow.py
@pytest.mark.asyncio
async def test_full_order_lifecycle(db):
    # Create order
    order = await db.create_order(
        equipment_type="Стиральная машина",
        description="Не включается",
        client_name="Иван",
        client_address="ул. Ленина 1",
        client_phone="+79991234567",
        dispatcher_id=123456789
    )
    assert order.status == OrderStatus.NEW

    # Assign master
    await db.assign_master_to_order(order.id, master_id=1)
    order = await db.get_order_by_id(order.id)
    assert order.status == OrderStatus.ASSIGNED

    # Close order
    await db.update_order_status(order.id, OrderStatus.CLOSED)
    order = await db.get_order_by_id(order.id)
    assert order.status == OrderStatus.CLOSED
```

3. **E2E тесты (bot interaction):**
```python
# tests/e2e/test_bot_commands.py
@pytest.mark.asyncio
async def test_start_command_flow():
    async with BotTestClient() as client:
        # Send /start
        response = await client.send("/start")
        assert "Добро пожаловать" in response.text

        # Click "Создать заявку"
        response = await client.click_button("Создать заявку")
        assert "выберите тип техники" in response.text
```

---

## 📈 Performance

### 1. Пагинация (P2)

**Проблема:** `get_all_orders()` без лимитов → OOM

**Решение:**
```python
# app/repositories/order_repository.py
async def get_paginated(
    self,
    page: int = 1,
    page_size: int = 20,
    filters: dict | None = None
) -> tuple[list[Order], int]:
    offset = (page - 1) * page_size

    query = select(Order)
    if filters:
        # Apply filters
        pass

    # Get total count
    count_query = select(func.count()).select_from(Order)
    total = await self.session.scalar(count_query)

    # Get page
    query = query.offset(offset).limit(page_size)
    result = await self.session.execute(query)
    orders = result.scalars().all()

    return orders, total

# Inline keyboard pagination
def build_order_list_keyboard(page: int, total_pages: int):
    keyboard = InlineKeyboardBuilder()

    # Orders on current page
    for order in orders:
        keyboard.button(text=f"#{order.id}", callback_data=f"order_{order.id}")

    # Pagination buttons
    row = []
    if page > 1:
        row.append(InlineKeyboardButton(text="◀️", callback_data=f"orders_page_{page-1}"))
    row.append(InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        row.append(InlineKeyboardButton(text="▶️", callback_data=f"orders_page_{page+1}"))

    keyboard.row(*row)
    return keyboard.as_markup()
```

---

### 2. Connection pooling (PostgreSQL)

```python
# app/database/engine.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

engine = create_async_engine(
    Config.DATABASE_URL,
    pool_size=20,  # Max connections
    max_overflow=10,  # Extra connections
    pool_pre_ping=True,  # Verify connections
    echo=False,
)

AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)
```

---

## 🚀 Deployment

### Production checklist

```bash
# Environment
export ENVIRONMENT=production
export DEV_MODE=false
export LOG_LEVEL=INFO

# Database
export DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/repairbot

# Redis
export REDIS_URL=redis://redis:6379/0

# Monitoring
export SENTRY_DSN=https://xxx@sentry.io/xxx

# Start
docker-compose -f docker-compose.prod.yml up -d
```

**docker-compose.prod.yml:**
```yaml
version: '3.8'

services:
  bot:
    image: ghcr.io/your-org/telegram-repair-bot:latest
    restart: always
    env_file:
      - .env.production
    depends_on:
      - postgres
      - redis
    healthcheck:
      test: ["CMD", "python", "-c", "import asyncio; asyncio.run(...)"]
      interval: 30s
      timeout: 10s
      retries: 3

  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: repairbot
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus

  grafana:
    image: grafana/grafana:latest
    environment:
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD}
    volumes:
      - grafana_data:/var/lib/grafana

volumes:
  postgres_data:
  redis_data:
  prometheus_data:
  grafana_data:
```

---

## 📝 Итоговый action plan

### Week 1-2: Critical fixes (P0)
- [ ] Docker secrets для BOT_TOKEN
- [ ] Redis FSM storage
- [ ] Rate limiting middleware
- [ ] State machine для Order
- [ ] PostgreSQL setup

### Week 3-4: High priority (P1)
- [ ] SQLAlchemy ORM migration
- [ ] Sentry integration
- [ ] Transaction isolation
- [ ] PII masking
- [ ] Idempotency keys

### Week 5-6: Quality improvements (P2)
- [ ] Test coverage 80%+
- [ ] Repository pattern
- [ ] Pagination
- [ ] CI/CD pipeline
- [ ] Prometheus metrics

---

**Документ подготовлен с использованием Context7 для анализа библиотек**
**Версия:** 1.0
**Дата:** 19 октября 2025

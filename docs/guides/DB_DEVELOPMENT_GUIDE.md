# Руководство по работе с БД: Dev(SQLite) + Prod(PostgreSQL)

## Обзор архитектуры

### Development (SQLite)
- **СУБД**: SQLite 3.x
- **Драйвер**: `aiosqlite==0.20.0`
- **Файл**: `bot_database.db`
- **Особенности**: Файловая БД, WAL режим, BEGIN IMMEDIATE

### Production (PostgreSQL)
- **СУБД**: PostgreSQL 15+
- **Драйвер**: `asyncpg==0.29.0` (планируется)
- **Строка подключения**: `postgresql+asyncpg://user:pass@host:5432/db`
- **Особенности**: Connection pooling, транзакции, индексы

## Переменные окружения

### Development (.env)
```bash
# SQLite для разработки
DATABASE_PATH=bot_database.db
DATABASE_URL=sqlite:///bot_database.db

# Логирование
LOG_LEVEL=DEBUG
DEV_MODE=true

# Telegram
BOT_TOKEN=your_dev_bot_token
ADMIN_IDS=123456789
DISPATCHER_IDS=987654321
```

### Production (.env.production)
```bash
# PostgreSQL для продакшена
DATABASE_URL=postgresql+asyncpg://repairbot:secure_password@postgres:5432/repairbot_db
DATABASE_PATH=/app/data/bot_database.db  # Fallback для совместимости

# Логирование
LOG_LEVEL=INFO
DEV_MODE=false

# Telegram
BOT_TOKEN=your_prod_bot_token
ADMIN_IDS=123456789
DISPATCHER_IDS=987654321

# Redis для FSM
REDIS_URL=redis://redis:6379/0
```

## Конфигурация Alembic

### Development (alembic.ini)
```ini
[alembic]
script_location = migrations
sqlalchemy.url = sqlite:///bot_database.db

[post_write_hooks]
hooks = black
black.type = console_scripts
black.entrypoint = black
black.options = -l 79 REVISION_SCRIPT_FILENAME
```

### Production (alembic.prod.ini)
```ini
[alembic]
script_location = migrations
sqlalchemy.url = postgresql+asyncpg://repairbot:secure_password@postgres:5432/repairbot_db

[post_write_hooks]
hooks = black
black.type = console_scripts
black.entrypoint = black
black.options = -l 79 REVISION_SCRIPT_FILENAME
```

## Docker Compose конфигурации

### Development (docker-compose.dev.yml)
```yaml
services:
  bot:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    container_name: telegram_repair_bot_dev
    env_file:
      - ../.env
    volumes:
      - bot_data:/app/data
      - ../bot_database.db:/app/bot_database.db  # SQLite файл
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    container_name: telegram_bot_redis_dev
    ports:
      - "6379:6379"

volumes:
  bot_data:
    driver: local
```

### Production (docker-compose.prod.yml)
```yaml
services:
  bot:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    container_name: telegram_repair_bot_prod
    env_file:
      - ../.env.production
    environment:
      - DATABASE_URL=postgresql+asyncpg://repairbot:${DB_PASSWORD}@postgres:5432/repairbot_db
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  postgres:
    image: postgres:15-alpine
    container_name: telegram_bot_postgres_prod
    environment:
      POSTGRES_DB: repairbot_db
      POSTGRES_USER: repairbot
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U repairbot -d repairbot_db"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: telegram_bot_redis_prod
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
    driver: local
  redis_data:
    driver: local
```

## Миграции

### Создание новой миграции
```bash
# Development
alembic revision --autogenerate -m "add_new_feature"

# Production (с указанием конфига)
alembic -c alembic.prod.ini revision --autogenerate -m "add_new_feature"
```

### Применение миграций
```bash
# Development
alembic upgrade head

# Production
alembic -c alembic.prod.ini upgrade head
```

### Откат миграций
```bash
# Development
alembic downgrade -1

# Production
alembic -c alembic.prod.ini downgrade -1
```

## Код для работы с БД

### Универсальный Database класс
```python
# app/database/db.py
import os
from contextlib import asynccontextmanager
import aiosqlite
import asyncpg  # Для PostgreSQL

class Database:
    def __init__(self, db_url: str = None):
        self.db_url = db_url or os.getenv('DATABASE_URL', 'sqlite:///bot_database.db')
        self.is_sqlite = self.db_url.startswith('sqlite')
        self.connection = None
        self.pool = None  # Для PostgreSQL

    async def connect(self):
        if self.is_sqlite:
            # SQLite
            db_path = self.db_url.replace('sqlite:///', '')
            self.connection = await aiosqlite.connect(db_path)
            self.connection.row_factory = aiosqlite.Row
            await self.connection.execute("PRAGMA journal_mode=WAL")
        else:
            # PostgreSQL
            self.pool = await asyncpg.create_pool(
                self.db_url,
                min_size=5,
                max_size=20,
                command_timeout=60
            )

    async def disconnect(self):
        if self.is_sqlite and self.connection:
            await self.connection.close()
        elif self.pool:
            await self.pool.close()

    @asynccontextmanager
    async def transaction(self):
        if self.is_sqlite:
            # SQLite транзакции
            await self.connection.execute("BEGIN IMMEDIATE")
            try:
                yield self.connection
                await self.connection.commit()
            except Exception as e:
                await self.connection.rollback()
                raise
        else:
            # PostgreSQL транзакции
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    yield conn

    async def execute(self, query: str, params: tuple = None):
        if self.is_sqlite:
            return await self.connection.execute(query, params or ())
        else:
            async with self.pool.acquire() as conn:
                return await conn.fetch(query, *params or ())
```

### Адаптация запросов
```python
# app/database/adapters.py
class QueryAdapter:
    @staticmethod
    def adapt_for_db(query: str, is_sqlite: bool) -> str:
        """Адаптирует SQL запросы для разных СУБД"""
        if is_sqlite:
            # SQLite специфичные изменения
            query = query.replace('$1', '?')  # PostgreSQL -> SQLite параметры
            query = query.replace('RETURNING *', '')  # SQLite не поддерживает RETURNING
        else:
            # PostgreSQL специфичные изменения
            query = query.replace('?', '$1')  # SQLite -> PostgreSQL параметры
            query = query.replace('AUTOINCREMENT', 'SERIAL')

        return query

    @staticmethod
    def get_parameter_style(is_sqlite: bool) -> str:
        return '?' if is_sqlite else '$1'
```

## Тестирование

### Unit тесты
```python
# tests/test_database.py
import pytest
import tempfile
import os
from app.database.db import Database

@pytest.fixture
async def sqlite_db():
    """Фикстура для SQLite тестов"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    db = Database(f'sqlite:///{db_path}')
    await db.connect()
    await db.init_db()

    yield db

    await db.disconnect()
    os.unlink(db_path)

@pytest.fixture
async def postgres_db():
    """Фикстура для PostgreSQL тестов"""
    db = Database('postgresql+asyncpg://test:test@localhost:5432/test_db')
    await db.connect()

    yield db

    await db.disconnect()

@pytest.mark.asyncio
async def test_create_order_sqlite(sqlite_db):
    """Тест создания заказа в SQLite"""
    order = await sqlite_db.create_order(
        equipment_type="Холодильник",
        description="Не работает",
        client_name="Иван",
        client_address="Москва",
        client_phone="+7900123456",
        dispatcher_id=123456789
    )
    assert order.id is not None
    assert order.status == "NEW"

@pytest.mark.asyncio
async def test_create_order_postgres(postgres_db):
    """Тест создания заказа в PostgreSQL"""
    order = await postgres_db.create_order(
        equipment_type="Холодильник",
        description="Не работает",
        client_name="Иван",
        client_address="Москва",
        client_phone="+7900123456",
        dispatcher_id=123456789
    )
    assert order.id is not None
    assert order.status == "NEW"
```

## Мониторинг и логирование

### Логирование запросов
```python
# app/database/logger.py
import logging
import time
from functools import wraps

logger = logging.getLogger('database.queries')

def log_queries(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time

            if execution_time > 0.1:  # Логируем медленные запросы
                logger.warning(
                    f"Slow query: {func.__name__} took {execution_time:.3f}s"
                )

            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                f"Query failed: {func.__name__} after {execution_time:.3f}s: {e}"
            )
            raise

    return wrapper
```

### Метрики производительности
```python
# app/database/metrics.py
from prometheus_client import Counter, Histogram, Gauge

# Метрики для мониторинга
query_counter = Counter('db_queries_total', 'Total database queries', ['operation', 'status'])
query_duration = Histogram('db_query_duration_seconds', 'Query duration', ['operation'])
active_connections = Gauge('db_active_connections', 'Active database connections')

class DatabaseMetrics:
    @staticmethod
    def record_query(operation: str, duration: float, success: bool):
        query_counter.labels(operation=operation, status='success' if success else 'error').inc()
        query_duration.labels(operation=operation).observe(duration)
```

## Backup и восстановление

### SQLite backup
```bash
# Создание backup
cp bot_database.db backups/bot_database_$(date +%Y%m%d_%H%M%S).db

# Восстановление
cp backups/bot_database_20250117_120000.db bot_database.db
```

### PostgreSQL backup
```bash
# Создание backup
pg_dump -h localhost -U repairbot -d repairbot_db > backups/repairbot_$(date +%Y%m%d_%H%M%S).sql

# Восстановление
psql -h localhost -U repairbot -d repairbot_db < backups/repairbot_20250117_120000.sql
```

## Troubleshooting

### Частые проблемы

1. **SQLite locked database**
   ```bash
   # Проверка процессов
   lsof bot_database.db
   # Перезапуск с WAL режимом
   sqlite3 bot_database.db "PRAGMA journal_mode=WAL;"
   ```

2. **PostgreSQL connection refused**
   ```bash
   # Проверка статуса
   docker-compose -f docker-compose.prod.yml ps postgres
   # Проверка логов
   docker-compose -f docker-compose.prod.yml logs postgres
   ```

3. **Миграции не применяются**
   ```bash
   # Проверка текущей версии
   alembic current
   # Принудительное обновление
   alembic upgrade head --sql
   ```

## Заключение

Данное руководство обеспечивает плавный переход между SQLite (development) и PostgreSQL (production) с минимальными изменениями в коде. Ключевые принципы:

- Универсальный Database класс
- Адаптация SQL запросов
- Единые миграции через Alembic
- Comprehensive тестирование
- Мониторинг и логирование

Следуя этому руководству, команда может эффективно разрабатывать на SQLite и деплоить на PostgreSQL без проблем совместимости.

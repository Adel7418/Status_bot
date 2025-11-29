# Инструкция по применению миграции для таблицы order_reports на сервере

## Проблема

На сервере в Docker контейнерах отсутствует таблица `order_reports` для баз данных `city1` и `city2`, что приводит к ошибке:
```
sqlite3.OperationalError: no such table: order_reports
```

## Решение

### Вариант 1: Применение миграций Alembic через Docker (Рекомендуется)

#### Для city1:
```bash
docker-compose -f docker/docker-compose.multibot.yml run --rm bot_city1 alembic upgrade head
```

#### Для city2:
```bash
docker-compose -f docker/docker-compose.multibot.yml run --rm bot_city2 alembic upgrade head
```

### Вариант 2: Ручное создание таблицы через Docker (если миграции не работают)

#### Для city1:
```bash
docker-compose -f docker/docker-compose.multibot.yml exec bot_city1 python scripts/create_order_reports_city1.py
```

#### Для city2:
```bash
docker-compose -f docker/docker-compose.multibot.yml exec bot_city2 python scripts/create_order_reports_city2.py
```

### Вариант 3: Прямой SQL через Docker (если Python скрипты недоступны)

#### Для city1:
```bash
docker-compose -f docker/docker-compose.multibot.yml exec bot_city1 sqlite3 /app/data/bot_database.db "
CREATE TABLE IF NOT EXISTS order_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    equipment_type VARCHAR(255) NOT NULL,
    client_name VARCHAR(255) NOT NULL,
    client_address VARCHAR(500),
    master_id INTEGER,
    master_name VARCHAR(255),
    dispatcher_id INTEGER,
    dispatcher_name VARCHAR(255),
    total_amount REAL DEFAULT 0.0,
    materials_cost REAL DEFAULT 0.0,
    master_profit REAL DEFAULT 0.0,
    company_profit REAL DEFAULT 0.0,
    out_of_city INTEGER DEFAULT 0,
    has_review INTEGER DEFAULT 0,
    created_at DATETIME,
    closed_at DATETIME,
    completion_time_hours REAL
);"
```

#### Для city2:
```bash
docker-compose -f docker/docker-compose.multibot.yml exec bot_city2 sqlite3 /app/data/bot_database.db "
CREATE TABLE IF NOT EXISTS order_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    equipment_type VARCHAR(255) NOT NULL,
    client_name VARCHAR(255) NOT NULL,
    client_address VARCHAR(500),
    master_id INTEGER,
    master_name VARCHAR(255),
    dispatcher_id INTEGER,
    dispatcher_name VARCHAR(255),
    total_amount REAL DEFAULT 0.0,
    materials_cost REAL DEFAULT 0.0,
    master_profit REAL DEFAULT 0.0,
    company_profit REAL DEFAULT 0.0,
    out_of_city INTEGER DEFAULT 0,
    has_review INTEGER DEFAULT 0,
    created_at DATETIME,
    closed_at DATETIME,
    completion_time_hours REAL
);"
```

## Проверка

После применения миграции можно проверить наличие таблицы:

### Для city1:
```bash
docker-compose -f docker/docker-compose.multibot.yml exec bot_city1 sqlite3 /app/data/bot_database.db "SELECT name FROM sqlite_master WHERE type='table' AND name='order_reports';"
```

### Для city2:
```bash
docker-compose -f docker/docker-compose.multibot.yml exec bot_city2 sqlite3 /app/data/bot_database.db "SELECT name FROM sqlite_master WHERE type='table' AND name='order_reports';"
```

Если таблица существует, команда вернет строку с `order_reports`.

## После применения миграции

После успешного применения миграции рекомендуется перезапустить контейнеры:

```bash
docker-compose -f docker/docker-compose.multibot.yml restart bot_city1 bot_city2
```

Или если нужно пересобрать:
```bash
docker-compose -f docker/docker-compose.multibot.yml up -d --build bot_city1 bot_city2
```

## Примечания

1. Миграция `77f5626ac688_add_order_reports_table.py` уже содержит проверку существования таблицы, поэтому её можно безопасно запускать несколько раз.
2. Скрипты `scripts/create_order_reports_city1.py` и `scripts/create_order_reports_city2.py` также проверяют наличие таблицы перед созданием.
3. Если миграции Alembic не применяются автоматически, используйте Вариант 2 или Вариант 3.

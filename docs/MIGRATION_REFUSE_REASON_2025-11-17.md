# Миграция: Добавление поля refuse_reason

**Дата:** 17 ноября 2025  
**Файл миграции:** `migrations/versions/add_refuse_reason_to_orders.py`  
**Revision ID:** `a1b2c3d4e5f6`

## Описание

Добавляет колонку `refuse_reason` в таблицу `orders` для хранения причин отказа от заявок.

## Изменения в базе данных

### Таблица: `orders`

**Добавляется колонка:**
- `refuse_reason` VARCHAR(500) NULL - Причина отказа/отмены заявки

## Применение миграции

### Вариант 1: Через Alembic (рекомендуется)

```bash
# Проверка текущей версии БД
alembic current

# Применение миграции
alembic upgrade head

# Или применение конкретной ревизии
alembic upgrade a1b2c3d4e5f6
```

### Вариант 2: Прямой SQL (для production)

Если Alembic не настроен, можно применить миграцию вручную:

```sql
-- Проверка существования колонки
SELECT COUNT(*) FROM pragma_table_info('orders') WHERE name='refuse_reason';

-- Если колонка не существует, добавить её
ALTER TABLE orders ADD COLUMN refuse_reason VARCHAR(500);
```

### Вариант 3: Для нескольких баз данных

Если используется multi-bot setup (city1, city2):

```bash
# City 1
cd /path/to/bot
export DATABASE_PATH=data/city1/bot_database.db
alembic upgrade head

# City 2
export DATABASE_PATH=data/city2/bot_database.db
alembic upgrade head
```

## Проверка применения миграции

### SQL проверка:

```sql
-- Проверить наличие колонки
PRAGMA table_info(orders);

-- Должна быть строка с name='refuse_reason', type='VARCHAR(500)', notnull=0
```

### Python проверка:

```python
from sqlalchemy import inspect, create_engine

engine = create_engine('sqlite:///data/bot_database.db')
inspector = inspect(engine)

columns = [c['name'] for c in inspector.get_columns('orders')]
print('refuse_reason' in columns)  # Должно вывести True
```

## Откат миграции (при необходимости)

```bash
# Откат на предыдущую версию
alembic downgrade -1

# Откат на конкретную ревизию
alembic downgrade 77f5626ac688
```

**⚠️ ВНИМАНИЕ:** Откат удалит колонку `refuse_reason` и все данные в ней будут потеряны!

## Безопасность

### Бэкап перед миграцией:

```bash
# Создать бэкап базы данных
cp data/bot_database.db data/bot_database_backup_$(date +%Y%m%d_%H%M%S).db

# Или через скрипт
python scripts/backup_db.py
```

### Проверка целостности после миграции:

```bash
# Проверить статистику
sqlite3 data/bot_database.db "SELECT COUNT(*) FROM orders;"

# Проверить отказы с причинами
sqlite3 data/bot_database.db "SELECT COUNT(*) FROM orders WHERE refuse_reason IS NOT NULL;"
```

## Совместимость

- ✅ **Обратно совместима**: Старый код будет работать (колонка nullable)
- ✅ **Без downtime**: Можно применить на работающей системе
- ✅ **Идемпотентна**: Можно запустить несколько раз безопасно

## Зависимости

- **Parent revision:** `77f5626ac688` (add_order_reports_table)
- **SQLAlchemy:** >= 2.0
- **Alembic:** >= 1.7

## Применение в Docker

```bash
# Через docker-compose
docker-compose -f docker/docker-compose.migrate.yml up

# Или напрямую в контейнере
docker exec -it telegram_repair_bot_city1 alembic upgrade head
docker exec -it telegram_repair_bot_city2 alembic upgrade head
```

## Troubleshooting

### Ошибка: "Table doesn't exist"

```bash
# Создать базовую схему
alembic upgrade base
alembic upgrade head
```

### Ошибка: "Column already exists"

Это нормально - миграция проверяет существование колонки и пропускает её создание.

### Ошибка: "Can't locate revision"

```bash
# Проверить список ревизий
alembic history

# Убедиться что файл миграции существует
ls -la migrations/versions/add_refuse_reason_to_orders.py
```

## После применения

1. ✅ Проверить что колонка создана
2. ✅ Проверить что бот запускается без ошибок
3. ✅ Протестировать функционал отказа с причиной
4. ✅ Проверить статистику в админ-панели
5. ✅ Проверить Excel-экспорт с причинами отказов

## Связанные файлы

- `app/database/orm_models.py` - ORM модель с полем refuse_reason
- `app/database/models.py` - Dataclass модель с полем refuse_reason
- `docs/REFUSE_REASON_FEATURE_2025-11-17.md` - Документация по функционалу

## История изменений

- **2025-11-17** - Создана миграция для добавления refuse_reason

## Автор

Claude (AI Assistant)  
Дата: 17 ноября 2025


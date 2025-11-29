# ✅ Исправление миграций для SQLite

## Проблема

Миграции **007** и **009** были созданы для PostgreSQL и содержали несовместимые с SQLite операции:
- **007**: CHECK constraints (не поддерживаются через ALTER TABLE в SQLite)
- **009**: ENUM типы, партиционирование, материализованные представления (только PostgreSQL)

## Решение

### 1. Удалены несовместимые миграции
- ❌ `007_add_constraints_and_validation.py` - удалена
- ❌ `009_postgresql_optimization.py` - удалена

### 2. Исправлена цепочка миграций

**До:**
```
005 → 006 → 007 → 008 → 009 → 010
```

**После:**
```
005 → 006 → 008 → 010
```

### 3. Обновлена миграция 008

Удалены PostgreSQL-специфичные операции:
- Partial indexes с `postgresql_where` (не поддерживаются в SQLite)

**Изменения:**
- `down_revision`: `007_add_constraints_and_validation` → `006_add_performance_indexes`
- Удалены индексы: `idx_users_active`, `idx_masters_active`, `idx_orders_active`

### 4. Обновлена миграция 010

**Изменения:**
- `down_revision`: `009_postgresql_optimization` → `008_add_soft_delete`

## Актуальная структура миграций

| Миграция | Описание | SQLite | PostgreSQL |
|----------|----------|--------|------------|
| 001 | Initial schema | ✅ | ✅ |
| 002 | Financial reports | ✅ | ✅ |
| 003 | DR fields | ✅ | ✅ |
| 004 | Order reports | ✅ | ✅ |
| 005 | Reschedule fields | ✅ | ✅ |
| 006 | Performance indexes | ✅ | ✅ |
| 008 | Soft delete & versioning | ✅ | ✅ |
| 010 | Master reports archive | ✅ | ✅ |

## Применение на сервере

### Вариант 1: Через Docker (рекомендуется)

```bash
# На продакшн сервере
cd ~/telegram_repair_bot

# Сначала обновите код из Git
git pull origin main

# Примените миграции через Docker
docker compose -f docker/docker-compose.prod.yml run --rm bot python3 scripts/apply_sqlite_migrations.py

# Проверьте версию
docker compose -f docker/docker-compose.prod.yml run --rm bot alembic current

# Запустите бота
make prod-deploy
```

### Вариант 2: Через Python скрипт (если Docker недоступен)

```bash
# На продакшн сервере
cd ~/telegram_repair_bot

# Обновите код
git pull origin main

# Активируйте виртуальное окружение
source venv/bin/activate

# Примените миграции
python scripts/apply_sqlite_migrations.py

# Проверьте версию
alembic current

# Запустите бота
python bot.py
```

### Вариант 3: Через встроенный скрипт alembic

```bash
# ВНИМАНИЕ: Этот вариант может не сработать из-за конфликтов версий
# Используйте Вариант 1 или 2

# Сначала обновите код
git pull origin main

# Попробуйте применить через alembic
docker compose -f docker/docker-compose.prod.yml run --rm bot alembic upgrade head
```

## Что делает скрипт `apply_sqlite_migrations.py`

1. ✅ Проверяет текущую версию миграции
2. ✅ Применяет миграцию 008:
   - Добавляет `deleted_at` в таблицы `users`, `masters`, `orders`, `audit_log`
   - Добавляет `version` в таблицы `users`, `masters`, `orders`
   - Создает индексы для `deleted_at`
   - Создает таблицу `entity_history` для истории изменений
3. ✅ Применяет миграцию 010:
   - Создает таблицу `master_reports_archive` для архивных отчетов
   - Создает индексы для быстрого поиска
4. ✅ Устанавливает версию на `010_create_master_reports_archive`
5. ✅ Показывает статистику таблиц

## Проверка успешного применения

```bash
# Через Docker
docker compose -f docker/docker-compose.prod.yml run --rm bot alembic current

# Должно вывести:
# INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
# INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
# 010_create_master_reports_archive (head)

# Проверьте структуру БД
docker compose -f docker/docker-compose.prod.yml run --rm bot python3 << 'EOF'
import sqlite3
conn = sqlite3.connect('/app/data/bot_database.db')
cursor = conn.cursor()

# Проверьте таблицы
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
print("Таблицы:")
for table in cursor.fetchall():
    print(f"  - {table[0]}")

# Проверьте версию
cursor.execute("SELECT version_num FROM alembic_version;")
print(f"\nВерсия миграции: {cursor.fetchone()[0]}")

conn.close()
EOF
```

## Откат (если что-то пошло не так)

### Откат миграций через alembic

```bash
# Откат на одну версию назад
docker compose -f docker/docker-compose.prod.yml run --rm bot alembic downgrade -1

# Откат на конкретную версию
docker compose -f docker/docker-compose.prod.yml run --rm bot alembic downgrade 006_add_performance_indexes
```

### Восстановление из backup

```bash
# Остановите бота
make prod-stop

# Восстановите БД из backup
cp backups/bot_database_YYYY-MM-DD_HH-MM-SS.db data/bot_database.db

# Запустите бота
make prod-deploy
```

## Будущая миграция на PostgreSQL

Когда вы будете готовы мигрировать на PostgreSQL:

1. Установите переменную окружения:
   ```bash
   DATABASE_URL=postgresql+asyncpg://user:password@localhost/dbname
   ```

2. Создайте PostgreSQL-специфичные миграции заново:
   ```bash
   alembic revision --autogenerate -m "add_postgresql_constraints"
   alembic revision --autogenerate -m "add_postgresql_optimizations"
   ```

3. Примените миграции:
   ```bash
   alembic upgrade head
   ```

## Связанные документы

- [MIGRATIONS_GUIDE.md](MIGRATIONS_GUIDE.md) - Полное руководство по миграциям
- [ORM_MIGRATION_COMPLETE.md](ORM_MIGRATION_COMPLETE.md) - ORM миграция
- [PRODUCTION_DEPLOY.md](PRODUCTION_DEPLOY.md) - Деплой в продакшн

---

**Дата:** 2025-10-20
**Статус:** ✅ Исправлено и готово к применению

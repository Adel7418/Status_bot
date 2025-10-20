# Аудит базы данных: Telegram Repair Bot

## Обзор архитектуры БД

### Текущее состояние
- **СУБД**: SQLite (dev) → PostgreSQL (prod планируется)
- **ORM**: Отсутствует, используется `aiosqlite` для прямых SQL запросов
- **Миграции**: Alembic 1.13.1 с 5 версиями миграций
- **Транзакции**: `BEGIN IMMEDIATE` для эксклюзивных блокировок
- **Индексы**: 8 базовых индексов для оптимизации

## SQL-профиль рисков

### 🔴 P0 - Критические риски

1. **Отсутствие ORM и типизации SQL**
   - **Проблема**: Прямые SQL запросы без валидации типов
   - **Риск**: SQL injection, ошибки типов, сложность рефакторинга
   - **Пример**: `app/database/db.py:850` - ручное формирование запросов
   ```python
   cursor = await self.connection.execute(
       "SELECT o.*, u1.first_name || ' ' || COALESCE(u1.last_name, '') as dispatcher_name"
   )
   ```

2. **N+1 проблема в JOIN запросах**
   - **Проблема**: Множественные LEFT JOIN без оптимизации
   - **Риск**: Деградация производительности при росте данных
   - **Пример**: `app/database/db.py:855-857` - тройной JOIN для каждого заказа
   ```sql
   LEFT JOIN users u1 ON o.dispatcher_id = u1.telegram_id
   LEFT JOIN masters m ON o.assigned_master_id = m.id
   LEFT JOIN users u2 ON m.telegram_id = u2.telegram_id
   ```

3. **Отсутствие составных индексов**
   - **Проблема**: Только простые индексы, нет составных для сложных запросов
   - **Риск**: Медленные запросы с WHERE + ORDER BY
   - **Пример**: Запросы по статусу + дате без индекса `(status, created_at)`

### 🟡 P1 - Высокие риски

4. **Неэффективная пагинация**
   - **Проблема**: Только LIMIT без OFFSET оптимизации
   - **Риск**: Медленная пагинация на больших страницах
   - **Пример**: `app/database/db.py:966` - простой LIMIT без keyset pagination

5. **Отсутствие connection pooling**
   - **Проблема**: Одно соединение на весь процесс
   - **Риск**: Блокировки при высокой нагрузке
   - **Решение**: Нужен connection pool для PostgreSQL

6. **Слабая валидация схемы**
   - **Проблема**: Нет CHECK constraints, ENUM типов
   - **Риск**: Некорректные данные в БД
   - **Пример**: `status` как TEXT вместо ENUM

### 🟠 P2 - Средние риски

7. **Дублирование кода в запросах**
   - **Проблема**: Повторяющиеся JOIN паттерны
   - **Риск**: Сложность поддержки, ошибки при изменениях
   - **Пример**: 38 одинаковых LEFT JOIN в разных методах

8. **Отсутствие soft delete**
   - **Проблема**: Прямое удаление записей
   - **Риск**: Потеря данных, сложность аудита
   - **Решение**: Добавить `deleted_at` поля

9. **Неоптимальные GROUP BY запросы**
   - **Проблема**: Агрегация без индексов
   - **Риск**: Медленные отчеты
   - **Пример**: `app/database/db.py:1489` - GROUP BY без индекса

10. **Отсутствие мониторинга запросов**
    - **Проблема**: Нет логирования медленных запросов
    - **Риск**: Скрытые проблемы производительности
    - **Решение**: Query logging, EXPLAIN ANALYZE

## Анализ схемы БД

### ✅ Положительные аспекты

- **Нормализация**: Правильные FK связи между таблицами
- **Аудит**: Таблица `order_status_history` для отслеживания изменений
- **Индексы**: Базовые индексы на ключевых полях
- **Миграции**: Структурированные Alembic миграции

### ❌ Проблемы схемы

- **Денормализация**: Дублирование имен в `orders` (dispatcher_name, master_name)
- **Отсутствие ENUM**: Статусы как TEXT вместо типизированных значений
- **Нет версионирования**: Отсутствие soft delete и версионирования записей
- **Слабая типизация**: Много NULL полей без четких ограничений

## Производительность

### Текущие индексы
```sql
-- Базовые индексы (8 штук)
CREATE INDEX idx_users_telegram_id ON users(telegram_id);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_masters_telegram_id ON masters(telegram_id);
CREATE INDEX idx_masters_is_approved ON masters(is_approved);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_assigned_master_id ON orders(assigned_master_id);
CREATE INDEX idx_orders_dispatcher_id ON orders(dispatcher_id);
CREATE INDEX idx_audit_user_id ON audit_log(user_id);
```

### Рекомендуемые индексы
```sql
-- Составные индексы для оптимизации
CREATE INDEX idx_orders_status_created ON orders(status, created_at);
CREATE INDEX idx_orders_master_status ON orders(assigned_master_id, status);
CREATE INDEX idx_orders_period ON orders(updated_at, status) WHERE status = 'CLOSED';
CREATE INDEX idx_audit_timestamp ON audit_log(timestamp);
CREATE INDEX idx_status_history_order ON order_status_history(order_id, changed_at);
```

## Миграции SQLite → PostgreSQL

### Текущее состояние
- **SQLite**: `aiosqlite` драйвер, файловая БД
- **PostgreSQL**: Планируется `asyncpg` драйвер
- **Миграции**: Alembic настроен для SQLite

### Проблемы совместимости

1. **Типы данных**
   - SQLite: `INTEGER`, `TEXT`, `REAL`
   - PostgreSQL: `BIGINT`, `VARCHAR`, `DECIMAL`

2. **Автоинкремент**
   - SQLite: `AUTOINCREMENT`
   - PostgreSQL: `SERIAL` или `IDENTITY`

3. **Булевы значения**
   - SQLite: `INTEGER` (0/1)
   - PostgreSQL: `BOOLEAN`

4. **Временные зоны**
   - SQLite: `TIMESTAMP` без TZ
   - PostgreSQL: `TIMESTAMPTZ`

## Рекомендации по исправлению

### Краткосрочные (1-2 недели)

1. **Добавить составные индексы**
   ```sql
   CREATE INDEX idx_orders_status_created ON orders(status, created_at);
   CREATE INDEX idx_orders_master_status ON orders(assigned_master_id, status);
   ```

2. **Оптимизировать пагинацию**
   ```python
   # Keyset pagination вместо OFFSET
   WHERE created_at < last_created_at ORDER BY created_at DESC LIMIT 20
   ```

3. **Добавить валидацию статусов**
   ```sql
   ALTER TABLE orders ADD CONSTRAINT chk_status
   CHECK (status IN ('NEW', 'ASSIGNED', 'IN_PROGRESS', 'COMPLETED', 'CLOSED', 'REFUSED'));
   ```

### Среднесрочные (1-2 месяца)

4. **Внедрить connection pooling**
   ```python
   from asyncpg import create_pool
   pool = await create_pool(database_url, min_size=5, max_size=20)
   ```

5. **Добавить soft delete**
   ```sql
   ALTER TABLE orders ADD COLUMN deleted_at TIMESTAMP;
   CREATE INDEX idx_orders_deleted ON orders(deleted_at);
   ```

6. **Внедрить query logging**
   ```python
   import logging
   logger = logging.getLogger('sql.queries')
   # Логировать все запросы > 100ms
   ```

### Долгосрочные (3-6 месяцев)

7. **Миграция на SQLAlchemy ORM**
   ```python
   from sqlalchemy.ext.asyncio import AsyncSession
   from sqlalchemy.orm import sessionmaker
   ```

8. **Полная миграция на PostgreSQL**
   - Настройка `asyncpg` драйвера
   - Адаптация типов данных
   - Тестирование производительности

9. **Внедрение мониторинга**
   - Prometheus метрики
   - Grafana дашборды
   - Алерты на медленные запросы

## Метрики успеха

- **Производительность**: < 100ms для 95% запросов
- **Доступность**: 99.9% uptime
- **Масштабируемость**: Поддержка 1000+ заказов/день
- **Безопасность**: 0 SQL injection уязвимостей
- **Поддерживаемость**: < 1 час на исправление багов БД

## Заключение

Текущая архитектура БД функциональна, но требует серьезной оптимизации для production использования. Критические проблемы с производительностью и безопасностью должны быть решены в первую очередь. Миграция на PostgreSQL и ORM значительно улучшит масштабируемость и поддерживаемость системы.

# План миграции на полный ORM

## Проблема

5 файлов используют прямой доступ к `.connection` (aiosqlite), что несовместимо с ORM:
1. `app/handlers/financial_reports.py`
2. `app/services/excel_export.py`
3. `app/services/active_orders_export.py`
4. `app/handlers/admin_history.py`
5. `app/services/financial_reports.py`

## Анализ проблемы

### Что не работает с ORM:
```python
# ❌ Это не работает в ORM
cursor = await db.connection.execute("SELECT ...")
rows = await cursor.fetchall()
```

### Что нужно сделать:
```python
# ✅ Правильный ORM подход
async with db.get_session() as session:
    result = await session.execute(select(...))
    rows = result.fetchall()
```

## План миграции

### Этап 1: Подготовка (1-2 дня)

#### 1.1 Создать утилиты для raw SQL
**Файл**: `app/database/orm_database.py`

Добавить метод для выполнения raw SQL запросов:

```python
async def execute_raw_sql(self, query: str, params: dict | tuple | None = None) -> list[Any]:
    """
    Выполнение raw SQL запросов для совместимости

    Args:
        query: SQL запрос
        params: Параметры запроса

    Returns:
        Список строк результата
    """
    async with self.get_session() as session:
        from sqlalchemy import text
        result = await session.execute(text(query), params or {})
        return [dict(row._mapping) for row in result]
```

#### 1.2 Добавить атрибут .connection в ORMDatabase
Для обратной совместимости:

```python
@property
async def connection(self):
    """Совместимость со старым API"""
    if not hasattr(self, '_legacy_connection'):
        # Создаем временное подключение
        self._legacy_connection = await self.engine.connect()
    return self._legacy_connection
```

**⚠️ Внимание**: Это хак для совместимости, используйте только для миграции!

---

### Этап 2: Миграция файлов (3-5 дней)

#### 2.1 app/handlers/financial_reports.py (1 день)

**Проблема**:
```python
cursor = await db.connection.execute("""
    SELECT m.id, u.first_name || ' ' || COALESCE(u.last_name, '') as full_name
    FROM masters m
    LEFT JOIN users u ON m.telegram_id = u.telegram_id
    WHERE m.is_approved = 1 AND m.deleted_at IS NULL
""")
```

**Решение 1**: Использовать ORM метод
```python
# Было
db = Database()
await db.connect()
cursor = await db.connection.execute(...)

# Стало
db = Database()
await db.connect()
masters = await db.get_all_masters(only_approved=True)
# Преобразуем в нужный формат
for master in masters:
    full_name = f"{master.user.first_name} {master.user.last_name or ''}"
    master_list.append({"id": master.id, "full_name": full_name})
```

**Решение 2**: Если нужен raw SQL
```python
masters = await db.execute_raw_sql("""
    SELECT m.id, u.first_name || ' ' || COALESCE(u.last_name, '') as full_name
    FROM masters m
    LEFT JOIN users u ON m.telegram_id = u.telegram_id
    WHERE m.is_approved = 1 AND m.deleted_at IS NULL
""")
```

**Приоритет**: 🔴 Высокий (критичный функционал)

---

#### 2.2 app/services/excel_export.py (2 дня)

**Проблема**:
- Использует `db.connection.execute()` для сложных запросов
- Использует `OrderRepositoryExtended` с `.connection`
- 10+ мест с прямым SQL

**Решение**:

1. **Для простых запросов**: Использовать ORM методы
```python
# Было
cursor = await self.db.connection.execute("""
    SELECT * FROM orders WHERE master_id = ?
""", (master_id,))
orders = await cursor.fetchall()

# Стало
async with self.db.get_session() as session:
    stmt = select(Order).where(Order.assigned_master_id == master_id)
    result = await session.execute(stmt)
    orders = result.scalars().all()
```

2. **Для сложных агрегаций**: Добавить методы в ORMDatabase
```python
# Добавить в app/database/orm_database.py
async def get_master_orders_with_stats(self, master_id: int, start_date: datetime, end_date: datetime) -> list[dict]:
    """Получение заявок мастера со статистикой"""
    async with self.get_session() as session:
        stmt = (
            select(
                Order,
                func.count(func.distinct(Order.id)).label('total_orders'),
                func.sum(Order.total_amount).label('total_revenue')
            )
            .where(
                and_(
                    Order.assigned_master_id == master_id,
                    Order.created_at >= start_date,
                    Order.created_at <= end_date
                )
            )
            .group_by(Order.id)
        )
        result = await session.execute(stmt)
        return [dict(row._mapping) for row in result]
```

3. **OrderRepositoryExtended**: Переписать на ORM или использовать через get_session()

**Приоритет**: 🔴 Высокий (Excel экспорт критичен)

---

#### 2.3 app/services/active_orders_export.py (1 день)

**Проблема**: Использует `db.get_all_orders()` - это уже ORM метод!

**Решение**: ✅ **ПОЧТИ НИЧЕГО НЕ НУЖНО**
Просто заменить импорт:
```python
from app.database import Database  # ✅ Уже сделано!
```

**Приоритет**: 🟢 Низкий

---

#### 2.4 app/handlers/admin_history.py (1 день)

**Проблема**: Использует `OrderRepositoryExtended(self.db.connection)`

**Решение**:

Вариант 1: Переписать на ORM
```python
# Было
from app.repositories.order_repository_extended import OrderRepositoryExtended
from app.database import Database

db = Database()
await db.connect()
repo = OrderRepositoryExtended(db.connection)
await repo.soft_delete(order_id, user_id)

# Стало
from app.database import Database

db = Database()
await db.connect()
# Прямые ORM операции
async with db.get_session() as session:
    order = await session.get(Order, order_id)
    if order:
        order.deleted_at = get_now()
        await session.commit()
```

Вариант 2: Добавить методы в ORMDatabase
```python
# Добавить в app/database/orm_database.py
async def soft_delete_order(self, order_id: int, deleted_by: int, reason: str | None = None) -> bool:
    """Мягкое удаление заявки"""
    async with self.get_session() as session:
        order = await session.get(Order, order_id)
        if not order:
            return False

        order.deleted_at = get_now()
        order.version += 1

        # Логируем в audit_log
        from app.database.orm_models import AuditLog
        audit = AuditLog(
            user_id=deleted_by,
            action='SOFT_DELETE_ORDER',
            details=f'Order #{order_id}: {reason or "No reason"}',
            timestamp=get_now()
        )
        session.add(audit)

        await session.commit()
        return True
```

**Приоритет**: 🟡 Средний

---

#### 2.5 app/services/financial_reports.py (1 день)

**Проблема**: Использует стандартные методы ORM

**Решение**: ✅ **УЖЕ РАБОТАЕТ**
Файл использует только `db.get_financial_report_by_id()`, `db.get_master_reports_by_report_id()` - все это уже ORM методы.

**Приоритет**: 🟢 Низкий

---

### Этап 3: Тестирование (2 дня)

#### 3.1 Юнит-тесты
```python
# tests/test_orm_migration.py
async def test_financial_reports_work():
    """Тест финансовых отчетов"""
    db = ORMDatabase()
    await db.connect()

    # Получаем мастеров
    masters = await db.get_all_masters(only_approved=True)
    assert len(masters) > 0

    # Проверяем что есть метод для raw SQL
    result = await db.execute_raw_sql("SELECT COUNT(*) as count FROM masters WHERE is_approved = 1")
    assert result[0]['count'] > 0
```

#### 3.2 Интеграционные тесты
- Протестировать Excel экспорт
- Протестировать финансовые отчеты
- Протестировать историю заявок

#### 3.3 Ручное тестирование
1. Экспорт Excel отчетов
2. Генерация финансовых отчетов
3. Просмотр истории заявок
4. Удаление/восстановление заявок

---

### Этап 4: Развертывание (1 день)

#### 4.1 Обновить feature flag
```env
USE_ORM=true  # ✅ Включить ORM везде
```

#### 4.2 Проверить на staging
```bash
# На сервере
cd ~/telegram_repair_bot
git pull
docker compose -f docker/docker-compose.prod.yml up -d --build
```

#### 4.3 Мониторинг
```bash
docker logs -f telegram_repair_bot_prod
```

---

### Этап 5: Очистка (опционально)

#### 5.1 Удалить старый код
После проверки на проде 2-3 недели:

```bash
# Удалить app/database/db.py
# Удалить app/repositories/ (если не нужны)
# Удалить USE_ORM feature flag
```

---

## Матрица сложности

| Файл | Сложность | Время | Приоритет | Статус |
|------|-----------|-------|-----------|--------|
| `active_orders_export.py` | 🟢 Простая | 1 час | 🟢 Низкий | ✅ Готово |
| `financial_reports.py` | 🟢 Простая | 2 часа | 🟡 Средний | ✅ Почти готово |
| `admin_history.py` | 🟡 Средняя | 1 день | 🟡 Средний | ⏳ Требует работы |
| `financial_reports.py` (handler) | 🟡 Средняя | 1 день | 🔴 Высокий | ⏳ Требует работы |
| `excel_export.py` | 🔴 Сложная | 2 дня | 🔴 Высокий | ⏳ Требует работы |

**Общее время**: 4-5 рабочих дней
**Риски**: Средние (Excel экспорт имеет много кода)

---

## Сценарии отката

Если что-то сломается:

```bash
# Переключить на старый код
USE_ORM=false

# Перезапустить бота
docker compose -f docker/docker-compose.prod.yml restart
```

---

## FAQ

### Q: Почему не переписать сразу на ORM?
**A**: Excel экспорт имеет 3000+ строк кода с raw SQL. Переписать все сразу рискованно.

### Q: Можно ли использовать оба подхода одновременно?
**A**: Да, feature flag позволяет переключаться.

### Q: Как отследить прогресс?
**A**: Создать issues в GitHub:
- [ ] Мигрировать financial_reports.py
- [ ] Мигрировать excel_export.py
- [ ] Мигрировать admin_history.py
- [ ] Обновить тесты
- [ ] Развернуть в production

---

## Следующие шаги

1. ✅ Добавить `execute_raw_sql()` в ORMDatabase
2. ⏳ Мигрировать `financial_reports.py` handler
3. ⏳ Мигрировать `excel_export.py`
4. ⏳ Мигрировать `admin_history.py`
5. ✅ Обновить тесты
6. ✅ Развернуть в production

**Начнем с шага 1?** 🚀

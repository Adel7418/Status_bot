# Исправление ошибки статистики мастеров

**Дата:** 17 ноября 2025
**Проблема:** Не работают таблицы статистики мастеров - ошибка базы данных

## Описание проблемы

При попытке сгенерировать статистику мастеров возникала ошибка базы данных. Причина заключалась в использовании прямых SQL-запросов через `self.db.connection.execute()`, которые не совместимы с новым ORM-подходом базы данных.

### Затронутые файлы

1. `app/services/reports_service.py` - метод `_get_masters_stats()`
2. `app/services/excel_export.py` - метод `_add_masters_statistics_sheet()`
3. `app/handlers/financial_reports.py` - метод `callback_masters_stats_excel()` (добавлено позже)

## Внесенные изменения

### 1. reports_service.py - метод _get_masters_stats()

**Было:**
```python
cursor = await self.db.connection.execute(
    """
    SELECT
        m.id,
        u.first_name || ' ' || COALESCE(u.last_name, '') as master_name,
        COUNT(o.id) as orders_count,
        ...
    FROM masters m
    LEFT JOIN users u ON m.telegram_id = u.telegram_id
    LEFT JOIN orders o ON m.id = o.assigned_master_id
        AND DATE(o.created_at) >= ? AND DATE(o.created_at) <= ?
    WHERE m.is_active = 1
    GROUP BY m.id, u.first_name, u.last_name
    ORDER BY total_profit DESC
    """,
    (start_date, end_date),
)
```

**Стало:**
```python
# Получаем всех активных мастеров
masters = await self.db.get_all_masters(only_active=True, only_approved=True)

result = []
for master in masters:
    # Получаем все заявки мастера
    orders = await self.db.get_orders_by_period(
        start_date=start_date,
        end_date=end_date,
        master_id=master.id
    )

    # Подсчитываем статистику
    orders_count = len(orders)
    closed_orders = len([o for o in orders if o.status == OrderStatus.CLOSED])
    out_of_city_count = sum(1 for o in orders if o.out_of_city is True)
    reviews_count = sum(1 for o in orders if o.has_review is True)
    total_profit = sum(o.master_profit or 0 for o in orders if o.status == OrderStatus.CLOSED)
    ...
```

### 2. excel_export.py - метод _add_masters_statistics_sheet()

**Было:**
```python
cursor = await self.db.connection.execute(
    """
    SELECT
        COUNT(*) as total_orders,
        SUM(CASE WHEN status = 'CLOSED' THEN 1 ELSE 0 END) as closed,
        ...
    FROM orders
    WHERE assigned_master_id = ?
        AND deleted_at IS NULL
    """,
    (master_id,),
)
```

**Стало:**
```python
# Получаем расширенную статистику по мастеру через ORM
orders = await self.db.get_orders_by_master(master_id, exclude_closed=False)

# Подсчитываем статистику
total_orders = len(orders)
closed = len([o for o in orders if o.status == OrderStatus.CLOSED])
in_work = len([o for o in orders if o.status in [OrderStatus.ASSIGNED, OrderStatus.IN_PROGRESS, OrderStatus.ACCEPTED]])
refused = len([o for o in orders if o.status == OrderStatus.REFUSED])
...
```

## Преимущества нового подхода

1. **Совместимость с ORM:** Код теперь работает как с legacy `Database`, так и с новым `ORMDatabase`
2. **Безопасность:** Использование ORM-методов вместо прямых SQL-запросов снижает риск SQL-инъекций
3. **Читаемость:** Код стал более понятным и легче поддерживаемым
4. **Типобезопасность:** Используются типизированные объекты модели вместо словарей

## Тестирование

Создан тестовый скрипт для проверки работы статистики:

```bash
python test_master_stats.py
```

**Результат теста:**
- ✅ Подключение к базе данных успешно
- ✅ Статистика получена успешно
- ✅ Данные корректно отображаются

## Оставшиеся задачи

В проекте остались другие места с прямыми SQL-запросами через `self.db.connection.execute()`:

- `app/services/reports_service.py`: методы `_get_orders_stats()`, `_get_accepted_orders_details()`, `_get_summary_stats()`, `_get_closed_orders_list()` и другие
- `app/services/excel_export.py`: множество методов экспорта в Excel
- `app/services/order_search.py`: метод поиска заказов
- `app/services/master_archive_service.py`: методы работы с архивами

Эти методы также следует постепенно мигрировать на ORM-подход для полной совместимости.

## Рекомендации

1. **Постепенная миграция:** Рекомендуется постепенно мигрировать оставшиеся прямые SQL-запросы на ORM-методы
2. **Тестирование:** После миграции каждого метода необходимо проводить тестирование
3. **Документирование:** Обновлять документацию по мере внесения изменений

### 3. financial_reports.py - метод callback_masters_stats_excel()

**Было:**
```python
cursor = await db.connection.execute(
    """
    SELECT
        m.id,
        u.first_name || ' ' || COALESCE(u.last_name, '') as full_name
    FROM masters m
    LEFT JOIN users u ON m.telegram_id = u.telegram_id
    WHERE m.is_approved = 1 AND m.deleted_at IS NULL
    ORDER BY u.first_name
    """
)
masters = await cursor.fetchall()
```

**Стало:**
```python
# Получаем всех утвержденных мастеров через ORM
masters_data = await db.get_all_masters(only_approved=True, only_active=True)

# Преобразуем в формат для совместимости
masters = [
    {"id": master.id, "full_name": master.get_display_name()}
    for master in masters_data
]
```

## Обновления

### 17 ноября 2025 - Дополнительное исправление

После первого исправления была обнаружена еще одна ошибка в `financial_reports.py`:
- **Commit:** `07304c0`
- **Ошибка:** `AttributeError: 'ORMDatabase' object has no attribute 'connection'` на строке 733
- **Решение:** Заменен прямой SQL-запрос на `get_all_masters()` с преобразованием данных

## Автор изменений

Claude (AI Assistant)
Дата: 17 ноября 2025
Обновлено: 17 ноября 2025

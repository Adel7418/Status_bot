# Инструкции для применения миграции на продакшене

## Проблема
В продакшене возникает ошибка:
```
sqlite3.OperationalError: no such table: audit_log
```

## Решение
Проблема в том, что миграция пытается добавить колонку `deleted_at` в таблицу `audit_log`, которая еще не существует.

**Исправлено двумя способами:**
1. Создана новая миграция `create_audit_log_table`, которая создает таблицу `audit_log` с колонкой `deleted_at`
2. Обновлена миграция `d0a601a63b16` - теперь она сначала проверяет существование таблицы и создает её при необходимости, затем добавляет колонку `deleted_at`

Это обеспечивает совместимость как с новыми развертываниями, так и с существующими базами данных.

## Порядок миграций
Теперь миграции выполняются в правильном порядке:
1. `add_missing_columns` - создает базовые таблицы
2. `add_missing_columns_to_orders_masters` - добавляет колонки в orders и masters
3. `create_audit_log_table` - **НОВАЯ** - создает таблицу audit_log с колонкой deleted_at
4. `d0a601a63b16_add_deleted_at_to_audit_log` - **ОБНОВЛЕНА** - создает таблицу если не существует, добавляет колонку
5. `abcfdb12222b_fix_audit_log_migration` - пропускается (таблица уже создана)

## Команды для выполнения на сервере

### 1. Обновить код
```bash
git pull origin main
```

### 2. Остановить бота
```bash
docker-compose -f docker/docker-compose.prod.yml down
```

### 3. Применить миграцию
```bash
docker-compose -f docker/docker-compose.prod.yml run --rm bot alembic upgrade head
```

### 4. Запустить бота
```bash
docker-compose -f docker/docker-compose.prod.yml up -d
```

### 5. Проверить логи
```bash
docker-compose -f docker/docker-compose.prod.yml logs -f bot
```

## Альтернативный способ (если есть доступ к контейнеру)

### 1. Войти в контейнер
```bash
docker exec -it telegram_repair_bot_prod bash
```

### 2. Применить миграцию
```bash
alembic upgrade head
```

### 3. Выйти из контейнера
```bash
exit
```

### 4. Перезапустить контейнер
```bash
docker-compose -f docker/docker-compose.prod.yml restart bot
```

## Проверка результата
После применения миграции в логах должно появиться одно из сообщений:

**При создании таблицы audit_log (миграция d0a601a63b16):**
```
[INFO] Таблица audit_log не существует - создаем её
[OK] Создана таблица audit_log с колонкой deleted_at
```

**Если таблица уже существует:**
```
[INFO] Таблица audit_log существует - проверяем колонку deleted_at
[OK] Колонка deleted_at уже существует в audit_log
```

**Или при добавлении колонки:**
```
[INFO] Таблица audit_log существует - проверяем колонку deleted_at
[OK] Добавлена колонка deleted_at в audit_log
```

**При пропуске дублирующих миграций:**
```
[SKIP] Таблица audit_log уже создана с колонкой deleted_at в предыдущих миграциях
```

## Важно!
Если миграция все еще падает с ошибкой, попробуйте:

1. **Проверить версию миграции:**
```bash
docker-compose -f docker/docker-compose.prod.yml run --rm bot alembic current
```

2. **Принудительно обновить до последней версии:**
```bash
docker-compose -f docker/docker-compose.prod.yml run --rm bot alembic upgrade head
```

3. **Если проблема persists, попробуйте откатиться и применить заново:**
```bash
docker-compose -f docker/docker-compose.prod.yml run --rm bot alembic downgrade -1
docker-compose -f docker/docker-compose.prod.yml run --rm bot alembic upgrade head
```

## Откат (если что-то пошло не так)
```bash
docker-compose -f docker/docker-compose.prod.yml run --rm bot alembic downgrade -1
```

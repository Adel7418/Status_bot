# Инструкции для исправления продакшн базы данных

## Проблема
В продакшн контейнере отсутствуют колонки `deleted_at` и `version` в таблицах `orders` и `masters`, что вызывает ошибки при экспорте Excel отчетов.

## Решение

### Вариант 1: Выполнение через Docker (если Docker доступен)

1. **Остановить контейнер:**
   ```bash
   docker stop telegram_repair_bot_prod
   ```

2. **Запустить контейнер с обновленным скриптом:**
   ```bash
   docker run --rm -v $(pwd)/data:/app/data -v $(pwd)/update_production_db.py:/app/update_production_db.py telegram_repair_bot_prod python /app/update_production_db.py
   ```

3. **Запустить контейнер обратно:**
   ```bash
   docker start telegram_repair_bot_prod
   ```

### Вариант 2: Выполнение внутри запущенного контейнера

1. **Подключиться к контейнеру:**
   ```bash
   docker exec -it telegram_repair_bot_prod /bin/bash
   ```

2. **Выполнить SQL команды напрямую:**
   ```sql
   sqlite3 /app/data/bot_database.db

   -- Проверить существующие колонки
   .schema orders
   .schema masters

   -- Добавить недостающие колонки в orders
   ALTER TABLE orders ADD COLUMN deleted_at TIMESTAMP;
   ALTER TABLE orders ADD COLUMN version INTEGER DEFAULT 1;

   -- Добавить недостающие колонки в masters
   ALTER TABLE masters ADD COLUMN deleted_at TIMESTAMP;
   ALTER TABLE masters ADD COLUMN version INTEGER DEFAULT 1;

   -- Обновить существующие записи
   UPDATE orders SET version = 1 WHERE version IS NULL;
   UPDATE masters SET version = 1 WHERE version IS NULL;

   -- Проверить результат
   .schema orders
   .schema masters

   .quit
   ```

3. **Перезапустить бота:**
   ```bash
   exit
   docker restart telegram_repair_bot_prod
   ```

### Вариант 3: Копирование исправленной базы данных

1. **Остановить контейнер:**
   ```bash
   docker stop telegram_repair_bot_prod
   ```

2. **Скопировать исправленную базу данных:**
   ```bash
   # Создать резервную копию
   cp /path/to/production/data/bot_database.db /path/to/production/data/bot_database_backup_$(date +%Y%m%d_%H%M%S).db

   # Скопировать исправленную базу данных
   cp data/bot_database.db /path/to/production/data/bot_database.db
   ```

3. **Запустить контейнер:**
   ```bash
   docker start telegram_repair_bot_prod
   ```

## Проверка исправления

После выполнения любого из вариантов проверьте:

1. **Логи контейнера:**
   ```bash
   docker logs telegram_repair_bot_prod
   ```

2. **Тест экспорта Excel:**
   - Зайдите в бот
   - Перейдите в раздел отчетов
   - Попробуйте экспортировать статистику по мастерам

## Файлы для исправления

- `update_production_db.py` - скрипт для автоматического исправления
- `migrations/versions/add_missing_columns_to_orders_masters.py` - миграция Alembic

## Примечания

- Всегда создавайте резервную копию базы данных перед изменениями
- Проверьте, что контейнер остановлен перед изменением файлов базы данных
- После исправления перезапустите контейнер для применения изменений

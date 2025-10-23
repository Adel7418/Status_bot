-- Скрипт для исправления продакшн базы данных
-- Добавляет недостающие колонки deleted_at и version

-- Проверяем существующие колонки
.schema orders
.schema masters

-- Добавляем недостающие колонки в таблицу orders
ALTER TABLE orders ADD COLUMN deleted_at TIMESTAMP;
ALTER TABLE orders ADD COLUMN version INTEGER DEFAULT 1;

-- Добавляем недостающие колонки в таблицу masters
ALTER TABLE masters ADD COLUMN deleted_at TIMESTAMP;
ALTER TABLE masters ADD COLUMN version INTEGER DEFAULT 1;

-- Обновляем существующие записи
UPDATE orders SET version = 1 WHERE version IS NULL;
UPDATE masters SET version = 1 WHERE version IS NULL;

-- Проверяем результат
.schema orders
.schema masters

-- Показываем количество записей
SELECT 'Orders count:' as table_name, COUNT(*) as count FROM orders
UNION ALL
SELECT 'Masters count:' as table_name, COUNT(*) as count FROM masters;

-- Исправление CHECK constraint для статусов заказов в city2
-- Применение: sqlite3 data/city2/bot_database.db < scripts/fix_status_constraint_city2.sql
-- ИЛИ через docker:
-- docker exec -i telegram_repair_bot_city2 sqlite3 /app/data/bot_database.db < scripts/fix_status_constraint_city2.sql

BEGIN TRANSACTION;

-- Создаём новую таблицу с правильным constraint
CREATE TABLE orders_new (
    id INTEGER NOT NULL PRIMARY KEY,
    equipment_type TEXT,
    description TEXT,
    client_name TEXT,
    client_address TEXT,
    client_phone TEXT,
    status TEXT NOT NULL CHECK(status IN ('NEW', 'ASSIGNED', 'ACCEPTED', 'ONSITE', 'CLOSED', 'REFUSED', 'DR')),
    assigned_master_id INTEGER,
    dispatcher_id INTEGER,
    scheduled_time TEXT,
    total_amount REAL,
    materials_cost REAL,
    master_profit REAL,
    company_profit REAL,
    notes TEXT,
    out_of_city BOOLEAN DEFAULT 0,
    has_review BOOLEAN DEFAULT 0,
    created_at DATETIME,
    updated_at DATETIME,
    deleted_at DATETIME,
    version INTEGER DEFAULT 1,
    FOREIGN KEY(assigned_master_id) REFERENCES masters (id),
    FOREIGN KEY(dispatcher_id) REFERENCES users (telegram_id)
);

-- Копируем данные
INSERT INTO orders_new SELECT * FROM orders;

-- Удаляем старую таблицу
DROP TABLE orders;

-- Переименовываем новую
ALTER TABLE orders_new RENAME TO orders;

-- Восстанавливаем индексы (критичные индексы)
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_assigned_master_id ON orders(assigned_master_id);
CREATE INDEX IF NOT EXISTS idx_orders_dispatcher_id ON orders(dispatcher_id);
CREATE INDEX IF NOT EXISTS idx_orders_deleted_at ON orders(deleted_at);
CREATE INDEX IF NOT EXISTS idx_orders_status_created ON orders(status, created_at);
CREATE INDEX IF NOT EXISTS idx_orders_master_status ON orders(assigned_master_id, status);
CREATE INDEX IF NOT EXISTS idx_orders_period ON orders(updated_at, status);
CREATE INDEX IF NOT EXISTS idx_orders_financial ON orders(status, total_amount);
CREATE INDEX IF NOT EXISTS idx_orders_review ON orders(has_review, status);

COMMIT;


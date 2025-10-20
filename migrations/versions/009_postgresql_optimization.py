"""postgresql_optimization

Revision ID: 009_postgresql_optimization
Revises: 008_add_soft_delete
Create Date: 2025-01-17 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '009_postgresql_optimization'
down_revision: Union[str, None] = '008_add_soft_delete'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add PostgreSQL-specific optimizations"""
    
    # Создаем ENUM типы для PostgreSQL
    op.execute("CREATE TYPE order_status_enum AS ENUM ('NEW', 'ASSIGNED', 'IN_PROGRESS', 'COMPLETED', 'CLOSED', 'REFUSED')")
    op.execute("CREATE TYPE user_role_enum AS ENUM ('ADMIN', 'DISPATCHER', 'MASTER', 'UNKNOWN')")
    
    # Изменяем типы колонок на ENUM (только для PostgreSQL)
    op.execute("ALTER TABLE orders ALTER COLUMN status TYPE order_status_enum USING status::order_status_enum")
    op.execute("ALTER TABLE users ALTER COLUMN role TYPE user_role_enum USING role::user_role_enum")
    
    # Создаем партиционирование для больших таблиц (PostgreSQL)
    op.execute("""
        CREATE TABLE orders_partitioned (
            LIKE orders INCLUDING ALL
        ) PARTITION BY RANGE (created_at)
    """)
    
    # Создаем партиции по месяцам
    op.execute("""
        CREATE TABLE orders_2025_01 PARTITION OF orders_partitioned
        FOR VALUES FROM ('2025-01-01') TO ('2025-02-01')
    """)
    
    op.execute("""
        CREATE TABLE orders_2025_02 PARTITION OF orders_partitioned
        FOR VALUES FROM ('2025-02-01') TO ('2025-03-01')
    """)
    
    # Создаем индексы для партиционированных таблиц
    op.execute("CREATE INDEX idx_orders_partitioned_status ON orders_partitioned (status)")
    op.execute("CREATE INDEX idx_orders_partitioned_created ON orders_partitioned (created_at)")
    
    # Создаем материализованные представления для отчетов
    op.execute("""
        CREATE MATERIALIZED VIEW daily_orders_summary AS
        SELECT 
            DATE(created_at) as order_date,
            status,
            COUNT(*) as order_count,
            SUM(total_amount) as total_revenue,
            AVG(total_amount) as avg_order_value
        FROM orders
        WHERE deleted_at IS NULL
        GROUP BY DATE(created_at), status
    """)
    
    op.execute("CREATE UNIQUE INDEX idx_daily_orders_summary_unique ON daily_orders_summary (order_date, status)")
    
    # Создаем функцию для обновления материализованного представления
    op.execute("""
        CREATE OR REPLACE FUNCTION refresh_daily_orders_summary()
        RETURNS void AS $$
        BEGIN
            REFRESH MATERIALIZED VIEW CONCURRENTLY daily_orders_summary;
        END;
        $$ LANGUAGE plpgsql
    """)
    
    # Создаем триггеры для автоматического обновления
    op.execute("""
        CREATE OR REPLACE FUNCTION trigger_refresh_daily_orders()
        RETURNS trigger AS $$
        BEGIN
            PERFORM refresh_daily_orders_summary();
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql
    """)
    
    op.execute("""
        CREATE TRIGGER refresh_daily_orders_trigger
        AFTER INSERT OR UPDATE OR DELETE ON orders
        FOR EACH STATEMENT
        EXECUTE FUNCTION trigger_refresh_daily_orders()
    """)
    
    # Создаем индексы для полнотекстового поиска
    op.execute("CREATE INDEX idx_orders_description_fts ON orders USING gin(to_tsvector('russian', description))")
    op.execute("CREATE INDEX idx_orders_client_name_fts ON orders USING gin(to_tsvector('russian', client_name))")
    
    # Создаем индексы для JSON полей (если будут добавлены)
    # op.execute("CREATE INDEX idx_orders_metadata_gin ON orders USING gin(metadata)")
    
    # Настраиваем статистику для оптимизатора
    op.execute("ALTER TABLE orders ALTER COLUMN status SET STATISTICS 1000")
    op.execute("ALTER TABLE orders ALTER COLUMN created_at SET STATISTICS 1000")
    op.execute("ALTER TABLE users ALTER COLUMN role SET STATISTICS 1000")


def downgrade() -> None:
    """Remove PostgreSQL-specific optimizations"""
    
    # Удаляем триггеры и функции
    op.execute("DROP TRIGGER IF EXISTS refresh_daily_orders_trigger ON orders")
    op.execute("DROP FUNCTION IF EXISTS trigger_refresh_daily_orders()")
    op.execute("DROP FUNCTION IF EXISTS refresh_daily_orders_summary()")
    
    # Удаляем материализованные представления
    op.execute("DROP MATERIALIZED VIEW IF EXISTS daily_orders_summary")
    
    # Удаляем партиционированные таблицы
    op.execute("DROP TABLE IF EXISTS orders_2025_02")
    op.execute("DROP TABLE IF EXISTS orders_2025_01")
    op.execute("DROP TABLE IF EXISTS orders_partitioned")
    
    # Возвращаем типы колонок к TEXT
    op.execute("ALTER TABLE users ALTER COLUMN role TYPE TEXT")
    op.execute("ALTER TABLE orders ALTER COLUMN status TYPE TEXT")
    
    # Удаляем ENUM типы
    op.execute("DROP TYPE IF EXISTS user_role_enum")
    op.execute("DROP TYPE IF EXISTS order_status_enum")





"""Add missing columns to orders and masters tables

Revision ID: add_missing_columns_to_orders_masters
Revises: add_missing_columns
Create Date: 2025-10-23 07:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_missing_columns_to_orders_masters'
down_revision: Union[str, None] = 'add_missing_columns'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Добавляем недостающие колонки в таблицу orders
    conn = op.get_bind()
    
    # Проверяем существование таблицы orders
    try:
        conn.execute(sa.text("SELECT 1 FROM orders LIMIT 1"))
        table_exists = True
    except Exception:
        table_exists = False
    
    if table_exists:
        # Проверяем и добавляем колонку deleted_at в orders
        try:
            conn.execute(sa.text("SELECT deleted_at FROM orders LIMIT 1"))
        except Exception:
            op.add_column('orders', sa.Column('deleted_at', sa.TIMESTAMP(), nullable=True))
            print("✅ Добавлена колонка deleted_at в orders")
        
        # Проверяем и добавляем колонку version в orders
        try:
            conn.execute(sa.text("SELECT version FROM orders LIMIT 1"))
        except Exception:
            op.add_column('orders', sa.Column('version', sa.INTEGER(), server_default=sa.text('1'), nullable=False))
            print("✅ Добавлена колонка version в orders")
        
        # Обновляем существующие записи
        conn.execute(sa.text("UPDATE orders SET version = 1 WHERE version IS NULL"))
        print("✅ Обновлены существующие записи в orders")
    
    # Проверяем и добавляем недостающие колонки в таблицу masters
    try:
        conn.execute(sa.text("SELECT 1 FROM masters LIMIT 1"))
        masters_exists = True
    except Exception:
        masters_exists = False
    
    if masters_exists:
        # Проверяем и добавляем колонку deleted_at в masters
        try:
            conn.execute(sa.text("SELECT deleted_at FROM masters LIMIT 1"))
        except Exception:
            op.add_column('masters', sa.Column('deleted_at', sa.TIMESTAMP(), nullable=True))
            print("✅ Добавлена колонка deleted_at в masters")
        
        # Проверяем и добавляем колонку version в masters
        try:
            conn.execute(sa.text("SELECT version FROM masters LIMIT 1"))
        except Exception:
            op.add_column('masters', sa.Column('version', sa.INTEGER(), server_default=sa.text('1'), nullable=False))
            print("✅ Добавлена колонка version в masters")
        
        # Обновляем существующие записи
        conn.execute(sa.text("UPDATE masters SET version = 1 WHERE version IS NULL"))
        print("✅ Обновлены существующие записи в masters")


def downgrade() -> None:
    # Удаляем добавленные колонки
    conn = op.get_bind()
    
    # Удаляем колонки из orders
    try:
        conn.execute(sa.text("SELECT version FROM orders LIMIT 1"))
        op.drop_column('orders', 'version')
    except Exception:
        pass  # Колонка не существует
    
    try:
        conn.execute(sa.text("SELECT deleted_at FROM orders LIMIT 1"))
        op.drop_column('orders', 'deleted_at')
    except Exception:
        pass  # Колонка не существует
    
    # Удаляем колонки из masters
    try:
        conn.execute(sa.text("SELECT version FROM masters LIMIT 1"))
        op.drop_column('masters', 'version')
    except Exception:
        pass  # Колонка не существует
    
    try:
        conn.execute(sa.text("SELECT deleted_at FROM masters LIMIT 1"))
        op.drop_column('masters', 'deleted_at')
    except Exception:
        pass  # Колонка не существует

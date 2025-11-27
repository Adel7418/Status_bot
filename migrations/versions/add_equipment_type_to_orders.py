"""Add equipment_type column to orders if missing

Revision ID: add_equipment_type_to_orders
Revises: fix_status_check
Create Date: 2025-11-05 23:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_equipment_type_to_orders'
down_revision: Union[str, None] = 'a0752cb417aa'  # После add_specialization_rates_table
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Добавляет колонку equipment_type в таблицу orders, если её нет"""
    from sqlalchemy import inspect
    
    conn = op.get_bind()
    inspector = inspect(conn)
    
    # Проверяем существование таблицы orders
    if not inspector.has_table('orders'):
        print("[SKIP] Таблица orders не существует")
        return
    
    # Проверяем наличие колонки equipment_type
    columns = [col['name'] for col in inspector.get_columns('orders')]
    
    if 'equipment_type' in columns:
        print("[SKIP] Колонка equipment_type уже существует в таблице orders")
        return
    
    # Добавляем колонку equipment_type
    try:
        with op.batch_alter_table('orders', schema=None) as batch_op:
            batch_op.add_column(sa.Column('equipment_type', sa.String(length=255), nullable=False, server_default=''))
        print("[OK] Колонка equipment_type добавлена в таблицу orders")
    except Exception as e:
        print(f"[ERROR] Ошибка при добавлении колонки equipment_type: {e}")
        # Пытаемся добавить через прямой SQL (для SQLite)
        try:
            conn.execute(sa.text("ALTER TABLE orders ADD COLUMN equipment_type TEXT NOT NULL DEFAULT ''"))
            conn.commit()
            print("[OK] Колонка equipment_type добавлена через прямой SQL")
        except Exception as e2:
            print(f"[ERROR] Не удалось добавить колонку через прямой SQL: {e2}")


def downgrade() -> None:
    """Удаляет колонку equipment_type из таблицы orders"""
    from sqlalchemy import inspect
    
    conn = op.get_bind()
    inspector = inspect(conn)
    
    # Проверяем существование таблицы orders
    if not inspector.has_table('orders'):
        print("[SKIP] Таблица orders не существует")
        return
    
    # Проверяем наличие колонки equipment_type
    columns = [col['name'] for col in inspector.get_columns('orders')]
    
    if 'equipment_type' not in columns:
        print("[SKIP] Колонка equipment_type не существует в таблице orders")
        return
    
    # Удаляем колонку equipment_type
    try:
        with op.batch_alter_table('orders', schema=None) as batch_op:
            batch_op.drop_column('equipment_type')
        print("[OK] Колонка equipment_type удалена из таблицы orders")
    except Exception as e:
        print(f"[ERROR] Ошибка при удалении колонки equipment_type: {e}")


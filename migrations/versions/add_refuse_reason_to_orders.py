"""add_refuse_reason_to_orders

Revision ID: a1b2c3d4e5f6
Revises: 77f5626ac688
Create Date: 2025-11-17 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '77f5626ac688'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Добавление колонки refuse_reason в таблицу orders"""
    from sqlalchemy import inspect
    
    bind = op.get_bind()
    inspector = inspect(bind)
    
    # Проверяем существование таблицы orders
    if not inspector.has_table('orders'):
        print("[SKIP] Таблица orders не существует")
        return
    
    # Получаем список колонок
    columns = [c['name'] for c in inspector.get_columns('orders')]
    
    # Проверяем и добавляем колонку refuse_reason в orders
    if 'refuse_reason' in columns:
        print("[INFO] Колонка refuse_reason уже существует в orders")
    else:
        op.add_column('orders', sa.Column('refuse_reason', sa.String(500), nullable=True))
        print("[OK] Добавлена колонка refuse_reason в orders")


def downgrade() -> None:
    """Удаление колонки refuse_reason из orders"""
    from sqlalchemy import inspect
    
    bind = op.get_bind()
    inspector = inspect(bind)
    
    # Проверяем существование таблицы orders
    if not inspector.has_table('orders'):
        print("[SKIP] Таблица orders не существует")
        return
    
    # Получаем список колонок
    columns = [c['name'] for c in inspector.get_columns('orders')]
    
    # Удаляем refuse_reason
    if 'refuse_reason' in columns:
        op.drop_column('orders', 'refuse_reason')
        print("[OK] Удалена колонка refuse_reason из orders")
    else:
        print("[INFO] Колонка refuse_reason не существует в orders")


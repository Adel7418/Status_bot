"""add_master_lead_name_to_orders

Revision ID: 45a8674c6c41
Revises: merge_fix_status_heads
Create Date: 2025-11-01 11:31:30.423971

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '45a8674c6c41'
down_revision: Union[str, None] = 'merge_fix_status_heads'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Добавление колонки master_lead_name в таблицу orders
    
    NOTE: Эта миграция также добавляла lead_source, но в более поздней
    миграции 4734f51bfd4b колонка lead_source была удалена как неиспользуемая.
    """
    from sqlalchemy import inspect
    
    bind = op.get_bind()
    inspector = inspect(bind)
    
    # Проверяем существование таблицы orders
    if not inspector.has_table('orders'):
        print("[SKIP] Таблица orders не существует")
        return
    
    # Получаем список колонок
    columns = [c['name'] for c in inspector.get_columns('orders')]
    
    # Проверяем и добавляем колонку master_lead_name в orders
    if 'master_lead_name' in columns:
        print("[INFO] Колонка master_lead_name уже существует в orders")
    else:
        op.add_column('orders', sa.Column('master_lead_name', sa.String(255), nullable=True))
        print("[OK] Добавлена колонка master_lead_name в orders")


def downgrade() -> None:
    """Удаление колонки master_lead_name из orders"""
    from sqlalchemy import inspect
    
    bind = op.get_bind()
    inspector = inspect(bind)
    
    # Проверяем существование таблицы orders
    if not inspector.has_table('orders'):
        print("[SKIP] Таблица orders не существует")
        return
    
    # Получаем список колонок
    columns = [c['name'] for c in inspector.get_columns('orders')]
    
    # Удаляем master_lead_name
    if 'master_lead_name' in columns:
        op.drop_column('orders', 'master_lead_name')
        print("[OK] Удалена колонка master_lead_name из orders")
    else:
        print("[INFO] Колонка master_lead_name не существует в orders")

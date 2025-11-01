"""remove_lead_source_column

Revision ID: 4734f51bfd4b
Revises: 45a8674c6c41
Create Date: 2025-11-01 11:40:26.041275

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4734f51bfd4b'
down_revision: Union[str, None] = '45a8674c6c41'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Удаление колонки lead_source из таблицы orders"""
    from sqlalchemy import inspect
    
    bind = op.get_bind()
    inspector = inspect(bind)
    
    # Проверяем, существует ли таблица orders
    if not inspector.has_table('orders'):
        print("[SKIP] Таблица orders не существует")
        return
    
    # Получаем список колонок
    columns = [c['name'] for c in inspector.get_columns('orders')]
    
    # Удаляем lead_source если существует
    if 'lead_source' in columns:
        op.drop_column('orders', 'lead_source')
        print("[OK] Удалена колонка lead_source из orders")
    else:
        print("[SKIP] Колонка lead_source не существует в orders")


def downgrade() -> None:
    """Восстановление колонки lead_source в таблицу orders"""
    from sqlalchemy import inspect
    
    bind = op.get_bind()
    inspector = inspect(bind)
    
    # Проверяем, существует ли таблица orders
    if not inspector.has_table('orders'):
        print("[SKIP] Таблица orders не существует")
        return
    
    # Получаем список колонок
    columns = [c['name'] for c in inspector.get_columns('orders')]
    
    # Восстанавливаем lead_source если не существует
    if 'lead_source' not in columns:
        op.add_column('orders', sa.Column('lead_source', sa.String(200), nullable=False, server_default=''))
        print("[OK] Восстановлена колонка lead_source в orders")
        # Обновляем старые записи
        bind.execute(sa.text("UPDATE orders SET lead_source = 'Unknown' WHERE lead_source IS NULL OR lead_source = ''"))
        # Удаляем server_default
        with op.batch_alter_table('orders', schema=None) as batch_op:
            batch_op.alter_column('lead_source', nullable=False)
        print("[OK] Колонка lead_source теперь NOT NULL")
    else:
        print("[SKIP] Колонка lead_source уже существует в orders")

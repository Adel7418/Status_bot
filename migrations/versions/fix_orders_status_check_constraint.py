"""fix orders status check constraint

Revision ID: fix_status_check
Revises: add_missing_columns_to_orders_masters
Create Date: 2025-10-31 07:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fix_status_check'
down_revision = 'add_missing_columns_to_orders_masters'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Исправление CHECK constraint для статусов заказов
    
    SQLite не поддерживает DROP CONSTRAINT напрямую, поэтому используем batch_alter_table.
    """
    # Используем batch_alter_table для SQLite - он пересоздаст таблицу автоматически
    with op.batch_alter_table('orders', schema=None) as batch_op:
        # Пытаемся удалить старый constraint (может не сработать, но попробуем)
        try:
            batch_op.drop_constraint('chk_orders_status', type_='check')
        except Exception:
            # Игнорируем, если constraint уже удалён или его нет
            pass
        
        # Создаём новый constraint с правильными статусами
        batch_op.create_check_constraint(
            'chk_orders_status',
            "status IN ('NEW', 'ASSIGNED', 'ACCEPTED', 'ONSITE', 'CLOSED', 'REFUSED', 'DR')"
        )


def downgrade() -> None:
    """Откат к старому constraint (для совместимости)"""
    op.drop_constraint('chk_orders_status', 'orders', type_='check')
    op.create_check_constraint(
        'chk_orders_status',
        'orders',
        "status IN ('NEW', 'ASSIGNED', 'IN_PROGRESS', 'COMPLETED', 'CLOSED', 'REFUSED')"
    )


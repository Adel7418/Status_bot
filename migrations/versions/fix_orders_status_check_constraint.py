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
    """Исправление CHECK constraint для статусов заказов"""
    # Удаляем старый constraint
    op.drop_constraint('chk_orders_status', 'orders', type_='check')
    
    # Создаём новый с правильными статусами
    op.create_check_constraint(
        'chk_orders_status',
        'orders',
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


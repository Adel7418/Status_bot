"""add_reschedule_fields

Revision ID: 005_add_reschedule_fields
Revises: 004_add_order_reports
Create Date: 2025-10-16 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '005_add_reschedule_fields'
down_revision: Union[str, None] = '004_add_order_reports'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema"""
    
    # Добавляем поля для переноса заявок
    op.add_column('orders', sa.Column('rescheduled_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('orders', sa.Column('last_rescheduled_at', sa.DateTime(), nullable=True))
    op.add_column('orders', sa.Column('reschedule_reason', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade database schema"""
    
    # Удаляем поля
    op.drop_column('orders', 'reschedule_reason')
    op.drop_column('orders', 'last_rescheduled_at')
    op.drop_column('orders', 'rescheduled_count')


"""add_dr_fields

Revision ID: 003_add_dr_fields
Revises: 002_add_financial_reports
Create Date: 2025-10-15 03:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003_add_dr_fields'
down_revision: Union[str, None] = '002_add_financial_reports'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema"""
    
    # Добавляем поля для длительного ремонта
    op.add_column('orders', sa.Column('estimated_completion_date', sa.String(), nullable=True))
    op.add_column('orders', sa.Column('prepayment_amount', sa.Float(), nullable=True))


def downgrade() -> None:
    """Downgrade database schema"""
    
    # Удаляем поля
    op.drop_column('orders', 'prepayment_amount')
    op.drop_column('orders', 'estimated_completion_date')


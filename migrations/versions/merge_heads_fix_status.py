"""merge heads abcfdb12222b and fix_status_check

Revision ID: merge_fix_status_heads
Revises: abcfdb12222b, fix_status_check
Create Date: 2025-10-31 08:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'merge_fix_status_heads'
down_revision = ('abcfdb12222b', 'fix_status_check')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass



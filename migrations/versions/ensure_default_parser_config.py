"""Ensure default parser config exists

Revision ID: ensure_parser_config
Revises: add_parser_analytics
Create Date: 2025-01-30 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ensure_parser_config'
down_revision: Union[str, None] = 'add_parser_analytics'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ensure default configuration exists (id=1)
    # This is needed because previous migrations might have skipped insertion
    # if the table already existed but was empty.
    op.execute(
        """
        INSERT OR IGNORE INTO parser_config (id, group_id, enabled, created_at, updated_at)
        VALUES (1, NULL, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """
    )


def downgrade() -> None:
    pass

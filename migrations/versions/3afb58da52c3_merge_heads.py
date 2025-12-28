"""merge heads

Revision ID: 3afb58da52c3
Revises: ensure_parser_config, migrate_hardcoded_rules
Create Date: 2025-12-28 21:20:35.318913

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3afb58da52c3'
down_revision: Union[str, None] = ('ensure_parser_config', 'migrate_hardcoded_rules')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

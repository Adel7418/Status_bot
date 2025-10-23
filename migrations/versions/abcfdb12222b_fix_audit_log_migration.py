"""fix_audit_log_migration

Revision ID: abcfdb12222b
Revises: d0a601a63b16
Create Date: 2025-10-24 02:29:54.456034

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'abcfdb12222b'
down_revision: Union[str, None] = 'd0a601a63b16'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Таблица audit_log уже создана с колонкой deleted_at в предыдущих миграциях
    print("[SKIP] Таблица audit_log уже создана с колонкой deleted_at в предыдущих миграциях")


def downgrade() -> None:
    # Таблица audit_log будет удалена в предыдущих миграциях
    print("[SKIP] Таблица audit_log будет удалена в предыдущих миграциях")

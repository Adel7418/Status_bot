"""Add missing columns

Revision ID: add_missing_columns
Revises: 
Create Date: 2025-10-22 20:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_missing_columns'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Добавляем недостающие колонки в таблицу users
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('deleted_at', sa.TIMESTAMP(), nullable=True))
        batch_op.add_column(sa.Column('version', sa.INTEGER(), server_default=sa.text('1'), nullable=False))


def downgrade() -> None:
    # Удаляем добавленные колонки
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('version')
        batch_op.drop_column('deleted_at')

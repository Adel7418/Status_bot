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
    # Проверяем, существуют ли колонки перед добавлением
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('users')]
    
    if 'deleted_at' not in columns:
        op.add_column('users', sa.Column('deleted_at', sa.TIMESTAMP(), nullable=True))
    
    if 'version' not in columns:
        op.add_column('users', sa.Column('version', sa.INTEGER(), server_default=sa.text('1'), nullable=False))


def downgrade() -> None:
    # Удаляем добавленные колонки
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('users')]
    
    if 'version' in columns:
        op.drop_column('users', 'version')
    
    if 'deleted_at' in columns:
        op.drop_column('users', 'deleted_at')

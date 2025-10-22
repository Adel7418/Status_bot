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
    # Используем простой SQL для проверки и добавления колонок
    conn = op.get_bind()
    
    # Проверяем существование колонки deleted_at
    try:
        conn.execute(sa.text("SELECT deleted_at FROM users LIMIT 1"))
    except Exception:
        # Колонка не существует, добавляем её
        op.add_column('users', sa.Column('deleted_at', sa.TIMESTAMP(), nullable=True))
    
    # Проверяем существование колонки version
    try:
        conn.execute(sa.text("SELECT version FROM users LIMIT 1"))
    except Exception:
        # Колонка не существует, добавляем её
        op.add_column('users', sa.Column('version', sa.INTEGER(), server_default=sa.text('1'), nullable=False))


def downgrade() -> None:
    # Удаляем добавленные колонки
    conn = op.get_bind()
    
    # Проверяем существование колонки version
    try:
        conn.execute(sa.text("SELECT version FROM users LIMIT 1"))
        op.drop_column('users', 'version')
    except Exception:
        pass  # Колонка не существует
    
    # Проверяем существование колонки deleted_at
    try:
        conn.execute(sa.text("SELECT deleted_at FROM users LIMIT 1"))
        op.drop_column('users', 'deleted_at')
    except Exception:
        pass  # Колонка не существует

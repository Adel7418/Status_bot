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
    # Создаём таблицу users если она не существует
    conn = op.get_bind()
    
    # Проверяем существование таблицы users
    try:
        conn.execute(sa.text("SELECT 1 FROM users LIMIT 1"))
        table_exists = True
    except Exception:
        table_exists = False
    
    if not table_exists:
        # Создаём таблицу users с базовой структурой
        op.create_table('users',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('telegram_id', sa.Integer(), nullable=False),
            sa.Column('username', sa.String(length=255), nullable=True),
            sa.Column('first_name', sa.String(length=255), nullable=True),
            sa.Column('last_name', sa.String(length=255), nullable=True),
            sa.Column('role', sa.String(length=100), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('deleted_at', sa.TIMESTAMP(), nullable=True),
            sa.Column('version', sa.INTEGER(), server_default=sa.text('1'), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('telegram_id')
        )
    else:
        # Таблица существует, добавляем недостающие колонки
        try:
            conn.execute(sa.text("SELECT deleted_at FROM users LIMIT 1"))
        except Exception:
            op.add_column('users', sa.Column('deleted_at', sa.TIMESTAMP(), nullable=True))
        
        try:
            conn.execute(sa.text("SELECT version FROM users LIMIT 1"))
        except Exception:
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

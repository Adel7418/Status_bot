"""create_audit_log_table

Revision ID: create_audit_log_table
Revises: add_missing_columns_to_orders_masters
Create Date: 2025-10-24 02:25:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import func


# revision identifiers, used by Alembic.
revision: str = 'create_audit_log_table'
down_revision: Union[str, None] = 'add_missing_columns_to_orders_masters'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Создаём таблицу audit_log если она не существует
    conn = op.get_bind()
    
    # Проверяем существование таблицы audit_log
    try:
        result = conn.execute(sa.text("SELECT name FROM sqlite_master WHERE type='table' AND name='audit_log'")).fetchone()
        if result:
            print("[SKIP] Таблица audit_log уже существует")
            return
    except Exception as e:
        print(f"[ERROR] Ошибка при проверке таблицы audit_log: {e}")
        return
    
    # Создаём таблицу audit_log
    op.create_table('audit_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(length=255), nullable=False),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), server_default=func.now(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.telegram_id'], ),
    )
    
    # Создаём индексы
    op.create_index('idx_audit_user_id', 'audit_log', ['user_id'])
    op.create_index('idx_audit_timestamp', 'audit_log', ['timestamp'])
    op.create_index('idx_audit_log_deleted_at', 'audit_log', ['deleted_at'])
    
    print("[OK] Создана таблица audit_log с колонкой deleted_at")


def downgrade() -> None:
    # Удаляем таблицу audit_log
    op.drop_table('audit_log')
    print("[OK] Удалена таблица audit_log")

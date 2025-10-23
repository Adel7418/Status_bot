"""add_deleted_at_to_audit_log

Revision ID: d0a601a63b16
Revises: add_missing_columns_to_orders_masters
Create Date: 2025-10-24 02:20:49.695567

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import func


# revision identifiers, used by Alembic.
revision: str = 'd0a601a63b16'
down_revision: Union[str, None] = 'create_audit_log_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Создаем таблицу audit_log если она не существует, затем добавляем колонку deleted_at
    conn = op.get_bind()
    
    # Проверяем, существует ли таблица audit_log
    try:
        result = conn.execute(sa.text("SELECT name FROM sqlite_master WHERE type='table' AND name='audit_log'")).fetchone()
        if not result:
            print("[INFO] Таблица audit_log не существует - создаем её")
            # Создаем таблицу audit_log
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
            
            # Создаем индексы
            op.create_index('idx_audit_user_id', 'audit_log', ['user_id'])
            op.create_index('idx_audit_timestamp', 'audit_log', ['timestamp'])
            op.create_index('idx_audit_log_deleted_at', 'audit_log', ['deleted_at'])
            
            print("[OK] Создана таблица audit_log с колонкой deleted_at")
            return
        else:
            print("[INFO] Таблица audit_log существует - проверяем колонку deleted_at")
    except Exception as e:
        print(f"[ERROR] Ошибка при проверке таблицы audit_log: {e}")
        return
    
    # Проверяем, существует ли уже колонка deleted_at
    try:
        # Получаем информацию о колонках таблицы
        columns_result = conn.execute(sa.text("PRAGMA table_info(audit_log)")).fetchall()
        column_names = [row[1] for row in columns_result]  # row[1] - это имя колонки
        
        if 'deleted_at' in column_names:
            print("[OK] Колонка deleted_at уже существует в audit_log")
            return
        else:
            # Колонка не существует, добавляем её
            op.add_column('audit_log', sa.Column('deleted_at', sa.TIMESTAMP(), nullable=True))
            print("[OK] Добавлена колонка deleted_at в audit_log")
            
    except Exception as e:
        print(f"[ERROR] Ошибка при проверке/добавлении колонки: {e}")


def downgrade() -> None:
    # Удаляем таблицу audit_log
    conn = op.get_bind()
    
    # Проверяем, существует ли таблица audit_log
    try:
        result = conn.execute(sa.text("SELECT name FROM sqlite_master WHERE type='table' AND name='audit_log'")).fetchone()
        if result:
            op.drop_table('audit_log')
            print("[OK] Удалена таблица audit_log")
        else:
            print("[SKIP] Таблица audit_log не существует")
    except Exception as e:
        print(f"[ERROR] Ошибка при удалении таблицы audit_log: {e}")

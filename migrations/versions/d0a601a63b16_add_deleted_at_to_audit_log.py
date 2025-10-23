"""add_deleted_at_to_audit_log

Revision ID: d0a601a63b16
Revises: add_missing_columns_to_orders_masters
Create Date: 2025-10-24 02:20:49.695567

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd0a601a63b16'
down_revision: Union[str, None] = 'add_missing_columns_to_orders_masters'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Добавляем колонку deleted_at в таблицу audit_log
    conn = op.get_bind()
    
    # Сначала проверяем, существует ли таблица audit_log
    try:
        result = conn.execute(sa.text("SELECT name FROM sqlite_master WHERE type='table' AND name='audit_log'")).fetchone()
        if not result:
            print("[SKIP] Таблица audit_log не существует - пропускаем миграцию")
            return
    except Exception as e:
        print(f"[SKIP] Ошибка при проверке таблицы audit_log: {e} - пропускаем миграцию")
        return
    
    # Проверяем, существует ли уже колонка
    try:
        conn.execute(sa.text("SELECT deleted_at FROM audit_log LIMIT 1"))
        print("[OK] Колонка deleted_at уже существует в audit_log")
    except Exception:
        # Колонка не существует, добавляем её
        op.add_column('audit_log', sa.Column('deleted_at', sa.TIMESTAMP(), nullable=True))
        print("[OK] Добавлена колонка deleted_at в audit_log")


def downgrade() -> None:
    # Удаляем колонку deleted_at из таблицы audit_log
    conn = op.get_bind()
    
    # Проверяем, существует ли таблица audit_log
    try:
        result = conn.execute(sa.text("SELECT name FROM sqlite_master WHERE type='table' AND name='audit_log'")).fetchone()
        if not result:
            print("[SKIP] Таблица audit_log не существует - пропускаем откат")
            return
    except Exception as e:
        print(f"[SKIP] Ошибка при проверке таблицы audit_log: {e} - пропускаем откат")
        return
    
    # Удаляем колонку
    try:
        op.drop_column('audit_log', 'deleted_at')
        print("[OK] Удалена колонка deleted_at из audit_log")
    except Exception as e:
        print(f"[SKIP] Ошибка при удалении колонки: {e}")

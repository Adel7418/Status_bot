"""add_missing_indexes

Revision ID: 177152cb46fa
Revises: 10ff87cace39
Create Date: 2025-10-21 14:17:37.501380

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '177152cb46fa'
down_revision: Union[str, None] = '10ff87cace39'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Добавление недостающих индексов для оптимизации производительности."""
    
    # Добавляем индексы на audit_log
    with op.batch_alter_table('audit_log', schema=None) as batch_op:
        batch_op.create_index('idx_audit_timestamp', ['timestamp'], unique=False)
    
    # Удаляем старые индексы на financial_reports и не создаем новые
    # (они не нужны, так как эта таблица используется редко)
    try:
        with op.batch_alter_table('financial_reports', schema=None) as batch_op:
            batch_op.drop_index('idx_financial_reports_period')
            batch_op.drop_index('idx_financial_reports_type')
    except:
        pass  # Индексы могут уже быть удалены
    
    # Удаляем старые индексы на master_financial_reports
    try:
        with op.batch_alter_table('master_financial_reports', schema=None) as batch_op:
            batch_op.drop_index('idx_master_reports_master_id')
            batch_op.drop_index('idx_master_reports_report_id')
    except:
        pass  # Индексы могут уже быть удалены
    
    # Добавляем индексы на masters
    with op.batch_alter_table('masters', schema=None) as batch_op:
        batch_op.create_index('idx_masters_active_approved', ['is_active', 'is_approved'], unique=False)
        batch_op.create_index('idx_masters_work_chat', ['work_chat_id'], unique=False)
    
    # Добавляем индексы на order_status_history
    with op.batch_alter_table('order_status_history', schema=None) as batch_op:
        batch_op.create_index('idx_status_history_changed_at', ['changed_at'], unique=False)
        batch_op.create_index('idx_status_history_changed_by', ['changed_by'], unique=False)
        batch_op.create_index('idx_status_history_order', ['order_id', 'changed_at'], unique=False)
    
    # Добавляем индексы на orders
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.create_index('idx_orders_financial', ['status', 'total_amount'], unique=False)
        batch_op.create_index('idx_orders_master_status', ['assigned_master_id', 'status'], unique=False)
        batch_op.create_index('idx_orders_period', ['updated_at', 'status'], unique=False)
        batch_op.create_index('idx_orders_review', ['has_review', 'status'], unique=False)
        batch_op.create_index('idx_orders_status_created', ['status', 'created_at'], unique=False)


def downgrade() -> None:
    """Удаление добавленных индексов."""
    
    # Удаляем индексы с orders
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.drop_index('idx_orders_status_created')
        batch_op.drop_index('idx_orders_review')
        batch_op.drop_index('idx_orders_period')
        batch_op.drop_index('idx_orders_master_status')
        batch_op.drop_index('idx_orders_financial')
    
    # Удаляем индексы с order_status_history
    with op.batch_alter_table('order_status_history', schema=None) as batch_op:
        batch_op.drop_index('idx_status_history_order')
        batch_op.drop_index('idx_status_history_changed_by')
        batch_op.drop_index('idx_status_history_changed_at')
    
    # Удаляем индексы с masters
    with op.batch_alter_table('masters', schema=None) as batch_op:
        batch_op.drop_index('idx_masters_work_chat')
        batch_op.drop_index('idx_masters_active_approved')
    
    # Восстанавливаем старые индексы на master_financial_reports
    with op.batch_alter_table('master_financial_reports', schema=None) as batch_op:
        batch_op.create_index('idx_master_reports_report_id', ['report_id'], unique=False)
        batch_op.create_index('idx_master_reports_master_id', ['master_id'], unique=False)
    
    # Восстанавливаем старые индексы на financial_reports
    with op.batch_alter_table('financial_reports', schema=None) as batch_op:
        batch_op.create_index('idx_financial_reports_type', ['report_type'], unique=False)
        batch_op.create_index('idx_financial_reports_period', ['period_start', 'period_end'], unique=False)
    
    # Удаляем индексы с audit_log
    with op.batch_alter_table('audit_log', schema=None) as batch_op:
        batch_op.drop_index('idx_audit_timestamp')

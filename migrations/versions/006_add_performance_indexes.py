"""add_performance_indexes

Revision ID: 006_add_performance_indexes
Revises: 005_add_reschedule_fields
Create Date: 2025-01-17 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '006_add_performance_indexes'
down_revision: Union[str, None] = '005_add_reschedule_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add performance optimization indexes"""
    
    # Составные индексы для оптимизации запросов
    op.create_index('idx_orders_status_created', 'orders', ['status', 'created_at'], unique=False)
    op.create_index('idx_orders_master_status', 'orders', ['assigned_master_id', 'status'], unique=False)
    op.create_index('idx_orders_period', 'orders', ['updated_at', 'status'], unique=False)
    
    # Индексы для аудита и истории
    op.create_index('idx_audit_timestamp', 'audit_log', ['timestamp'], unique=False)
    op.create_index('idx_status_history_order', 'order_status_history', ['order_id', 'changed_at'], unique=False)
    
    # Индексы для финансовых отчетов
    op.create_index('idx_orders_financial', 'orders', ['status', 'total_amount'], unique=False)
    op.create_index('idx_orders_review', 'orders', ['has_review', 'status'], unique=False)
    
    # Индексы для мастеров
    op.create_index('idx_masters_active_approved', 'masters', ['is_active', 'is_approved'], unique=False)
    op.create_index('idx_masters_work_chat', 'masters', ['work_chat_id'], unique=False)


def downgrade() -> None:
    """Remove performance optimization indexes"""
    
    # Удаляем индексы в обратном порядке
    op.drop_index('idx_masters_work_chat', table_name='masters')
    op.drop_index('idx_masters_active_approved', table_name='masters')
    op.drop_index('idx_orders_review', table_name='orders')
    op.drop_index('idx_orders_financial', table_name='orders')
    op.drop_index('idx_status_history_order', table_name='order_status_history')
    op.drop_index('idx_audit_timestamp', table_name='audit_log')
    op.drop_index('idx_orders_period', table_name='orders')
    op.drop_index('idx_orders_master_status', table_name='orders')
    op.drop_index('idx_orders_status_created', table_name='orders')





"""add_soft_delete

Revision ID: 008_add_soft_delete
Revises: 006_add_performance_indexes
Create Date: 2025-01-17 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '008_add_soft_delete'
down_revision: Union[str, None] = '006_add_performance_indexes'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add soft delete functionality"""
    
    # Добавляем поля для soft delete
    op.add_column('users', sa.Column('deleted_at', sa.DateTime(), nullable=True))
    op.add_column('masters', sa.Column('deleted_at', sa.DateTime(), nullable=True))
    op.add_column('orders', sa.Column('deleted_at', sa.DateTime(), nullable=True))
    op.add_column('audit_log', sa.Column('deleted_at', sa.DateTime(), nullable=True))
    
    # Создаем индексы для soft delete
    op.create_index('idx_users_deleted_at', 'users', ['deleted_at'], unique=False)
    op.create_index('idx_masters_deleted_at', 'masters', ['deleted_at'], unique=False)
    op.create_index('idx_orders_deleted_at', 'orders', ['deleted_at'], unique=False)
    op.create_index('idx_audit_log_deleted_at', 'audit_log', ['deleted_at'], unique=False)
    
    # Добавляем поля для версионирования
    op.add_column('users', sa.Column('version', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('masters', sa.Column('version', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('orders', sa.Column('version', sa.Integer(), nullable=False, server_default='1'))
    
    # Создаем таблицу для истории изменений
    op.create_table(
        'entity_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('table_name', sa.String(50), nullable=False),
        sa.Column('record_id', sa.Integer(), nullable=False),
        sa.Column('field_name', sa.String(50), nullable=False),
        sa.Column('old_value', sa.Text(), nullable=True),
        sa.Column('new_value', sa.Text(), nullable=True),
        sa.Column('changed_by', sa.Integer(), nullable=True),
        sa.Column('changed_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['changed_by'], ['users.telegram_id'])
    )
    
    # Индексы для истории изменений
    op.create_index('idx_entity_history_table_record', 'entity_history', ['table_name', 'record_id'], unique=False)
    op.create_index('idx_entity_history_changed_at', 'entity_history', ['changed_at'], unique=False)
    op.create_index('idx_entity_history_changed_by', 'entity_history', ['changed_by'], unique=False)


def downgrade() -> None:
    """Remove soft delete functionality"""
    
    # Удаляем таблицу истории
    op.drop_index('idx_entity_history_changed_by', table_name='entity_history')
    op.drop_index('idx_entity_history_changed_at', table_name='entity_history')
    op.drop_index('idx_entity_history_table_record', table_name='entity_history')
    op.drop_table('entity_history')
    
    # Удаляем поля версионирования
    op.drop_column('orders', 'version')
    op.drop_column('masters', 'version')
    op.drop_column('users', 'version')
    
    # Удаляем индексы soft delete
    op.drop_index('idx_audit_log_deleted_at', table_name='audit_log')
    op.drop_index('idx_orders_deleted_at', table_name='orders')
    op.drop_index('idx_masters_deleted_at', table_name='masters')
    op.drop_index('idx_users_deleted_at', table_name='users')
    
    # Удаляем поля soft delete
    op.drop_column('audit_log', 'deleted_at')
    op.drop_column('orders', 'deleted_at')
    op.drop_column('masters', 'deleted_at')
    op.drop_column('users', 'deleted_at')





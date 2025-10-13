"""Initial schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2025-10-12 23:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial database schema"""
    
    # Создание таблицы users
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('telegram_id', sa.Integer(), nullable=False),
        sa.Column('username', sa.Text(), nullable=True),
        sa.Column('first_name', sa.Text(), nullable=True),
        sa.Column('last_name', sa.Text(), nullable=True),
        sa.Column('role', sa.Text(), nullable=False, server_default='UNKNOWN'),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('telegram_id')
    )
    
    # Создание индексов для users
    op.create_index('idx_users_telegram_id', 'users', ['telegram_id'], unique=False)
    op.create_index('idx_users_role', 'users', ['role'], unique=False)
    
    # Создание таблицы masters
    op.create_table(
        'masters',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('telegram_id', sa.Integer(), nullable=False),
        sa.Column('phone', sa.Text(), nullable=False),
        sa.Column('specialization', sa.Text(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('is_approved', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('work_chat_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('telegram_id'),
        sa.ForeignKeyConstraint(['telegram_id'], ['users.telegram_id'])
    )
    
    # Создание индексов для masters
    op.create_index('idx_masters_telegram_id', 'masters', ['telegram_id'], unique=False)
    op.create_index('idx_masters_is_approved', 'masters', ['is_approved'], unique=False)
    
    # Создание таблицы orders
    op.create_table(
        'orders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('equipment_type', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('client_name', sa.Text(), nullable=False),
        sa.Column('client_address', sa.Text(), nullable=False),
        sa.Column('client_phone', sa.Text(), nullable=False),
        sa.Column('status', sa.Text(), nullable=False, server_default='NEW'),
        sa.Column('assigned_master_id', sa.Integer(), nullable=True),
        sa.Column('dispatcher_id', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('scheduled_time', sa.Text(), nullable=True),
        sa.Column('total_amount', sa.Float(), nullable=True),
        sa.Column('materials_cost', sa.Float(), nullable=True),
        sa.Column('master_profit', sa.Float(), nullable=True),
        sa.Column('company_profit', sa.Float(), nullable=True),
        sa.Column('has_review', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['assigned_master_id'], ['masters.id']),
        sa.ForeignKeyConstraint(['dispatcher_id'], ['users.telegram_id'])
    )
    
    # Создание индексов для orders
    op.create_index('idx_orders_status', 'orders', ['status'], unique=False)
    op.create_index('idx_orders_assigned_master_id', 'orders', ['assigned_master_id'], unique=False)
    op.create_index('idx_orders_dispatcher_id', 'orders', ['dispatcher_id'], unique=False)
    
    # Создание таблицы audit_log
    op.create_table(
        'audit_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.Text(), nullable=False),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.telegram_id'])
    )
    
    # Создание индекса для audit_log
    op.create_index('idx_audit_user_id', 'audit_log', ['user_id'], unique=False)
    
    # Создание таблицы order_status_history
    op.create_table(
        'order_status_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('old_status', sa.Text(), nullable=True),
        sa.Column('new_status', sa.Text(), nullable=False),
        sa.Column('changed_by', sa.Integer(), nullable=True),
        sa.Column('changed_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id']),
        sa.ForeignKeyConstraint(['changed_by'], ['users.telegram_id'])
    )


def downgrade() -> None:
    """Drop all tables"""
    op.drop_table('order_status_history')
    op.drop_index('idx_audit_user_id', table_name='audit_log')
    op.drop_table('audit_log')
    op.drop_index('idx_orders_dispatcher_id', table_name='orders')
    op.drop_index('idx_orders_assigned_master_id', table_name='orders')
    op.drop_index('idx_orders_status', table_name='orders')
    op.drop_table('orders')
    op.drop_index('idx_masters_is_approved', table_name='masters')
    op.drop_index('idx_masters_telegram_id', table_name='masters')
    op.drop_table('masters')
    op.drop_index('idx_users_role', table_name='users')
    op.drop_index('idx_users_telegram_id', table_name='users')
    op.drop_table('users')




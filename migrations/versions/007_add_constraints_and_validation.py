"""add_constraints_and_validation

Revision ID: 007_add_constraints_and_validation
Revises: 006_add_performance_indexes
Create Date: 2025-01-17 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '007_add_constraints_and_validation'
down_revision: Union[str, None] = '006_add_performance_indexes'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add constraints and validation rules"""
    
    # Добавляем CHECK constraints для валидации статусов
    op.create_check_constraint(
        'chk_orders_status',
        'orders',
        "status IN ('NEW', 'ASSIGNED', 'IN_PROGRESS', 'COMPLETED', 'CLOSED', 'REFUSED')"
    )
    
    # Валидация ролей пользователей
    op.create_check_constraint(
        'chk_users_role',
        'users',
        "role IN ('ADMIN', 'DISPATCHER', 'MASTER', 'UNKNOWN') OR role LIKE '%,%'"
    )
    
    # Валидация булевых полей
    op.create_check_constraint(
        'chk_masters_is_active',
        'masters',
        'is_active IN (0, 1)'
    )
    
    op.create_check_constraint(
        'chk_masters_is_approved',
        'masters',
        'is_approved IN (0, 1)'
    )
    
    op.create_check_constraint(
        'chk_orders_has_review',
        'orders',
        'has_review IN (0, 1) OR has_review IS NULL'
    )
    
    # Валидация положительных сумм
    op.create_check_constraint(
        'chk_orders_total_amount',
        'orders',
        'total_amount IS NULL OR total_amount >= 0'
    )
    
    op.create_check_constraint(
        'chk_orders_materials_cost',
        'orders',
        'materials_cost IS NULL OR materials_cost >= 0'
    )
    
    op.create_check_constraint(
        'chk_orders_master_profit',
        'orders',
        'master_profit IS NULL OR master_profit >= 0'
    )
    
    op.create_check_constraint(
        'chk_orders_company_profit',
        'orders',
        'company_profit IS NULL OR company_profit >= 0'
    )
    
    # Валидация количества переносов
    op.create_check_constraint(
        'chk_orders_rescheduled_count',
        'orders',
        'rescheduled_count >= 0'
    )
    
    # Валидация телефонов (базовая)
    op.create_check_constraint(
        'chk_masters_phone',
        'masters',
        "phone LIKE '+%' OR phone LIKE '8%' OR phone LIKE '7%'"
    )
    
    # Валидация Telegram ID (должны быть положительными)
    op.create_check_constraint(
        'chk_users_telegram_id',
        'users',
        'telegram_id > 0'
    )
    
    op.create_check_constraint(
        'chk_masters_telegram_id',
        'masters',
        'telegram_id > 0'
    )


def downgrade() -> None:
    """Remove constraints and validation rules"""
    
    # Удаляем constraints в обратном порядке
    op.drop_constraint('chk_masters_telegram_id', 'masters', type_='check')
    op.drop_constraint('chk_users_telegram_id', 'users', type_='check')
    op.drop_constraint('chk_masters_phone', 'masters', type_='check')
    op.drop_constraint('chk_orders_rescheduled_count', 'orders', type_='check')
    op.drop_constraint('chk_orders_company_profit', 'orders', type_='check')
    op.drop_constraint('chk_orders_master_profit', 'orders', type_='check')
    op.drop_constraint('chk_orders_materials_cost', 'orders', type_='check')
    op.drop_constraint('chk_orders_total_amount', 'orders', type_='check')
    op.drop_constraint('chk_orders_has_review', 'orders', type_='check')
    op.drop_constraint('chk_masters_is_approved', 'masters', type_='check')
    op.drop_constraint('chk_masters_is_active', 'masters', type_='check')
    op.drop_constraint('chk_users_role', 'users', type_='check')
    op.drop_constraint('chk_orders_status', 'orders', type_='check')





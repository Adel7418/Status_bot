"""add_financial_reports_and_out_of_city

Revision ID: 002_add_financial_reports
Revises: 001_initial_schema
Create Date: 2025-01-14 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002_add_financial_reports'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema"""
    
    # Добавляем поле out_of_city в таблицу orders
    op.add_column('orders', sa.Column('out_of_city', sa.Boolean(), nullable=True))
    
    # Создаем таблицу финансовых отчетов
    op.create_table(
        'financial_reports',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('report_type', sa.String(), nullable=False),
        sa.Column('period_start', sa.String(), nullable=True),
        sa.Column('period_end', sa.String(), nullable=True),
        sa.Column('total_orders', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_amount', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('total_materials_cost', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('total_net_profit', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('total_company_profit', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('total_master_profit', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('average_check', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('created_at', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Создаем таблицу отчетов по мастерам
    op.create_table(
        'master_financial_reports',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('report_id', sa.Integer(), nullable=False),
        sa.Column('master_id', sa.Integer(), nullable=False),
        sa.Column('master_name', sa.String(), nullable=False),
        sa.Column('orders_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_amount', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('total_materials_cost', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('total_net_profit', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('total_master_profit', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('total_company_profit', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('average_check', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('reviews_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('out_of_city_count', sa.Integer(), nullable=False, server_default='0'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['report_id'], ['financial_reports.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['master_id'], ['masters.id'], ondelete='CASCADE')
    )
    
    # Создаем индексы для производительности
    op.create_index('idx_financial_reports_type', 'financial_reports', ['report_type'])
    op.create_index('idx_financial_reports_period', 'financial_reports', ['period_start', 'period_end'])
    op.create_index('idx_master_reports_report_id', 'master_financial_reports', ['report_id'])
    op.create_index('idx_master_reports_master_id', 'master_financial_reports', ['master_id'])


def downgrade() -> None:
    """Downgrade database schema"""
    
    # Удаляем индексы
    op.drop_index('idx_master_reports_master_id')
    op.drop_index('idx_master_reports_report_id')
    op.drop_index('idx_financial_reports_period')
    op.drop_index('idx_financial_reports_type')
    
    # Удаляем таблицы
    op.drop_table('master_financial_reports')
    op.drop_table('financial_reports')
    
    # Удаляем поле out_of_city
    # Примечание: SQLite не поддерживает DROP COLUMN напрямую
    # Нужно пересоздать таблицу, но для простоты оставляем поле
    # op.drop_column('orders', 'out_of_city')


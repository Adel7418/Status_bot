"""Add order reports table

Revision ID: 004
Revises: 003
Create Date: 2025-10-15 06:15:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '004'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade():
    """Add order_reports table for individual order tracking"""
    op.create_table('order_reports',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('equipment_type', sa.String(), nullable=False),
        sa.Column('client_name', sa.String(), nullable=False),
        sa.Column('client_address', sa.String(), nullable=True),
        sa.Column('master_id', sa.Integer(), nullable=True),
        sa.Column('master_name', sa.String(), nullable=True),
        sa.Column('dispatcher_id', sa.Integer(), nullable=True),
        sa.Column('dispatcher_name', sa.String(), nullable=True),
        sa.Column('total_amount', sa.Float(), nullable=False),
        sa.Column('materials_cost', sa.Float(), nullable=False),
        sa.Column('master_profit', sa.Float(), nullable=False),
        sa.Column('company_profit', sa.Float(), nullable=False),
        sa.Column('out_of_city', sa.Boolean(), nullable=True),
        sa.Column('has_review', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('closed_at', sa.DateTime(), nullable=False),
        sa.Column('completion_time_hours', sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create index for faster queries
    op.create_index('idx_order_reports_order_id', 'order_reports', ['order_id'])
    op.create_index('idx_order_reports_master_id', 'order_reports', ['master_id'])
    op.create_index('idx_order_reports_closed_at', 'order_reports', ['closed_at'])


def downgrade():
    """Remove order_reports table"""
    op.drop_index('idx_order_reports_closed_at', table_name='order_reports')
    op.drop_index('idx_order_reports_master_id', table_name='order_reports')
    op.drop_index('idx_order_reports_order_id', table_name='order_reports')
    op.drop_table('order_reports')

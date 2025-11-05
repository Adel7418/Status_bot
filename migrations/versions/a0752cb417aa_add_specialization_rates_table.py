"""add_specialization_rates_table

Revision ID: a0752cb417aa
Revises: 77f5626ac688
Create Date: 2025-11-05 19:50:06.625033

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a0752cb417aa'
down_revision: Union[str, None] = '77f5626ac688'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Создаем таблицу specialization_rates если её нет
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    
    if not inspector.has_table('specialization_rates'):
        op.create_table(
            'specialization_rates',
            sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
            sa.Column('specialization_name', sa.String(length=255), nullable=False),
            sa.Column('master_percentage', sa.Float(), nullable=False),
            sa.Column('company_percentage', sa.Float(), nullable=False),
            sa.Column('is_default', sa.Boolean(), nullable=False, server_default='0'),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('(CURRENT_TIMESTAMP)')),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('(CURRENT_TIMESTAMP)')),
            sa.Column('deleted_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('specialization_name'),
            sa.CheckConstraint('master_percentage >= 0 AND master_percentage <= 100', name='chk_master_percentage_range'),
            sa.CheckConstraint('company_percentage >= 0 AND company_percentage <= 100', name='chk_company_percentage_range'),
            sa.CheckConstraint('ABS(master_percentage + company_percentage - 100) < 0.01', name='chk_percentages_sum_100'),
        )
        
        # Создаем индексы
        op.create_index('idx_specialization_rates_name', 'specialization_rates', ['specialization_name'])
        op.create_index('idx_specialization_rates_default', 'specialization_rates', ['is_default'])
        
        print("[OK] Таблица specialization_rates создана")
        
        # Добавляем начальные данные: электрик и сантехник - 50/50 фиксированно
        connection = op.get_bind()
        connection.execute(
            sa.text("""
                INSERT INTO specialization_rates (specialization_name, master_percentage, company_percentage, is_default)
                VALUES 
                    ('электрик', 50.0, 50.0, 0),
                    ('сантехник', 50.0, 50.0, 0)
            """)
        )
        print("[OK] Добавлены начальные данные: электрик и сантехник - 50/50")
    else:
        print("[SKIP] Таблица specialization_rates уже существует")


def downgrade() -> None:
    # Удаляем таблицу specialization_rates если она существует
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    
    if inspector.has_table('specialization_rates'):
        op.drop_index('idx_specialization_rates_default', table_name='specialization_rates')
        op.drop_index('idx_specialization_rates_name', table_name='specialization_rates')
        op.drop_table('specialization_rates')
        print("[OK] Таблица specialization_rates удалена")
    else:
        print("[SKIP] Таблица specialization_rates не существует")

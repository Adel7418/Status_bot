"""
Создание таблицы для архивных отчетов мастеров

Revision ID: 010
Revises: 009
Create Date: 2025-10-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '010_create_master_reports_archive'
down_revision: Union[str, None] = '009_postgresql_optimization'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Создание таблицы архивных отчетов мастеров"""
    
    op.create_table(
        'master_reports_archive',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('master_id', sa.Integer(), nullable=False),
        sa.Column('period_start', sa.DateTime(), nullable=False, comment='Начало периода отчета'),
        sa.Column('period_end', sa.DateTime(), nullable=False, comment='Конец периода отчета'),
        sa.Column('file_path', sa.String(500), nullable=False, comment='Путь к файлу отчета'),
        sa.Column('file_name', sa.String(255), nullable=False, comment='Имя файла'),
        sa.Column('file_size', sa.Integer(), nullable=True, comment='Размер файла в байтах'),
        sa.Column('total_orders', sa.Integer(), default=0, comment='Всего заявок в отчете'),
        sa.Column('active_orders', sa.Integer(), default=0, comment='Активных заявок'),
        sa.Column('completed_orders', sa.Integer(), default=0, comment='Завершенных заявок'),
        sa.Column('total_revenue', sa.Float(), default=0.0, comment='Общая выручка'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('notes', sa.Text(), nullable=True, comment='Дополнительные заметки'),
        
        sa.ForeignKeyConstraint(['master_id'], ['masters.id'], ondelete='CASCADE'),
    )
    
    # Индексы для быстрого поиска
    op.create_index('idx_master_reports_master_id', 'master_reports_archive', ['master_id'])
    op.create_index('idx_master_reports_period', 'master_reports_archive', ['period_start', 'period_end'])
    op.create_index('idx_master_reports_created', 'master_reports_archive', ['created_at'])


def downgrade() -> None:
    """Удаление таблицы архивных отчетов"""
    op.drop_index('idx_master_reports_created', table_name='master_reports_archive')
    op.drop_index('idx_master_reports_period', table_name='master_reports_archive')
    op.drop_index('idx_master_reports_master_id', table_name='master_reports_archive')
    op.drop_table('master_reports_archive')


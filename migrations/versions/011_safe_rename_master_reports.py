"""Safe rename master_reports_archive to master_report_archives

Revision ID: 011_safe_rename
Revises: 010_create_master_reports_archive
Create Date: 2025-10-21 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '011_safe_rename'
down_revision: Union[str, None] = '010_create_master_reports_archive'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Безопасное переименование таблицы master_reports_archive → master_report_archives"""
    
    # SQLite не поддерживает ALTER TABLE RENAME COLUMN напрямую,
    # но поддерживает RENAME TABLE
    with op.batch_alter_table('master_reports_archive', schema=None) as batch_op:
        # Переименовываем таблицу
        pass  # batch_alter_table сам выполнит переименование при rename_table
    
    # Переименовываем таблицу
    op.rename_table('master_reports_archive', 'master_report_archives')
    
    # Обновляем индексы с новыми именами (старые будут автоматически пересозданы)
    # Индексы уже созданы в миграции 010, просто переименовываются автоматически


def downgrade() -> None:
    """Откат: master_report_archives → master_reports_archive"""
    
    op.rename_table('master_report_archives', 'master_reports_archive')



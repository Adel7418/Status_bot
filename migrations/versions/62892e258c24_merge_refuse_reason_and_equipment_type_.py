"""merge refuse_reason and equipment_type heads

Revision ID: 62892e258c24
Revises: add_equipment_type_to_orders, a1b2c3d4e5f6
Create Date: 2025-11-17 23:14:38.822657

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '62892e258c24'
down_revision: Union[str, None] = ('add_equipment_type_to_orders', 'a1b2c3d4e5f6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

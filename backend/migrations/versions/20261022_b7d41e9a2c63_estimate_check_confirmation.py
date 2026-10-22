"""estimate check confirmation

Revision ID: b7d41e9a2c63
Revises: 57031ffaa27f
Create Date: 2026-10-22 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import app.models.base  # noqa: F401  (custom column types)


# revision identifiers, used by Alembic.
revision: str = 'b7d41e9a2c63'
down_revision: Union[str, Sequence[str], None] = '57031ffaa27f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('estimates', schema=None) as batch_op:
        batch_op.add_column(sa.Column('check_confirmed_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('check_confirmed_by', sa.String(length=36), nullable=True))
        batch_op.create_foreign_key(
            batch_op.f('fk_estimates_check_confirmed_by_users'), 'users', ['check_confirmed_by'], ['id']
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('estimates', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('fk_estimates_check_confirmed_by_users'), type_='foreignkey')
        batch_op.drop_column('check_confirmed_by')
        batch_op.drop_column('check_confirmed_at')

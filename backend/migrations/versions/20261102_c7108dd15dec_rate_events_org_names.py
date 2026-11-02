"""rate events; company names no longer unique

Revision ID: c7108dd15dec
Revises: cbf967daf8d4
Create Date: 2026-11-02 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import app.models.base  # noqa: F401  (custom column types)


# revision identifiers, used by Alembic.
revision: str = "c7108dd15dec"
down_revision: Union[str, Sequence[str], None] = "cbf967daf8d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "rate_events",
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("key", sa.String(length=320), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rate_events")),
    )
    with op.batch_alter_table("rate_events", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_rate_events_kind"), ["kind"], unique=False)
        batch_op.create_index(batch_op.f("ix_rate_events_key"), ["key"], unique=False)
    # Two companies may share a name; a sign-up no longer learns that one exists.
    with op.batch_alter_table("organisations", schema=None) as batch_op:
        batch_op.drop_constraint("uq_organisations_name", type_="unique")


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("organisations", schema=None) as batch_op:
        batch_op.create_unique_constraint("uq_organisations_name", ["name"])
    with op.batch_alter_table("rate_events", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_rate_events_key"))
        batch_op.drop_index(batch_op.f("ix_rate_events_kind"))
    op.drop_table("rate_events")

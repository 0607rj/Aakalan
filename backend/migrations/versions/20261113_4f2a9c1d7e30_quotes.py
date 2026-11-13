"""quotes typed in to compare with an estimate

Revision ID: 4f2a9c1d7e30
Revises: c7108dd15dec
Create Date: 2026-11-13 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import app.models.base  # noqa: F401  (custom column types)


# revision identifiers, used by Alembic.
revision: str = "4f2a9c1d7e30"
down_revision: Union[str, Sequence[str], None] = "c7108dd15dec"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: a new table only, nothing else touched."""
    op.create_table(
        "quotes",
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("amount_paise", sa.BigInteger(), nullable=False),
        sa.Column("covers", sa.String(length=10), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("org_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organisations.id"], name=op.f("fk_quotes_org_id_organisations"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], name=op.f("fk_quotes_project_id_projects"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_quotes")),
    )
    with op.batch_alter_table("quotes", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_quotes_org_id"), ["org_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_quotes_project_id"), ["project_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("quotes", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_quotes_project_id"))
        batch_op.drop_index(batch_op.f("ix_quotes_org_id"))
    op.drop_table("quotes")

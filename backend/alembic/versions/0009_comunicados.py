"""comunicados das companhias (IPE)

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-19 10:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0009"
down_revision: str | Sequence[str] | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "filings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("protocol", sa.String(length=30), nullable=False),
        sa.Column("delivered_on", sa.Date(), nullable=False),
        sa.Column("category", sa.String(length=20), nullable=False),
        sa.Column("kind", sa.String(length=120), nullable=False),
        sa.Column("subject", sa.Text(), nullable=False),
        sa.Column("link", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asset_id", "protocol", name="uq_filings_asset_protocol"),
    )
    with op.batch_alter_table("filings", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_filings_asset_id"), ["asset_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_filings_delivered_on"), ["delivered_on"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("filings", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_filings_delivered_on"))
        batch_op.drop_index(batch_op.f("ix_filings_asset_id"))
    op.drop_table("filings")

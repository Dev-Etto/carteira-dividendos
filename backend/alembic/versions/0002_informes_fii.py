"""informes de FII

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-17 21:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "fii_reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("ref_date", sa.Date(), nullable=False),
        sa.Column("equity", sa.Float(), nullable=True),
        sa.Column("shares", sa.Float(), nullable=True),
        sa.Column("nav_per_share", sa.Float(), nullable=True),
        sa.Column("holders", sa.Integer(), nullable=True),
        sa.Column("admin_fee", sa.Float(), nullable=True),
        sa.Column("paper", sa.Float(), nullable=False),
        sa.Column("brick", sa.Float(), nullable=False),
        sa.Column("fof", sa.Float(), nullable=False),
        sa.Column("cash", sa.Float(), nullable=False),
        sa.Column("started_on", sa.Date(), nullable=True),
        sa.Column("listed", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asset_id", "ref_date"),
    )
    with op.batch_alter_table("fii_reports", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_fii_reports_asset_id"), ["asset_id"], unique=False)

    op.create_table(
        "fii_quarterly_reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("ref_date", sa.Date(), nullable=False),
        sa.Column("properties", sa.Integer(), nullable=True),
        sa.Column("vacancy", sa.Float(), nullable=True),
        sa.Column("largest_property_share", sa.Float(), nullable=True),
        sa.Column("largest_credit_value", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asset_id", "ref_date"),
    )
    with op.batch_alter_table("fii_quarterly_reports", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_fii_quarterly_reports_asset_id"), ["asset_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("fii_quarterly_reports", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_fii_quarterly_reports_asset_id"))
    op.drop_table("fii_quarterly_reports")
    with op.batch_alter_table("fii_reports", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_fii_reports_asset_id"))
    op.drop_table("fii_reports")

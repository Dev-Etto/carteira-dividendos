"""trimestres do ITR

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-18 22:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0008"
down_revision: str | Sequence[str] | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "quarterly_fundamentals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("quarter", sa.Integer(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("revenue", sa.Float(), nullable=True),
        sa.Column("ebit", sa.Float(), nullable=True),
        sa.Column("net_income", sa.Float(), nullable=True),
        sa.Column("equity", sa.Float(), nullable=True),
        sa.Column("gross_debt", sa.Float(), nullable=True),
        sa.Column("cash", sa.Float(), nullable=True),
        sa.Column("source", sa.String(length=10), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asset_id", "year", "quarter", name="uq_quarterly_fundamentals_asset"),
    )
    with op.batch_alter_table("quarterly_fundamentals", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_quarterly_fundamentals_asset_id"), ["asset_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("quarterly_fundamentals", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_quarterly_fundamentals_asset_id"))
    op.drop_table("quarterly_fundamentals")

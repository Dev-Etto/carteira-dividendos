"""ETFs: favoritos, taxa de administração, distribuição e patrimônio

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-17 23:30:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("assets", schema=None) as batch_op:
        batch_op.add_column(sa.Column("favorite", sa.Boolean(), server_default=sa.false(), nullable=False))
        batch_op.add_column(sa.Column("admin_fee", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("distributes", sa.Boolean(), nullable=True))

    op.create_table(
        "etf_reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("ref_date", sa.Date(), nullable=False),
        sa.Column("equity", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asset_id", "ref_date"),
    )
    with op.batch_alter_table("etf_reports", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_etf_reports_asset_id"), ["asset_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("etf_reports", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_etf_reports_asset_id"))
    op.drop_table("etf_reports")
    with op.batch_alter_table("assets", schema=None) as batch_op:
        batch_op.drop_column("distributes")
        batch_op.drop_column("admin_fee")
        batch_op.drop_column("favorite")

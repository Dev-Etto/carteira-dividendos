"""região dos ETFs (nacional ou internacional), para a classe internacional do ARCA

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-18 18:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006"
down_revision: str | Sequence[str] | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INTERNATIONAL_ETFS = ("IVVB11",)
"""ETFs de índice estrangeiro do universo inicial; os demais começam como nacionais."""


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("assets", schema=None) as batch_op:
        batch_op.add_column(sa.Column("region", sa.String(length=15), server_default="nacional", nullable=False))
    assets = sa.table("assets", sa.column("ticker", sa.String), sa.column("region", sa.String))
    op.execute(assets.update().where(assets.c.ticker.in_(INTERNATIONAL_ETFS)).values(region="internacional"))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("assets", schema=None) as batch_op:
        batch_op.drop_column("region")

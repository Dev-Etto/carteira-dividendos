"""balanço: circulante, dívida de curto prazo e imobilizado

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-18 12:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005"
down_revision: str | Sequence[str] | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

COLUMNS = ("current_assets", "current_liabilities", "short_term_debt", "fixed_assets")


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("fundamentals", schema=None) as batch_op:
        for name in COLUMNS:
            batch_op.add_column(sa.Column(name, sa.Float(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("fundamentals", schema=None) as batch_op:
        for name in reversed(COLUMNS):
            batch_op.drop_column(name)

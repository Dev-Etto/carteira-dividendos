"""metodologias: avaliação por método e escolhas no perfil

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-18 03:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UNNAMED_UNIQUE = {"uq": "uq_%(table_name)s_%(column_0_name)s"}
"""A unicidade de evaluations nasceu sem nome; esta convenção dá um nome a ela para o batch poder removê-la."""


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("evaluations", schema=None, naming_convention=UNNAMED_UNIQUE) as batch_op:
        batch_op.add_column(sa.Column("method", sa.String(length=20), server_default="barsi", nullable=False))
        batch_op.drop_constraint("uq_evaluations_asset_id", type_="unique")
        batch_op.create_unique_constraint("uq_evaluations_asset_id", ["asset_id", "date", "method"])
    op.execute(
        "UPDATE evaluations SET method = (SELECT assets.asset_class FROM assets WHERE assets.id = evaluations.asset_id) "
        "WHERE asset_id IN (SELECT id FROM assets WHERE asset_class IN ('fii', 'etf'))"
    )
    with op.batch_alter_table("profile", schema=None) as batch_op:
        batch_op.add_column(sa.Column("selection_method", sa.String(length=20), server_default="barsi", nullable=False))
        batch_op.add_column(sa.Column("allocation_method", sa.String(length=20), server_default="perfil", nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("profile", schema=None) as batch_op:
        batch_op.drop_column("allocation_method")
        batch_op.drop_column("selection_method")
    op.execute("DELETE FROM evaluations WHERE method NOT IN ('barsi', 'fii', 'etf')")
    with op.batch_alter_table("evaluations", schema=None, naming_convention=UNNAMED_UNIQUE) as batch_op:
        batch_op.drop_constraint("uq_evaluations_asset_id", type_="unique")
        batch_op.create_unique_constraint("uq_evaluations_asset_id", ["asset_id", "date"])
        batch_op.drop_column("method")

"""caixa a investir: sobras do aporte que voltam no próximo plano

Revision ID: 0010
Revises: 0009
Create Date: 2026-11-19 20:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0010"
down_revision: str | Sequence[str] | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Cria a marca e aplica às sobras já registradas pelo plano de aporte, que têm sempre a mesma assinatura:
    Tesouro Selic do Tesouro Nacional, taxa zero, liquidez diária e fora da reserva de emergência."""
    with op.batch_alter_table("fixed_income_holdings", schema=None) as batch_op:
        batch_op.add_column(sa.Column("to_invest", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.execute(
        "UPDATE fixed_income_holdings SET to_invest = 1 WHERE name = 'Tesouro Selic' AND issuer = 'Tesouro Nacional' "
        "AND indexer = 'selic' AND rate = 0 AND daily_liquidity = 1 AND is_emergency_reserve = 0"
    )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("fixed_income_holdings", schema=None) as batch_op:
        batch_op.drop_column("to_invest")

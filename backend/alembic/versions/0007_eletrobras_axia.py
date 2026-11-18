"""Eletrobras passa a negociar como Axia Energia (AXIA3)

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-18 20:00:00

"""

from collections.abc import Sequence

from alembic import op

revision: str = "0007"
down_revision: str | Sequence[str] | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Renomeia o ativo no lugar, para manter preços, proventos, operações e avaliações. Se o AXIA3 já
    foi cadastrado à parte (pela tela Explorar), o ELET3 só deixa de ser atualizado."""
    op.execute(
        "UPDATE assets SET ticker = 'AXIA3', name = 'Axia Energia (ex-Eletrobras)', economic_group = 'Axia' "
        "WHERE ticker = 'ELET3' AND NOT EXISTS (SELECT 1 FROM assets WHERE ticker = 'AXIA3')"
    )
    op.execute("UPDATE assets SET active = 0 WHERE ticker = 'ELET3'")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        "UPDATE assets SET ticker = 'ELET3', name = 'Eletrobras', economic_group = NULL "
        "WHERE ticker = 'AXIA3' AND NOT EXISTS (SELECT 1 FROM assets WHERE ticker = 'ELET3')"
    )
    op.execute("UPDATE assets SET active = 1 WHERE ticker = 'ELET3'")

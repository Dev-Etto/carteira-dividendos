"""Indicadores do Banco Central (Selic, CDI, IPCA 12 meses)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import MacroRate
from app.schemas.api import MacroOut


def _latest(db: Session, series: str) -> MacroRate | None:
    return db.scalar(select(MacroRate).where(MacroRate.series == series).order_by(MacroRate.date.desc()).limit(1))


def latest_macro(db: Session) -> MacroOut:
    """Último valor de cada série; `as_of` é a data mais recente entre elas."""
    selic, cdi, ipca = _latest(db, "selic_meta"), _latest(db, "cdi"), _latest(db, "ipca_12m")
    found = [r for r in (selic, cdi, ipca) if r is not None]
    return MacroOut(
        selic_meta=selic.value if selic else None,
        cdi=cdi.value if cdi else None,
        ipca_12m=ipca.value if ipca else None,
        as_of=max((r.date for r in found), default=None),
    )

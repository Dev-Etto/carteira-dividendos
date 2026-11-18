"""Indicadores do Banco Central (Selic, CDI, IPCA 12 meses)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import MacroRate, TreasuryBond
from app.schemas.api import MacroOut


def _latest(db: Session, series: str) -> MacroRate | None:
    return db.scalar(select(MacroRate).where(MacroRate.series == series).order_by(MacroRate.date.desc()).limit(1))


def latest_rate(db: Session, series: str) -> float | None:
    row = _latest(db, series)
    return row.value if row else None


def system_npl_pct(db: Session) -> float | None:
    """Inadimplência acima de 90 dias de todo o sistema financeiro, em %, a régua dos bancos."""
    rate = latest_rate(db, "inadimplencia_sfn")
    return rate * 100 if rate is not None else None


def ntnb_real_rate(db: Session) -> float | None:
    """Juro real do Tesouro IPCA+ de vencimento mais longo na data mais recente: a referência de
    retorno sem risco acima da inflação, com a qual se compara o rendimento de um FII de tijolo."""
    day = db.scalar(select(TreasuryBond.date).order_by(TreasuryBond.date.desc()).limit(1))
    return db.scalar(
        select(TreasuryBond.buy_rate)
        .where(TreasuryBond.date == day, TreasuryBond.name.like("%IPCA+%"), TreasuryBond.buy_rate.is_not(None))
        .order_by(TreasuryBond.maturity.desc())
        .limit(1)
    )


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

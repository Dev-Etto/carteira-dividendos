"""Renda fixa: aplicações do usuário, taxas do Tesouro Direto e comparador isento × tributado."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.db.models import FixedIncomeHolding, TreasuryBond
from app.engine.renda_fixa import (
    TAX_EXEMPT,
    annual_gross_rate,
    check_reserve_eligibility,
    ir_rate,
    net_annual_rate,
    taxed_equivalent,
)
from app.schemas.api import CompareIn, CompareOut, FixedIncomeIn, FixedIncomeOut, TreasuryOut
from app.services.macro import latest_macro

FALLBACK_CDI = 0.1375
FALLBACK_SELIC = 0.1375
FALLBACK_IPCA = 0.045


def holding_out(h: FixedIncomeHolding) -> FixedIncomeOut:
    out = FixedIncomeOut.model_validate(h)
    check = check_reserve_eligibility(h.kind, h.indexer, h.daily_liquidity, h.rate, h.fgc_covered)
    out.reserve_ok, out.reserve_reason = check.ok, check.reason
    return out


def _get_holding(db: Session, holding_id: int) -> FixedIncomeHolding:
    h = db.get(FixedIncomeHolding, holding_id)
    if h is None:
        raise NotFoundError("Aplicação não encontrada")
    return h


def list_holdings(db: Session) -> list[FixedIncomeOut]:
    return [holding_out(h) for h in db.scalars(select(FixedIncomeHolding).order_by(FixedIncomeHolding.start_date))]


def create_holding(db: Session, body: FixedIncomeIn) -> FixedIncomeOut:
    h = FixedIncomeHolding(**body.model_dump())
    db.add(h)
    db.commit()
    return holding_out(h)


def add_holdings(db: Session, items: list[FixedIncomeIn]) -> list[FixedIncomeHolding]:
    """Adiciona à sessão várias aplicações (registro do aporte). Quem chama faz o commit."""
    holdings = [FixedIncomeHolding(**item.model_dump()) for item in items]
    db.add_all(holdings)
    return holdings


def update_holding(db: Session, holding_id: int, body: FixedIncomeIn) -> FixedIncomeOut:
    h = _get_holding(db, holding_id)
    for field, value in body.model_dump().items():
        setattr(h, field, value)
    db.commit()
    return holding_out(h)


def delete_holding(db: Session, holding_id: int) -> None:
    db.delete(_get_holding(db, holding_id))
    db.commit()


def list_treasury(db: Session) -> list[TreasuryOut]:
    """Títulos à venda no último dia disponível do Tesouro Transparente."""
    last = db.scalar(select(func.max(TreasuryBond.date)))
    if not last:
        return []
    bonds = db.scalars(
        select(TreasuryBond)
        .where(TreasuryBond.date == last, TreasuryBond.buy_rate.is_not(None))
        .order_by(TreasuryBond.name, TreasuryBond.maturity)
    )
    return [TreasuryOut(name=b.name, maturity=b.maturity, date=b.date, buy_rate=b.buy_rate, buy_price=b.buy_price) for b in bonds]


def compare(db: Session, body: CompareIn) -> CompareOut:
    """Rendimento bruto e líquido de um título e a taxa equivalente do outro lado (isento × tributado).

    `body.rate` é % do CDI para o indexador cdi e % ao ano nos demais. Sem dados do Banco Central,
    usa as taxas de referência FALLBACK_*.
    """
    macro = latest_macro(db)
    cdi = macro.cdi or FALLBACK_CDI
    rate = body.rate if body.indexer == "cdi" else body.rate / 100
    gross = annual_gross_rate(body.indexer, rate, cdi, macro.ipca_12m or FALLBACK_IPCA, macro.selic_meta or FALLBACK_SELIC)
    net = net_annual_rate(gross, body.kind, body.days)
    exempt = body.kind in TAX_EXEMPT
    return CompareOut(
        gross_annual=gross,
        net_annual=net,
        ir_rate=0.0 if exempt else ir_rate(body.days),
        tax_exempt=exempt,
        equivalent_label="Um CDB precisaria render, bruto" if exempt else "Uma LCI/LCA isenta equivalente renderia",
        equivalent_rate=taxed_equivalent(gross, body.days) if exempt else net,
        vs_cdi_net=net - cdi * (1 - ir_rate(body.days)),
    )

"""Aporte do mês: monta o plano com o motor puro e registra o que foi feito a partir dele."""

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Asset, TreasuryBond
from app.engine import fmt
from app.engine.aporte import Candidate, PlanLine, build_plan
from app.schemas.api import FixedIncomeIn, PlanLineOut, PlanOut, RegisterPlanIn, RegisterPlanOut
from app.services.evaluation import latest_evaluations
from app.services.fixed_income import add_holdings, consume_cash_to_invest, holding_out
from app.services.portfolio import PortfolioState, load_portfolio
from app.services.profile import current_allocation, get_profile, reserve_target, targets
from app.services.transactions import add_plan_purchases, tx_out

LONG_TERM_FALLBACK = "Tesouro IPCA+ (vencimento longo) ou CDB ≥ 100% do CDI"
LIQUID_FIXED_INCOME = "Tesouro Selic ou CDB com liquidez diária ≥ 100% do CDI"
LONG_TERM_MIN_YEARS = 5


def best_long_treasury(db: Session) -> TreasuryBond | None:
    """Tesouro IPCA+ sem juros semestrais com vencimento mais curto entre os de pelo menos 5 anos."""
    last = db.scalar(select(TreasuryBond.date).order_by(TreasuryBond.date.desc()).limit(1))
    bonds = db.scalars(
        select(TreasuryBond).where(
            TreasuryBond.date == last,
            TreasuryBond.name.like("%IPCA+%"),
            TreasuryBond.name.not_like("%Juros%"),
            TreasuryBond.buy_rate.is_not(None),
        )
    ).all()
    long_bonds = [b for b in bonds if b.maturity.year >= date.today().year + LONG_TERM_MIN_YEARS]
    return min(long_bonds, key=lambda b: b.maturity, default=None)


def _bond_label(bond: TreasuryBond | None) -> str:
    if bond is None:
        return LONG_TERM_FALLBACK
    return f"{bond.name} {bond.maturity.year} (IPCA + {fmt.pct(bond.buy_rate, 2)})"


def buy_candidates(db: Session, state: PortfolioState, asset_class: str) -> list[Candidate]:
    """Ativos da classe (acao | fii) com veredito "comprar" e preço conhecido, com o quanto já há de
    cada um na carteira. O grupo de concentração é o setor da ação ou o tipo do FII."""
    held = {p.ticker: p.value for p in state.positions}
    assets = {a.id: a for a in db.scalars(select(Asset).where(Asset.active, Asset.asset_class == asset_class))}
    evaluations = latest_evaluations(db, assets)
    return [
        Candidate(
            ticker=asset.ticker,
            name=asset.name,
            price=asset.last_price,
            score=ev.score,
            margin=ev.margin_pct or 0.0,
            sector=asset.sector,
            held_value=held.get(asset.ticker, 0.0),
        )
        for asset_id, ev in evaluations.items()
        if ev.verdict == "comprar" and (asset := assets.get(asset_id)) and asset.last_price
    ]


def favorite_etfs(db: Session, state: PortfolioState, region: str | None = None) -> list[Candidate]:
    """ETFs marcados como favoritos, com preço e sem reprovação eliminatória (veredito "evitar").
    Com `region`, só os daquela região (nacional ou internacional)."""
    held = {p.ticker: p.value for p in state.positions}
    query = select(Asset).where(Asset.active, Asset.asset_class == "etf", Asset.favorite)
    if region is not None:
        query = query.where(Asset.region == region)
    assets = list(db.scalars(query))
    evaluations = latest_evaluations(db, [a.id for a in assets])
    avoided = {asset_id for asset_id, ev in evaluations.items() if ev.verdict == "evitar"}
    return [
        Candidate(
            ticker=asset.ticker,
            name=asset.name,
            price=asset.last_price,
            score=evaluations[asset.id].score if asset.id in evaluations else 0,
            margin=0.0,
            sector="etf",
            held_value=held.get(asset.ticker, 0.0),
        )
        for asset in assets
        if asset.last_price and asset.id not in avoided
    ]


def _money(value: float) -> Decimal:
    return Decimal(str(round(value, 2)))


def _selic_holding(line: PlanLine, is_reserve: bool, to_invest: bool) -> FixedIncomeIn:
    """Tesouro Selic da reserva, do caixa a investir (a sobra do plano, marcada para o próximo aporte) ou da
    renda fixa de uma divisão que a quer como caixa (o "C" do ARCA)."""
    return FixedIncomeIn(
        name="Tesouro Selic",
        issuer="Tesouro Nacional",
        kind="tesouro",
        indexer="selic",
        rate=0.0,
        start_date=date.today(),
        daily_liquidity=True,
        amount=_money(line.amount),
        is_emergency_reserve=is_reserve,
        fgc_covered=True,
        to_invest=to_invest,
    )


def _long_term_holding(line: PlanLine, bond: TreasuryBond | None) -> FixedIncomeIn | None:
    """Só há aplicação pronta quando o plano indicou um título específico; senão o usuário escolhe."""
    if bond is None or bond.buy_rate is None:
        return None
    return FixedIncomeIn(
        name=f"{bond.name} {bond.maturity.year}",
        issuer="Tesouro Nacional",
        kind="tesouro",
        indexer="ipca",
        rate=round(bond.buy_rate * 100, 2),
        start_date=date.today(),
        maturity=bond.maturity,
        daily_liquidity=True,
        amount=_money(line.amount),
        is_emergency_reserve=False,
        fgc_covered=True,
    )


def _suggested_holding(line: PlanLine, bond: TreasuryBond | None, liquid: bool) -> FixedIncomeIn | None:
    """Aplicação pronta para cadastrar a partir de uma linha de renda fixa do plano."""
    builders = {
        "reserva": lambda: _selic_holding(line, is_reserve=True, to_invest=False),
        "caixa": lambda: _selic_holding(line, is_reserve=False, to_invest=True),
        "renda_fixa": lambda: _selic_holding(line, False, False) if liquid else _long_term_holding(line, bond),
    }
    build = builders.get(line.asset_class)
    return build() if build else None


def make_plan(db: Session, amount: float) -> PlanOut:
    profile = get_profile(db)
    state = load_portfolio(db)
    bond = best_long_treasury(db)
    liquid = current_allocation(db).liquid_fixed_income
    plan = build_plan(
        amount=amount + state.cash_to_invest,
        reserve_current=state.reserve,
        reserve_target=reserve_target(profile),
        class_current=state.class_values,
        targets=targets(db),
        stock_candidates=buy_candidates(db, state, "acao"),
        fii_candidates=buy_candidates(db, state, "fii"),
        etf_candidates=favorite_etfs(db, state),
        international_candidates=favorite_etfs(db, state, "internacional"),
        long_term_fixed_income=LIQUID_FIXED_INCOME if liquid else _bond_label(bond),
    )
    notes = [f"Inclui {fmt.brl(state.cash_to_invest)} do caixa a investir de aportes anteriores."] if state.cash_to_invest else []
    return PlanOut(
        amount=plan.amount,
        cash_used=state.cash_to_invest,
        lines=[
            PlanLineOut.model_validate({**vars(line), "holding": _suggested_holding(line, bond, liquid)}) for line in plan.lines
        ],
        notes=notes + plan.notes,
        leftover=plan.leftover,
    )


def register_plan(db: Session, body: RegisterPlanIn) -> RegisterPlanOut:
    """Registra as compras e as aplicações do plano numa única transação: ou entram todas, ou nenhuma."""
    consume_cash_to_invest(db, body.cash_used)
    transactions = add_plan_purchases(db, body.date, body.purchases)
    holdings = add_holdings(db, body.holdings)
    db.commit()
    return RegisterPlanOut(transactions=[tx_out(t) for t in transactions], holdings=[holding_out(h) for h in holdings])

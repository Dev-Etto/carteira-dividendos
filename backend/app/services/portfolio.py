"""Carteira consolidada: posições, valor por classe e setor, divisão atual × alvo e alertas."""

from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Asset, Dividend, Evaluation, FixedIncomeHolding, Profile, Split, Transaction
from app.engine import fmt
from app.engine.carteira import PositionCalc, SplitEvent, Tx, compute_position, entitled_income
from app.engine.renda_fixa import check_reserve_eligibility
from app.schemas.api import ClassSlice, PortfolioOut, PositionOut
from app.services.evaluation import latest_evaluations
from app.services.fixed_income import holding_out
from app.services.profile import ASSET_CLASSES, get_profile, reserve_target, targets

CLASS_OF = {"acao": "acoes", "fii": "fiis", "etf": "etfs"}

MAX_STOCK_SHARE = 0.20
MAX_SECTOR_SHARE = 0.30
MIN_STOCKS_FOR_CONCENTRATION = 5


@dataclass
class PositionView:
    asset_id: int
    ticker: str
    name: str
    asset_class: str
    sector: str
    quantity: float
    avg_price: float
    total_cost: float
    price: float | None
    value: float
    profit: float
    profit_pct: float | None
    weight_pct: float
    income_12m: float
    yield_on_cost: float | None


@dataclass(frozen=True)
class PortfolioState:
    """Fotografia da carteira calculada uma vez por requisição. `class_values` não inclui a reserva."""

    positions: list[PositionView]
    holdings: list[FixedIncomeHolding]
    class_values: dict[str, float]
    reserve: float

    @property
    def total_invested(self) -> float:
        return sum(self.class_values.values())

    @property
    def income_12m(self) -> float:
        return sum(p.income_12m for p in self.positions)

    @property
    def stocks(self) -> list[PositionView]:
        return [p for p in self.positions if p.asset_class == "acoes"]

    @property
    def sector_values(self) -> dict[str, float]:
        return _sum_by_sector(self.positions)


def _sum_by_sector(items: list["PositionView"]) -> dict[str, float]:
    out: dict[str, float] = defaultdict(float)
    for p in items:
        out[p.sector] += p.value
    return dict(out)


def _position_view(asset: Asset, pos: PositionCalc, income: Decimal) -> PositionView:
    qty = float(pos.quantity)
    cost = float(pos.total_cost)
    value = qty * asset.last_price if asset.last_price else cost
    return PositionView(
        asset_id=asset.id,
        ticker=asset.ticker,
        name=asset.name,
        asset_class=CLASS_OF.get(asset.asset_class, asset.asset_class),
        sector=asset.sector,
        quantity=qty,
        avg_price=float(pos.avg_price),
        total_cost=cost,
        price=asset.last_price,
        value=value,
        profit=value - cost,
        profit_pct=(value / cost - 1) if cost else None,
        weight_pct=0.0,
        income_12m=float(income),
        yield_on_cost=(float(income) / cost) if cost else None,
    )


def positions(db: Session) -> list[PositionView]:
    """Posições abertas, ordenadas da maior para a menor, com os proventos de 12 meses a que tiveram direito."""
    txs_by_asset: dict[int, list[Tx]] = defaultdict(list)
    for t in db.scalars(select(Transaction).order_by(Transaction.date, Transaction.id)):
        txs_by_asset[t.asset_id].append(Tx(t.date, t.kind, Decimal(t.quantity), Decimal(t.price), Decimal(t.fees or 0)))
    if not txs_by_asset:
        return []
    assets = {a.id: a for a in db.scalars(select(Asset).where(Asset.id.in_(txs_by_asset)))}
    splits: dict[int, list[SplitEvent]] = defaultdict(list)
    for s in db.scalars(select(Split).where(Split.asset_id.in_(txs_by_asset))):
        splits[s.asset_id].append(SplitEvent(s.date, Decimal(str(s.ratio))))
    year_ago = date.today() - timedelta(days=365)
    divs_ttm: dict[int, list[tuple[date, float]]] = defaultdict(list)
    dividends = select(Dividend).where(
        Dividend.asset_id.in_(txs_by_asset), Dividend.ex_date > year_ago, Dividend.kind != "amortizacao"
    )
    for d in db.scalars(dividends):
        divs_ttm[d.asset_id].append((d.ex_date, d.amount))

    out: list[PositionView] = []
    for aid, txs in txs_by_asset.items():
        first = min(t.date for t in txs)
        pos = compute_position(txs, [s for s in splits[aid] if s.date > first])
        if pos.quantity <= 0:
            continue
        out.append(_position_view(assets[aid], pos, entitled_income(txs, splits[aid], divs_ttm[aid])))
    total = sum(p.value for p in out)
    for p in out:
        p.weight_pct = 100 * p.value / total if total else 0.0
    return sorted(out, key=lambda p: -p.value)


def load_portfolio(db: Session) -> PortfolioState:
    pos = positions(db)
    holdings = list(db.scalars(select(FixedIncomeHolding).order_by(FixedIncomeHolding.start_date)))
    values = dict.fromkeys(ASSET_CLASSES, 0.0)
    for p in pos:
        values[p.asset_class] = values.get(p.asset_class, 0.0) + p.value
    values["renda_fixa"] += sum(float(h.amount) for h in holdings if not h.is_emergency_reserve)
    reserve = sum(float(h.amount) for h in holdings if h.is_emergency_reserve)
    return PortfolioState(positions=pos, holdings=holdings, class_values=values, reserve=reserve)


def class_slices(state: PortfolioState, target: dict[str, float]) -> list[ClassSlice]:
    total = state.total_invested
    return [
        ClassSlice(
            asset_class=cls,
            value=state.class_values.get(cls, 0.0),
            current_pct=100 * state.class_values.get(cls, 0.0) / total if total else 0.0,
            target_pct=target.get(cls, 0.0),
        )
        for cls in ASSET_CLASSES
    ]


def _reserve_alerts(state: PortfolioState, profile: Profile) -> list[str]:
    target = reserve_target(profile)
    if not profile.onboarded or state.reserve >= target:
        return []
    return [
        f"Reserva de emergência em {fmt.brl(state.reserve)} de {fmt.brl(target)}. Complete antes de investir em renda variável."
    ]


def _verdict_alerts(state: PortfolioState, evaluations: dict[int, Evaluation]) -> list[str]:
    return [
        f"{p.ticker} está com veredito 'evitar' (nota {ev.score}). Revise se a tese de compra continua válida."
        for p in state.positions
        if (ev := evaluations.get(p.asset_id)) and ev.verdict == "evitar"
    ]


def _concentration_alerts(state: PortfolioState) -> list[str]:
    """Só faz sentido falar de concentração a partir de algumas ações na carteira."""
    stocks = state.stocks
    total = sum(p.value for p in stocks)
    if len(stocks) < MIN_STOCKS_FOR_CONCENTRATION or not total:
        return []
    by_stock = [
        f"{p.ticker} representa {fmt.pct(p.value / total, 0)} das suas ações. O limite sugerido é {fmt.pct(MAX_STOCK_SHARE, 0)}."
        for p in stocks
        if p.value / total > MAX_STOCK_SHARE
    ]
    by_sector = [
        f"O setor {sector} tem {fmt.pct(v / total, 0)} das suas ações. O limite sugerido é {fmt.pct(MAX_SECTOR_SHARE, 0)}."
        for sector, v in _sum_by_sector(stocks).items()
        if v / total > MAX_SECTOR_SHARE
    ]
    return by_stock + by_sector


def _reserve_eligibility_alerts(state: PortfolioState) -> list[str]:
    checks = [
        (h, check_reserve_eligibility(h.kind, h.indexer, h.daily_liquidity, h.rate, h.fgc_covered))
        for h in state.holdings
        if h.is_emergency_reserve
    ]
    return [f"{h.name} está marcado como reserva, mas: {chk.reason}" for h, chk in checks if not chk.ok]


def portfolio_alerts(state: PortfolioState, profile: Profile, evaluations: dict[int, Evaluation]) -> list[str]:
    return [
        *_reserve_alerts(state, profile),
        *_verdict_alerts(state, evaluations),
        *_concentration_alerts(state),
        *_reserve_eligibility_alerts(state),
    ]


def _position_out(p: PositionView, ev: Evaluation | None) -> PositionOut:
    return PositionOut.model_validate({**asdict(p), "verdict": ev.verdict if ev else None})


def build_portfolio(db: Session) -> PortfolioOut:
    profile = get_profile(db)
    state = load_portfolio(db)
    evaluations = latest_evaluations(db, [p.asset_id for p in state.positions])
    return PortfolioOut(
        positions=[_position_out(p, evaluations.get(p.asset_id)) for p in state.positions],
        fixed_income=[holding_out(h) for h in state.holdings],
        classes=class_slices(state, targets(db)),
        sectors=state.sector_values,
        total_invested=state.total_invested,
        reserve_value=state.reserve,
        reserve_target=reserve_target(profile),
        income_12m=state.income_12m,
        alerts=portfolio_alerts(state, profile, evaluations),
    )

"""Monta o StockSnapshot do motor a partir do banco."""

from collections import defaultdict
from datetime import date, timedelta
from statistics import mean

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Asset, Dividend, Fundamental, PriceDaily, SectorMetric
from app.engine.types import StockSnapshot, YearFundamentals


def _multiple(price: float, amount: float | None, shares: float) -> float | None:
    """Preço ÷ valor por ação (lucro → P/L, patrimônio → P/VP). Só faz sentido com valor positivo."""
    if not amount or amount <= 0:
        return None
    return price / (amount / shares)


def _multiples_history(
    month_close: dict[tuple[int, int], float],
    fundamentals: dict[int, YearFundamentals],
    shares: float | None,
    price: float | None,
    today: date,
) -> tuple[list[float], list[float]]:
    """Séries mensais de P/L e P/VP dos últimos 5 anos, mais o ponto de hoje.

    Cada mês usa o último fechamento do mês e o balanço do ano anterior, que já estava publicado.
    O ponto de hoje usa o preço atual e o balanço mais recente.
    """
    if not shares:
        return [], []
    start = today - timedelta(days=365 * 5)
    points = [(close, fundamentals.get(y - 1)) for (y, m), close in sorted(month_close.items()) if date(y, m, 1) >= start]
    latest = fundamentals.get(max(fundamentals)) if fundamentals else None
    if price:
        points.append((price, latest))
    pe = [_multiple(close, f.net_income, shares) for close, f in points if f]
    pb = [_multiple(close, f.equity, shares) for close, f in points if f]
    return [v for v in pe if v is not None], [v for v in pb if v is not None]


def build_stock_snapshot(db: Session, asset: Asset, today: date | None = None) -> StockSnapshot:
    today = today or date.today()
    prices = db.execute(
        select(PriceDaily.date, PriceDaily.close, PriceDaily.volume)
        .where(PriceDaily.asset_id == asset.id, PriceDaily.date >= today - timedelta(days=365 * 7))
        .order_by(PriceDaily.date)
    ).all()
    divs = db.execute(
        select(Dividend.ex_date, Dividend.amount).where(Dividend.asset_id == asset.id, Dividend.kind != "amortizacao")
    ).all()
    funds = db.scalars(select(Fundamental).where(Fundamental.asset_id == asset.id)).all()
    metrics = db.scalars(select(SectorMetric).where(SectorMetric.asset_id == asset.id)).all()

    price = asset.last_price or (prices[-1].close if prices else None)

    recent = prices[-63:]
    avg_vol = mean(p.close * p.volume for p in recent) if len(recent) >= 20 else None

    by_year: dict[int, float] = defaultdict(float)
    ttm = 0.0
    for d in divs:
        by_year[d.ex_date.year] += d.amount
        if d.ex_date > today - timedelta(days=365):
            ttm += d.amount

    price_by_year: dict[int, list[float]] = defaultdict(list)
    month_close: dict[tuple[int, int], float] = {}
    for p in prices:
        price_by_year[p.date.year].append(p.close)
        month_close[(p.date.year, p.date.month)] = p.close

    fundamentals = {
        f.year: YearFundamentals(
            year=f.year,
            revenue=f.revenue,
            ebit=f.ebit,
            depreciation=f.depreciation,
            net_income=f.net_income,
            equity=f.equity,
            gross_debt=f.gross_debt,
            cash=f.cash,
            operating_cash_flow=f.operating_cash_flow,
            investing_cash_flow=f.investing_cash_flow,
            dividends_paid=f.dividends_paid,
        )
        for f in funds
    }

    pe_hist, pb_hist = _multiples_history(month_close, fundamentals, asset.shares_outstanding, price, today)

    return StockSnapshot(
        ticker=asset.ticker,
        name=asset.name,
        sector=asset.sector,
        segment=asset.segment,
        price=price,
        avg_daily_volume_brl=avg_vol,
        shares_outstanding=asset.shares_outstanding,
        dividends_by_year=dict(by_year),
        dividends_ttm=ttm if divs else None,
        avg_price_by_year={y: mean(v) for y, v in price_by_year.items()},
        fundamentals=fundamentals,
        sector_metrics={m.key: m.value for m in metrics},
        pe_history=pe_hist,
        pb_history=pb_hist,
        current_year=today.year,
    )

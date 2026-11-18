"""Monta os snapshots do motor (ações, FIIs e ETFs) a partir do banco."""

from collections import defaultdict
from datetime import date, timedelta
from statistics import mean
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    Asset,
    Dividend,
    EtfReport,
    FiiQuarterlyReport,
    FiiReport,
    Fundamental,
    PriceDaily,
    QuarterlyFundamental,
    SectorMetric,
)
from app.engine.types import EtfSnapshot, FiiKind, FiiSnapshot, QuarterFundamentals, StockSnapshot, YearFundamentals
from app.services.macro import latest_rate, ntnb_real_rate

LIQUIDITY_WINDOW = 63
"""Pregões (cerca de 3 meses) da média de volume diário em R$."""
MIN_LIQUIDITY_SAMPLE = 20
FII_KIND_BY_SECTOR: dict[str, FiiKind] = {"papel": "papel", "tijolo": "tijolo", "fof": "fof", "hibrido": "hibrido"}


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


def _avg_daily_volume(points: list[tuple[float, float]]) -> float | None:
    recent = points[-LIQUIDITY_WINDOW:]
    if len(recent) < MIN_LIQUIDITY_SAMPLE:
        return None
    return mean(close * volume for close, volume in recent)


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

    avg_vol = _avg_daily_volume([(p.close, p.volume) for p in prices])

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
            current_assets=f.current_assets,
            current_liabilities=f.current_liabilities,
            short_term_debt=f.short_term_debt,
            fixed_assets=f.fixed_assets,
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
        ntnb_real=ntnb_real_rate(db),
        quarters=stock_quarters(db, asset.id),
    )


def stock_quarters(db: Session, asset_id: int) -> list[QuarterFundamentals]:
    rows = db.scalars(
        select(QuarterlyFundamental)
        .where(QuarterlyFundamental.asset_id == asset_id)
        .order_by(QuarterlyFundamental.year, QuarterlyFundamental.quarter)
    )
    return [QuarterFundamentals(year=q.year, quarter=q.quarter, revenue=q.revenue, net_income=q.net_income) for q in rows]


def _report_fields(report: FiiReport | None) -> dict[str, Any]:
    """Campos do snapshot que vêm do informe mensal; vazio enquanto o informe não foi carregado."""
    if report is None:
        return {}
    return {
        "equity": report.equity,
        "nav_per_share": report.nav_per_share,
        "holders": report.holders,
        "listed": report.listed,
        "started_on": report.started_on,
        "admin_fee_month": report.admin_fee,
    }


def _quarterly_fields(quarterly: FiiQuarterlyReport | None) -> dict[str, Any]:
    if quarterly is None:
        return {}
    return {
        "largest_property_share": quarterly.largest_property_share,
        "properties": quarterly.properties,
        "vacancy": quarterly.vacancy,
    }


def _dividends_windows(db: Session, asset_id: int, today: date) -> tuple[float | None, float | None]:
    """Proventos por cota nos últimos 12 meses e nos 12 meses anteriores. Sem nenhum provento, (None, None)."""
    divs = db.execute(
        select(Dividend.ex_date, Dividend.amount).where(
            Dividend.asset_id == asset_id, Dividend.kind != "amortizacao", Dividend.ex_date > today - timedelta(days=730)
        )
    ).all()
    if not divs:
        return None, None
    year_ago = today - timedelta(days=365)
    ttm = sum(d.amount for d in divs if d.ex_date > year_ago)
    prev = sum(d.amount for d in divs if d.ex_date <= year_ago)
    return ttm, prev


def _credit_share(report: FiiReport | None, quarterly: FiiQuarterlyReport | None) -> float | None:
    if report is None or quarterly is None or not report.equity or quarterly.largest_credit_value is None:
        return None
    return quarterly.largest_credit_value / report.equity


def build_fii_snapshot(db: Session, asset: Asset, today: date | None = None) -> FiiSnapshot:
    today = today or date.today()
    prices = db.execute(
        select(PriceDaily.close, PriceDaily.volume)
        .where(PriceDaily.asset_id == asset.id, PriceDaily.date >= today - timedelta(days=120))
        .order_by(PriceDaily.date)
    ).all()
    report = db.scalar(select(FiiReport).where(FiiReport.asset_id == asset.id).order_by(FiiReport.ref_date.desc()).limit(1))
    quarterly = db.scalar(
        select(FiiQuarterlyReport)
        .where(FiiQuarterlyReport.asset_id == asset.id)
        .order_by(FiiQuarterlyReport.ref_date.desc())
        .limit(1)
    )
    ttm, prev = _dividends_windows(db, asset.id, today)
    return FiiSnapshot(
        ticker=asset.ticker,
        name=asset.name,
        kind=FII_KIND_BY_SECTOR.get(asset.sector, "hibrido"),
        today=today,
        segment=asset.segment,
        price=asset.last_price or (prices[-1].close if prices else None),
        avg_daily_volume_brl=_avg_daily_volume([(p.close, p.volume) for p in prices]),
        dividends_ttm=ttm,
        dividends_prev_ttm=prev,
        cdi=latest_rate(db, "cdi"),
        ntnb_real=ntnb_real_rate(db),
        largest_credit_share=_credit_share(report, quarterly),
        **_report_fields(report),
        **_quarterly_fields(quarterly),
    )


def build_etf_snapshot(db: Session, asset: Asset, today: date | None = None) -> EtfSnapshot:
    """Proventos só quando a fonte de cotações os traz; se o ETF distribui, quem diz é o usuário."""
    today = today or date.today()
    prices = db.execute(
        select(PriceDaily.close, PriceDaily.volume)
        .where(PriceDaily.asset_id == asset.id, PriceDaily.date >= today - timedelta(days=120))
        .order_by(PriceDaily.date)
    ).all()
    equity = db.scalar(
        select(EtfReport.equity).where(EtfReport.asset_id == asset.id).order_by(EtfReport.ref_date.desc()).limit(1)
    )
    ttm, _ = _dividends_windows(db, asset.id, today)
    return EtfSnapshot(
        ticker=asset.ticker,
        name=asset.name,
        price=asset.last_price or (prices[-1].close if prices else None),
        avg_daily_volume_brl=_avg_daily_volume([(p.close, p.volume) for p in prices]),
        equity=equity,
        admin_fee=asset.admin_fee,
        dividends_ttm=ttm,
        distributes=asset.distributes,
    )

"""Universo de ativos: listagem com a avaliação do dia, ficha completa, histórico e cadastro."""

from collections import defaultdict
from datetime import date, timedelta
from statistics import mean

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.db.models import Asset, Dividend, Evaluation, Fundamental, PriceDaily
from app.engine.types import RuleResult
from app.schemas.api import AssetCreate, AssetDetail, AssetHistory, AssetRow, DividendYearOut, PricePointOut, ScorePointOut
from app.services.evaluation import evaluate_asset, latest_evaluation, latest_evaluations, save_evaluation
from app.services.sync import start_background_sync

SECTOR_RISKS = {
    "bancos": "Bancos sofrem com aumento da inadimplência em crises e com mudanças de regulação do Banco Central.",
    "seguros": "Seguradoras dependem de juros altos para a receita financeira; quando a Selic cai, o lucro tende a cair.",
    "energia": "Empresas de energia dependem de regras do governo (ANEEL), de chuvas e da renovação das concessões.",
    "saneamento": "Saneamento depende de revisões tarifárias e de decisões políticas dos estados e municípios.",
    "telecom": "Telecom exige investimentos altos e constantes em rede, e a concorrência pressiona preços.",
    "ciclico": "Setor cíclico: lucro e dividendos podem cair muito quando a economia ou o preço das commodities cai.",
    "perene": "Mesmo setores estáveis enfrentam concorrência e mudanças de hábito dos consumidores.",
}
VERDICT_ORDER = {"comprar": 0, "aguardar": 1, "neutro": 2, "evitar": 3}
VOLUME_WINDOW_DAYS = 63
VOLUME_MIN_DAYS = 20
MAX_WARN_RISKS = 3
CHART_EVERY_N_DAYS = 5
NEW_ASSET_SYNC_STEPS = {"cvm", "mercado", "avaliacoes"}


def get_asset(db: Session, ticker: str) -> Asset:
    asset = db.scalar(select(Asset).where(Asset.ticker == ticker.strip().upper()))
    if asset is None:
        raise NotFoundError(f"Ativo {ticker} não está no universo. Cadastre-o em Explorar.")
    return asset


def _avg_volume(db: Session, asset_id: int) -> float | None:
    """Volume financeiro médio dos últimos ~3 meses de pregão."""
    rows = db.execute(
        select(PriceDaily.close, PriceDaily.volume)
        .where(PriceDaily.asset_id == asset_id)
        .order_by(PriceDaily.date.desc())
        .limit(VOLUME_WINDOW_DAYS)
    ).all()
    return mean(r.close * r.volume for r in rows) if len(rows) >= VOLUME_MIN_DAYS else None


def asset_row(asset: Asset, ev: Evaluation | None, avg_volume: float | None = None) -> AssetRow:
    return AssetRow(
        ticker=asset.ticker,
        name=asset.name,
        asset_class=asset.asset_class,
        sector=asset.sector,
        segment=asset.segment,
        price=asset.last_price,
        price_at=asset.last_price_at,
        score=ev.score if ev else None,
        verdict=ev.verdict if ev else None,
        ceiling_price=ev.ceiling_price if ev else None,
        margin_pct=ev.margin_pct if ev else None,
        dividend_yield=ev.dividend_yield if ev else None,
        avg_daily_volume_brl=avg_volume,
        evaluated_on=ev.date if ev else None,
    )


def _matches(ev: Evaluation | None, verdict: str | None, min_score: int | None) -> bool:
    verdict_ok = not verdict or (ev is not None and ev.verdict == verdict)
    score_ok = min_score is None or (ev is not None and ev.score >= min_score)
    return verdict_ok and score_ok


def list_assets(
    db: Session,
    asset_class: str | None = None,
    sector: str | None = None,
    verdict: str | None = None,
    min_score: int | None = None,
    search: str | None = None,
) -> list[AssetRow]:
    """Ativos ativos filtrados, do melhor veredito para o pior e, dentro dele, da maior nota para a menor."""
    query = select(Asset).where(Asset.active)
    if asset_class:
        query = query.where(Asset.asset_class == asset_class)
    if sector:
        query = query.where(Asset.sector == sector)
    if search:
        like = f"%{search.upper()}%"
        query = query.where(func.upper(Asset.ticker).like(like) | func.upper(Asset.name).like(like))
    assets = list(db.scalars(query))
    evaluations = latest_evaluations(db, [a.id for a in assets])
    rows = [asset_row(a, evaluations.get(a.id)) for a in assets if _matches(evaluations.get(a.id), verdict, min_score)]
    return sorted(rows, key=lambda r: (VERDICT_ORDER.get(r.verdict or "", len(VERDICT_ORDER)), -(r.score or 0)))


def buy_opportunities(db: Session, limit: int) -> list[AssetRow]:
    """Ações com veredito "comprar", da maior nota para a menor."""
    assets = {a.id: a for a in db.scalars(select(Asset).where(Asset.active, Asset.asset_class == "acao"))}
    evaluations = latest_evaluations(db, assets)
    buys = sorted((ev for ev in evaluations.values() if ev.verdict == "comprar"), key=lambda ev: -ev.score)
    return [asset_row(assets[ev.asset_id], ev) for ev in buys[:limit]]


def _current_evaluation(db: Session, asset: Asset) -> Evaluation:
    """Avaliação mais recente; se o ativo nunca foi avaliado (recém-cadastrado), avalia agora."""
    ev = latest_evaluation(db, asset.id)
    if ev is not None:
        return ev
    save_evaluation(db, asset, evaluate_asset(db, asset))
    db.commit()
    return db.scalars(select(Evaluation).where(Evaluation.asset_id == asset.id).order_by(Evaluation.date.desc())).one()


def _risks(asset: Asset, rules: list[RuleResult]) -> list[str]:
    failed = [f"{r.label}: {r.explanation}" for r in rules if r.status == "fail"]
    warned = [f"{r.label}: {r.explanation}" for r in rules if r.status == "warn"][:MAX_WARN_RISKS]
    sector = [SECTOR_RISKS[asset.sector]] if asset.sector in SECTOR_RISKS else []
    return failed + warned + sector


def _balance_source(fund: Fundamental | None) -> str | None:
    if fund is None:
        return None
    published = f" (publicado em {fund.published_at:%d/%m/%Y})" if fund.published_at else ""
    return f"CVM, DFP {fund.year}{published}"


def _data_sources(db: Session, asset: Asset, ev: Evaluation) -> dict[str, str | None]:
    last_fund = db.scalar(select(Fundamental).where(Fundamental.asset_id == asset.id).order_by(Fundamental.year.desc()).limit(1))
    last_div = db.scalar(select(func.max(Dividend.ex_date)).where(Dividend.asset_id == asset.id))
    quote = f"{asset.price_source or '—'} em {asset.last_price_at:%d/%m/%Y %H:%M}" if asset.last_price_at else None
    return {
        "Cotação": quote,
        "Balanços": _balance_source(last_fund),
        "Proventos": f"Yahoo Finance, último em {last_div:%d/%m/%Y}" if last_div else None,
        "Avaliação": f"motor {ev.engine_version} em {ev.date:%d/%m/%Y}",
    }


def asset_detail(db: Session, ticker: str) -> AssetDetail:
    asset = get_asset(db, ticker)
    ev = _current_evaluation(db, asset)
    rules = [RuleResult(**r) for r in ev.rules]
    return AssetDetail(
        **asset_row(asset, ev, _avg_volume(db, asset.id)).model_dump(),
        summary=ev.summary,
        rules=rules,
        extras=ev.extras or {},
        economic_group=asset.economic_group,
        data_sources=_data_sources(db, asset, ev),
        risks=_risks(asset, rules),
    )


def _weekly_prices(db: Session, asset_id: int, start: date) -> list[PricePointOut]:
    """Um ponto a cada 5 pregões (≈ semanal) e sempre o último, para o gráfico."""
    prices = db.execute(
        select(PriceDaily.date, PriceDaily.close)
        .where(PriceDaily.asset_id == asset_id, PriceDaily.date >= start)
        .order_by(PriceDaily.date)
    ).all()
    last = len(prices) - 1
    return [PricePointOut(date=p.date, close=p.close) for i, p in enumerate(prices) if i % CHART_EVERY_N_DAYS == 0 or i == last]


def _dividends_by_year(db: Session, asset_id: int, since: date) -> list[DividendYearOut]:
    """Proventos por ano com o dividend yield sobre o preço médio daquele ano."""
    totals: dict[int, float] = defaultdict(float)
    for d in db.scalars(select(Dividend).where(Dividend.asset_id == asset_id, Dividend.ex_date >= since)):
        totals[d.ex_date.year] += d.amount
    closes: dict[int, list[float]] = defaultdict(list)
    for p in db.execute(
        select(PriceDaily.date, PriceDaily.close).where(PriceDaily.asset_id == asset_id, PriceDaily.date >= since)
    ):
        closes[p.date.year].append(p.close)
    return [
        DividendYearOut(year=y, amount=v, dividend_yield=v / mean(closes[y]) if closes.get(y) else None)
        for y, v in sorted(totals.items())
    ]


def asset_history(db: Session, ticker: str, years: int) -> AssetHistory:
    """Preços dos últimos `years` anos; proventos desde cinco anos antes disso, para comparar ciclos."""
    asset = get_asset(db, ticker)
    start = date.today() - timedelta(days=365 * years)
    scores = db.scalars(select(Evaluation).where(Evaluation.asset_id == asset.id).order_by(Evaluation.date))
    return AssetHistory(
        prices=_weekly_prices(db, asset.id, start),
        dividends_by_year=_dividends_by_year(db, asset.id, date(start.year - 5, 1, 1)),
        scores=[ScorePointOut(date=e.date, score=e.score, verdict=e.verdict) for e in scores],
    )


def create_asset(db: Session, body: AssetCreate) -> AssetRow:
    """Cadastra a ação e já dispara, em segundo plano, a coleta de balanços, preços e a avaliação dela.
    Se outra atualização estiver rodando, os dados chegam na próxima."""
    ticker = body.ticker.strip().upper()
    if db.scalar(select(Asset).where(Asset.ticker == ticker)):
        raise ConflictError("Ativo já cadastrado")
    asset = Asset(
        ticker=ticker,
        name=body.name,
        asset_class="acao",
        sector=body.sector,
        segment=body.segment,
        economic_group=body.economic_group,
        active=True,
    )
    db.add(asset)
    db.commit()
    start_background_sync(NEW_ASSET_SYNC_STEPS, {ticker})
    return asset_row(asset, None)

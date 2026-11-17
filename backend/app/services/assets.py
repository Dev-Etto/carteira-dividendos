"""Universo de ativos: listagem com a avaliação do dia, ficha completa, histórico e cadastro."""

from collections import defaultdict
from datetime import date, timedelta
from itertools import chain, zip_longest
from statistics import mean

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import BusinessRuleError, ConflictError, NotFoundError
from app.db.models import Asset, Dividend, EtfReport, Evaluation, FiiQuarterlyReport, FiiReport, Fundamental, PriceDaily
from app.engine.types import RuleResult
from app.schemas.api import (
    AssetCreate,
    AssetDetail,
    AssetHistory,
    AssetRow,
    AssetUpdate,
    DividendYearOut,
    PricePointOut,
    ScorePointOut,
)
from app.services.evaluation import EVALUATED_CLASSES, evaluate_asset, latest_evaluation, latest_evaluations, save_evaluation
from app.services.sync import start_background_sync

SECTOR_RISKS = {
    "bancos": "Bancos sofrem com aumento da inadimplência em crises e com mudanças de regulação do Banco Central.",
    "seguros": "Seguradoras dependem de juros altos para a receita financeira; quando a Selic cai, o lucro tende a cair.",
    "energia": "Empresas de energia dependem de regras do governo (ANEEL), de chuvas e da renovação das concessões.",
    "saneamento": "Saneamento depende de revisões tarifárias e de decisões políticas dos estados e municípios.",
    "telecom": "Telecom exige investimentos altos e constantes em rede, e a concorrência pressiona preços.",
    "ciclico": "Setor cíclico: lucro e dividendos podem cair muito quando a economia ou o preço das commodities cai.",
    "perene": "Mesmo setores estáveis enfrentam concorrência e mudanças de hábito dos consumidores.",
    "etf": "Um ETF acompanha o índice para cima e para baixo: o risco é o do mercado que ele replica, sem proteção na queda.",
}
FII_KIND_RISKS = {
    "papel": "FIIs de papel dependem de os devedores pagarem os CRIs em dia; o rendimento também cai quando o CDI ou o IPCA caem.",
    "tijolo": "FIIs de tijolo sofrem com vacância e inquilinos inadimplentes; com juros altos, as cotas tendem a cair.",
    "fof": "Fundos de fundos somam a taxa deles à dos fundos que compram, e o resultado depende das vendas de cotas.",
    "hibrido": "Fundos híbridos misturam os riscos de crédito (CRIs) e de imóveis (vacância e inadimplência).",
}
VERDICT_ORDER = {"comprar": 0, "aguardar": 1, "neutro": 2, "evitar": 3}
VOLUME_WINDOW_DAYS = 63
VOLUME_MIN_DAYS = 20
MAX_WARN_RISKS = 3
CHART_EVERY_N_DAYS = 5
NEW_ASSET_SYNC_STEPS = {
    "acao": {"cvm", "mercado", "avaliacoes"},
    "fii": {"fiis", "mercado", "avaliacoes"},
    "etf": {"etfs", "mercado", "avaliacoes"},
}
NEW_ASSET_SECTOR = {"fii": "hibrido", "etf": "etf"}
"""Grupo de um ativo novo sem setor: o FII fica híbrido até o informe da CVM dizer se é papel ou tijolo."""


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
        favorite=bool(asset.favorite),
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
    """Ações e FIIs com veredito "comprar", intercalando as classes (a melhor ação, o melhor FII, a
    segunda ação...) para uma não esconder a outra; dentro de cada classe, da maior nota para a menor."""
    assets = {a.id: a for a in db.scalars(select(Asset).where(Asset.active, Asset.asset_class.in_(EVALUATED_CLASSES)))}
    evaluations = latest_evaluations(db, assets)
    buys = sorted((ev for ev in evaluations.values() if ev.verdict == "comprar"), key=lambda ev: -ev.score)
    by_class = [[ev for ev in buys if assets[ev.asset_id].asset_class == cls] for cls in EVALUATED_CLASSES]
    interleaved = [ev for ev in chain.from_iterable(zip_longest(*by_class)) if ev is not None]
    return [asset_row(assets[ev.asset_id], ev) for ev in interleaved[:limit]]


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
    risks = FII_KIND_RISKS if asset.asset_class == "fii" else SECTOR_RISKS
    sector = [risks[asset.sector]] if asset.sector in risks else []
    return failed + warned + sector


def _balance_source(fund: Fundamental | None) -> str | None:
    if fund is None:
        return None
    published = f" (publicado em {fund.published_at:%d/%m/%Y})" if fund.published_at else ""
    return f"CVM, DFP {fund.year}{published}"


def _fii_sources(db: Session, asset: Asset) -> dict[str, str | None]:
    monthly = db.scalar(select(func.max(FiiReport.ref_date)).where(FiiReport.asset_id == asset.id))
    quarterly = db.scalar(select(func.max(FiiQuarterlyReport.ref_date)).where(FiiQuarterlyReport.asset_id == asset.id))
    return {
        "Informe mensal": f"CVM, referência {monthly:%m/%Y}" if monthly else None,
        "Informe trimestral": f"CVM, trimestre encerrado em {quarterly:%d/%m/%Y}" if quarterly else None,
    }


def _etf_sources(db: Session, asset: Asset) -> dict[str, str | None]:
    day = db.scalar(select(func.max(EtfReport.ref_date)).where(EtfReport.asset_id == asset.id))
    fee = "informada por você" if asset.admin_fee is not None else None
    return {"Patrimônio": f"CVM, cadastro de fundos em {day:%d/%m/%Y}" if day else None, "Taxa de administração": fee}


def _stock_sources(db: Session, asset: Asset) -> dict[str, str | None]:
    last_fund = db.scalar(select(Fundamental).where(Fundamental.asset_id == asset.id).order_by(Fundamental.year.desc()).limit(1))
    return {"Balanços": _balance_source(last_fund)}


def _data_sources(db: Session, asset: Asset, ev: Evaluation) -> dict[str, str | None]:
    last_div = db.scalar(select(func.max(Dividend.ex_date)).where(Dividend.asset_id == asset.id))
    quote = f"{asset.price_source or '—'} em {asset.last_price_at:%d/%m/%Y %H:%M}" if asset.last_price_at else None
    sources = {"fii": _fii_sources, "etf": _etf_sources}.get(asset.asset_class, _stock_sources)
    reports = sources(db, asset)
    return {
        "Cotação": quote,
        **reports,
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


def _nav_history(db: Session, asset_id: int, start: date) -> list[PricePointOut]:
    reports = db.execute(
        select(FiiReport.ref_date, FiiReport.nav_per_share)
        .where(FiiReport.asset_id == asset_id, FiiReport.ref_date >= start, FiiReport.nav_per_share.is_not(None))
        .order_by(FiiReport.ref_date)
    ).all()
    return [PricePointOut(date=r.ref_date, close=r.nav_per_share) for r in reports]


def asset_history(db: Session, ticker: str, years: int) -> AssetHistory:
    """Preços dos últimos `years` anos; proventos desde cinco anos antes disso, para comparar ciclos.
    Em FIIs, também o valor patrimonial da cota mês a mês."""
    asset = get_asset(db, ticker)
    start = date.today() - timedelta(days=365 * years)
    scores = db.scalars(select(Evaluation).where(Evaluation.asset_id == asset.id).order_by(Evaluation.date))
    return AssetHistory(
        prices=_weekly_prices(db, asset.id, start),
        dividends_by_year=_dividends_by_year(db, asset.id, date(start.year - 5, 1, 1)),
        scores=[ScorePointOut(date=e.date, score=e.score, verdict=e.verdict) for e in scores],
        nav=_nav_history(db, asset.id, start),
    )


def create_asset(db: Session, body: AssetCreate) -> AssetRow:
    """Cadastra a ação ou o FII e já dispara, em segundo plano, a coleta dos dados dele (balanços ou
    informes da CVM, preços) e a avaliação. Se outra atualização estiver rodando, os dados chegam na próxima."""
    ticker = body.ticker.strip().upper()
    if db.scalar(select(Asset).where(Asset.ticker == ticker)):
        raise ConflictError("Ativo já cadastrado")
    asset = Asset(
        ticker=ticker,
        name=body.name,
        asset_class=body.asset_class,
        sector=body.sector or NEW_ASSET_SECTOR[body.asset_class],
        segment=body.segment,
        economic_group=body.economic_group,
        active=True,
    )
    db.add(asset)
    db.commit()
    start_background_sync(NEW_ASSET_SYNC_STEPS[body.asset_class], {ticker})
    return asset_row(asset, None)


def update_asset(db: Session, ticker: str, body: AssetUpdate) -> AssetDetail:
    """Marca o ETF como favorito e/ou guarda a taxa informada; mudar a taxa já reavalia o ETF."""
    asset = get_asset(db, ticker)
    if asset.asset_class != "etf":
        raise BusinessRuleError("Favorito e taxa de administração só valem para ETFs")
    changes = body.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(asset, field, value)
    db.commit()
    if "admin_fee" in changes:
        save_evaluation(db, asset, evaluate_asset(db, asset))
        db.commit()
    return asset_detail(db, ticker)

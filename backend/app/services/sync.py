"""Orquestra a coleta. Ordem: universo → macro → Tesouro → CVM (ações) → CVM (FIIs) → CVM (ETFs) → cotações/histórico → avaliações.

Cada etapa é registrada em sync_runs. Uma etapa que falha não impede as outras.
Só roda um sync por vez: `_lock` garante isso e também responde à tela de Configurações se há um rodando.
"""

import asyncio
import csv
import logging
import threading
from collections.abc import Awaitable, Callable
from datetime import date, datetime, timedelta
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import BusinessRuleError
from app.db.models import (
    Asset,
    Dividend,
    EtfReport,
    FiiQuarterlyReport,
    FiiReport,
    Filing,
    Fundamental,
    MacroRate,
    PriceDaily,
    QuarterlyFundamental,
    SectorMetric,
    Split,
    SyncRun,
    TreasuryBond,
)
from app.db.session import SessionLocal
from app.engine import fii
from app.providers import bcb, bcb_ifdata, cvm, cvm_etf, cvm_fii, cvm_ipe, market, tesouro
from app.providers.base import DOWNLOAD_ERRORS, DividendEvent, PricePoint, Quote, SplitInfo
from app.schemas.api import SyncRunOut, SyncStatus
from app.services.evaluation import evaluate_all
from app.services.upsert import upsert

log = logging.getLogger("sync")
DATA_DIR = Path(__file__).resolve().parents[1] / "data"

FUNDAMENTAL_FIELDS = (
    "revenue",
    "ebit",
    "depreciation",
    "net_income",
    "equity",
    "gross_debt",
    "cash",
    "operating_cash_flow",
    "investing_cash_flow",
    "dividends_paid",
    "current_assets",
    "current_liabilities",
    "short_term_debt",
    "fixed_assets",
)

INCREMENTAL_OVERLAP_DAYS = 10
MarketHistory = tuple[list[PricePoint], list[DividendEvent], list[SplitInfo], float | None]

FII_REPORT_FIELDS = (
    "equity",
    "shares",
    "nav_per_share",
    "holders",
    "admin_fee",
    "paper",
    "brick",
    "fof",
    "cash",
    "started_on",
    "listed",
)
FII_QUARTERLY_FIELDS = ("properties", "vacancy", "largest_property_share", "largest_credit_value")
ASSET_FIELDS = ["name", "asset_class", "sector", "segment", "economic_group"]
FII_SEED_FIELDS = ["name", "asset_class", "economic_group"]
"""Num FII, tipo (sector) e segmento vêm do informe da CVM; o universo.csv só dá o palpite inicial."""

STEPS = ("universo", "macro", "tesouro", "cvm", "itr", "bancos", "comunicados", "fiis", "etfs", "mercado", "avaliacoes")

_lock = threading.Lock()
_current_step: str | None = None


def parse_steps(etapas: str | None) -> set[str] | None:
    """Converte "macro,cvm" no conjunto de etapas; vazio significa todas."""
    only = {e.strip() for e in (etapas or "").split(",") if e.strip()}
    unknown = only - set(STEPS)
    if unknown:
        raise BusinessRuleError(f"Etapas desconhecidas: {sorted(unknown)}. Use: {', '.join(STEPS)}")
    return only or None


def sync_status(db: Session) -> SyncStatus:
    runs = db.scalars(select(SyncRun).order_by(SyncRun.id.desc()).limit(12)).all()
    return SyncStatus(running=is_running(), step=current_step(), runs=[SyncRunOut.model_validate(r) for r in runs])


def needs_initial_sync(db: Session) -> bool:
    """Verdadeiro quando nenhuma atualização de dados foi feita ainda (banco recém-criado)."""
    return db.scalar(select(SyncRun.id).limit(1)) is None


def is_running() -> bool:
    return _lock.locked()


def current_step() -> str | None:
    return _current_step


async def _step(db: Session, name: str, fn: Callable[[], Awaitable[int]]) -> None:
    run = SyncRun(source=name, started_at=datetime.now(), status="running")
    db.add(run)
    db.commit()
    global _current_step
    _current_step = name
    try:
        run.rows = await fn()
        run.status = "ok"
        db.commit()
    except Exception as e:
        db.rollback()
        log.exception("falha na etapa %s", name)
        run.status = "error"
        run.error = f"{type(e).__name__}: {e}"[:2000]
    run.finished_at = datetime.now()
    db.commit()


def seed_universe(db: Session) -> int:
    n = 0
    with open(DATA_DIR / "universo.csv", encoding="utf-8") as f:
        rows = [
            {
                "ticker": r["ticker"].strip().upper(),
                "name": r["nome"].strip(),
                "asset_class": r["classe"].strip(),
                "sector": r["setor"].strip(),
                "segment": r["segmento"].strip() or None,
                "economic_group": r["grupo"].strip() or None,
                "region": (r.get("regiao") or "").strip() or "nacional",
                "active": True,
            }
            for r in csv.DictReader(f)
            if r.get("ticker")
        ]
    stocks = [r for r in rows if r["asset_class"] != "fii"]
    funds = [r for r in rows if r["asset_class"] == "fii"]
    n += upsert(db, Asset, stocks, keys=["ticker"], update=ASSET_FIELDS)
    n += upsert(db, Asset, funds, keys=["ticker"], update=FII_SEED_FIELDS)
    db.commit()
    return n


def load_sector_metrics(db: Session) -> int:
    path = DATA_DIR / "sector_metrics.csv"
    if not path.exists():
        return 0
    tickers = {a.ticker: a.id for a in db.scalars(select(Asset))}
    rows = []
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            aid = tickers.get((r.get("ticker") or "").strip().upper())
            if not aid or not r.get("valor"):
                continue
            rows.append(
                {
                    "asset_id": aid,
                    "key": r["chave"].strip(),
                    "value": float(r["valor"].replace(",", ".")),
                    "reference": (r.get("referencia") or "").strip() or None,
                    "source": (r.get("fonte") or "manual").strip(),
                    "updated_at": date.today(),
                }
            )
    n = upsert(db, SectorMetric, rows, keys=["asset_id", "key"], update=["value", "reference", "source", "updated_at"])
    db.commit()
    return n


async def sync_macro(db: Session) -> int:
    total = 0
    for name in bcb.SERIES:
        points = await bcb.fetch_series(name)
        total += upsert(
            db, MacroRate, [{"series": name, "date": d, "value": v} for d, v in points], keys=["series", "date"], update=["value"]
        )
    db.commit()
    return total


async def sync_treasury(db: Session) -> int:
    bonds = await tesouro.fetch_bonds()
    rows = [b.__dict__ for b in bonds]
    n = upsert(
        db, TreasuryBond, rows, keys=["name", "maturity", "date"], update=["buy_rate", "sell_rate", "buy_price", "sell_price"]
    )
    db.commit()
    return n


async def sync_cvm(db: Session) -> int:
    today = date.today()
    assets = list(db.scalars(select(Asset).where(Asset.asset_class == "acao")))
    mapping = await cvm.fetch_ticker_map(today.year)
    for a in assets:
        if a.ticker in mapping:
            a.cnpj = mapping[a.ticker]
    db.commit()
    by_cnpj: dict[str, list[Asset]] = {}
    for a in assets:
        if a.cnpj:
            by_cnpj.setdefault(a.cnpj, []).append(a)
    total = 0
    years = range(today.year - get_settings().cvm_years, today.year)
    for year in years:
        try:
            statements = await cvm.fetch_dfp(year, set(by_cnpj))
        except DOWNLOAD_ERRORS:
            log.warning("DFP %s indisponível", year)
            continue
        rows = [
            {"asset_id": a.id, "year": year, "published_at": st.published_at, "source": "cvm"}
            | {k: st.values.get(k) for k in FUNDAMENTAL_FIELDS}
            for cnpj, st in statements.items()
            for a in by_cnpj[cnpj]
        ]
        total += upsert(
            db,
            Fundamental,
            rows,
            keys=["asset_id", "year"],
            update=["published_at", "source", *FUNDAMENTAL_FIELDS],
        )
        db.commit()
    return total


QUARTER_FIELDS = ("revenue", "ebit", "net_income", "equity", "gross_debt", "cash")


def _fourth_quarters(db: Session, year: int) -> list[dict[str, object]]:
    """4º trimestre de cada ação que tem o ano na DFP e os três primeiros trimestres no ITR."""
    quarters: dict[int, list[QuarterlyFundamental]] = {}
    for q in db.scalars(select(QuarterlyFundamental).where(QuarterlyFundamental.year == year, QuarterlyFundamental.quarter < 4)):
        quarters.setdefault(q.asset_id, []).append(q)
    complete = {aid: qs for aid, qs in quarters.items() if len(qs) == 3}
    annuals = db.scalars(select(Fundamental).where(Fundamental.year == year, Fundamental.asset_id.in_(complete)))
    return [
        {"asset_id": f.asset_id, "year": year, "quarter": 4, "period_end": date(year, 12, 31), "source": "dfp-itr"}
        | dict.fromkeys(QUARTER_FIELDS)
        | cvm.fourth_quarter(
            {k: v for k in QUARTER_FIELDS if (v := getattr(f, k)) is not None},
            [{k: v for k in QUARTER_FIELDS if (v := getattr(q, k)) is not None} for q in complete[f.asset_id]],
        )
        for f in annuals
    ]


async def sync_itr(db: Session) -> int:
    """Trimestres do ITR dos últimos anos e o 4º trimestre calculado pela DFP. Precisa do CNPJ que a etapa
    cvm grava."""
    assets = list(db.scalars(select(Asset).where(Asset.asset_class == "acao", Asset.cnpj.is_not(None))))
    by_cnpj: dict[str, list[Asset]] = {}
    for a in assets:
        by_cnpj.setdefault(a.cnpj or "", []).append(a)
    today = date.today()
    total = 0
    for year in range(today.year - get_settings().itr_years + 1, today.year + 1):
        try:
            statements = await cvm.fetch_itr(year, set(by_cnpj))
        except DOWNLOAD_ERRORS:
            log.warning("ITR %s indisponível", year)
            continue
        rows = [
            {"asset_id": a.id, "year": st.year, "quarter": st.quarter, "period_end": st.period_end, "source": "itr"}
            | {k: st.values.get(k) for k in QUARTER_FIELDS}
            for st in statements
            for a in by_cnpj[st.cnpj]
        ]
        keys = ["asset_id", "year", "quarter"]
        update = ["period_end", "source", *QUARTER_FIELDS]
        total += upsert(db, QuarterlyFundamental, rows, keys=keys, update=update)
        db.commit()
        total += upsert(db, QuarterlyFundamental, _fourth_quarters(db, year), keys=keys, update=update)
        db.commit()
    return total


FILING_YEARS = 2
"""Ano atual e o anterior: em janeiro, o arquivo do ano ainda tem poucos comunicados."""


async def sync_filings(db: Session) -> int:
    """Comunicados (IPE) das ações com CNPJ, gravados por ativo e protocolo."""
    assets = list(db.scalars(select(Asset).where(Asset.asset_class == "acao", Asset.cnpj.is_not(None))))
    by_cnpj: dict[str, list[Asset]] = {}
    for a in assets:
        by_cnpj.setdefault(a.cnpj or "", []).append(a)
    total = 0
    today = date.today()
    for year in range(today.year - FILING_YEARS + 1, today.year + 1):
        try:
            filings = await cvm_ipe.fetch_filings(year, set(by_cnpj))
        except DOWNLOAD_ERRORS:
            log.warning("IPE %s indisponível", year)
            continue
        rows = [
            {
                "asset_id": a.id,
                "protocol": f.protocol,
                "delivered_on": f.delivered_on,
                "category": f.category,
                "kind": f.kind[:120],
                "subject": f.subject,
                "link": f.link,
            }
            for f in filings
            for a in by_cnpj[f.cnpj]
        ]
        total += upsert(
            db, Filing, rows, keys=["asset_id", "protocol"], update=["delivered_on", "category", "kind", "subject", "link"]
        )
        db.commit()
    return total


CNPJ_ROOT_DIGITS = 8


def _pick_basel(found: list[bcb_ifdata.Basel], root: str) -> bcb_ifdata.Basel | None:
    """Conglomerado prudencial do banco pela raiz do CNPJ; havendo mais de um, o de nome "prudencial"."""
    matches = sorted((b for b in found if b.cnpj_root == root), key=lambda b: "PRUDENCIAL" not in b.institution)
    return matches[0] if matches else None


async def sync_banks(db: Session) -> int:
    """Índice de Basileia dos bancos pelo IF.data do Banco Central. Substitui o valor manual do CSV, que
    continua valendo para quem o IF.data não cobre (holdings como a Itaúsa)."""
    banks = list(db.scalars(select(Asset).where(Asset.sector == "bancos", Asset.cnpj.is_not(None))))
    if not banks:
        return 0
    found = await bcb_ifdata.fetch_basel()
    rows = [
        {
            "asset_id": a.id,
            "key": "basileia",
            "value": b.ratio_pct,
            "reference": b.reference,
            "source": "BCB IF.data",
            "updated_at": date.today(),
        }
        for a in banks
        if (b := _pick_basel(found, (a.cnpj or "")[:CNPJ_ROOT_DIGITS])) is not None
    ]
    n = upsert(db, SectorMetric, rows, keys=["asset_id", "key"], update=["value", "reference", "source", "updated_at"])
    db.commit()
    return n


async def _fii_monthly(year: int, tickers: set[str]) -> dict[str, list[cvm_fii.FiiMonthly]]:
    try:
        return await cvm_fii.fetch_monthly(year, tickers)
    except DOWNLOAD_ERRORS:
        log.warning("informe mensal de FII %s indisponível", year)
        return {}


async def _fii_quarterly(year: int, cnpjs: set[str]) -> dict[str, cvm_fii.FiiQuarterly]:
    try:
        return await cvm_fii.fetch_quarterly(year, cnpjs)
    except DOWNLOAD_ERRORS:
        log.warning("informe trimestral de FII %s indisponível", year)
        return {}


def _apply_fii_report(asset: Asset, history: list[cvm_fii.FiiMonthly]) -> list[dict[str, object]]:
    """Atualiza CNPJ, tipo e segmento pelo informe mais recente e devolve as linhas de fii_reports."""
    latest = max(history, key=lambda r: r.ref_date)
    asset.cnpj = latest.cnpj
    asset.sector = fii.classify(latest.paper, latest.brick, latest.fof)
    asset.segment = latest.segment
    return [
        {"asset_id": asset.id, "ref_date": r.ref_date} | {k: getattr(r, k) for k in FII_REPORT_FIELDS}
        for r in history
        if r.cnpj == latest.cnpj
    ]


async def _sync_fii_quarterly(db: Session, assets: list[Asset], today: date) -> int:
    """Informe trimestral do ano corrente; quem ainda não tem, tenta o do ano anterior (começo de ano)."""
    by_cnpj = {a.cnpj: a for a in assets if a.cnpj}
    found: dict[str, cvm_fii.FiiQuarterly] = {}
    for year in (today.year, today.year - 1):
        missing = set(by_cnpj) - set(found)
        if missing:
            found |= await _fii_quarterly(year, missing)
    rows = [
        {"asset_id": by_cnpj[cnpj].id, "ref_date": q.ref_date} | {k: getattr(q, k) for k in FII_QUARTERLY_FIELDS}
        for cnpj, q in found.items()
    ]
    n = upsert(db, FiiQuarterlyReport, rows, keys=["asset_id", "ref_date"], update=list(FII_QUARTERLY_FIELDS))
    db.commit()
    return n


async def sync_fii(db: Session) -> int:
    """Informes mensais dos FIIs do universo (ano anterior e corrente) e o trimestral mais recente."""
    today = date.today()
    assets = {a.ticker: a for a in db.scalars(select(Asset).where(Asset.asset_class == "fii"))}
    if not assets:
        return 0
    history: dict[str, list[cvm_fii.FiiMonthly]] = {}
    for year in (today.year - 1, today.year):
        for ticker, reports in (await _fii_monthly(year, set(assets))).items():
            history.setdefault(ticker, []).extend(reports)
    rows = [row for ticker, reports in history.items() for row in _apply_fii_report(assets[ticker], reports)]
    n = upsert(db, FiiReport, rows, keys=["asset_id", "ref_date"], update=list(FII_REPORT_FIELDS))
    db.commit()
    return n + await _sync_fii_quarterly(db, list(assets.values()), today)


async def _etf_fund(
    asset: Asset, by_name: dict[str, cvm_etf.IndexFund], by_cnpj: dict[str, cvm_etf.IndexFund]
) -> cvm_etf.IndexFund | None:
    """Fundo da CVM do ETF: pelo CNPJ já conhecido ou, na primeira vez, pelo nome que o Yahoo mostra."""
    known = by_cnpj.get(asset.cnpj or "")
    if known is not None:
        return known
    long_name = await market.yahoo_long_name(asset.ticker)
    return by_name.get(cvm_etf.name_key(long_name or asset.name))


async def sync_etf(db: Session) -> int:
    """Patrimônio dos ETFs do universo no cadastro de fundos da CVM."""
    assets = list(db.scalars(select(Asset).where(Asset.asset_class == "etf")))
    if not assets:
        return 0
    by_name = await cvm_etf.fetch_index_funds()
    by_cnpj = {fund.cnpj: fund for fund in by_name.values()}
    rows = []
    for asset in assets:
        fund = await _etf_fund(asset, by_name, by_cnpj)
        if fund is None:
            log.warning("ETF %s não encontrado no cadastro da CVM", asset.ticker)
            continue
        asset.cnpj = fund.cnpj
        rows.append({"asset_id": asset.id, "ref_date": fund.equity_date or date.today(), "equity": fund.equity})
    n = upsert(db, EtfReport, rows, keys=["asset_id", "ref_date"], update=["equity"])
    db.commit()
    return n


async def _history(db: Session, asset: Asset) -> MarketHistory:
    """Histórico incremental (últimos dias). O Yahoo reajusta todo o histórico depois de um desdobramento;
    quando aparece um no trecho novo, apaga o que havia e baixa tudo de novo."""
    last = db.scalar(select(func.max(PriceDaily.date)).where(PriceDaily.asset_id == asset.id))
    start = last - timedelta(days=INCREMENTAL_OVERLAP_DAYS) if last else None
    history = await market.yahoo_history(asset.ticker, start)
    _, _, new_splits, _ = history
    if not (start and new_splits):
        return history
    db.query(PriceDaily).filter(PriceDaily.asset_id == asset.id).delete()
    db.query(Dividend).filter(Dividend.asset_id == asset.id, Dividend.source == "yahoo").delete()
    return await market.yahoo_history(asset.ticker, None)


def _store_history(db: Session, asset: Asset, history: MarketHistory) -> int:
    prices, divs, splits, shares = history
    stored = upsert(
        db,
        PriceDaily,
        [{"asset_id": asset.id, "date": p.date, "close": p.close, "volume": p.volume, "source": "yahoo"} for p in prices],
        keys=["asset_id", "date"],
        update=["close", "volume"],
    )
    upsert(
        db,
        Dividend,
        [{"asset_id": asset.id, "ex_date": d.ex_date, "amount": d.amount, "kind": d.kind, "source": "yahoo"} for d in divs],
        keys=["asset_id", "ex_date", "kind", "amount"],
    )
    upsert(
        db,
        Split,
        [{"asset_id": asset.id, "date": s.date, "ratio": s.ratio, "source": "yahoo"} for s in splits],
        keys=["asset_id", "date"],
    )
    asset.shares_outstanding = shares or asset.shares_outstanding
    if prices:
        asset.last_price, asset.last_price_at, asset.price_source = prices[-1].close, datetime.now(), "yahoo"
    return stored


def _apply_quote(asset: Asset, quote: Quote) -> None:
    """A cotação da brapi é mais fresca que o fechamento do Yahoo e traz o valor de mercado e o nome."""
    asset.last_price, asset.last_price_at, asset.price_source = quote.price, datetime.now(), "brapi"
    if quote.market_cap and quote.price:
        asset.shares_outstanding = quote.market_cap / quote.price
    if quote.name and asset.name == asset.ticker:
        asset.name = quote.name


async def _sync_asset_market(db: Session, asset: Asset) -> int:
    stored = _store_history(db, asset, await _history(db, asset))
    quote = await market.brapi_quote(asset.ticker)
    if quote:
        _apply_quote(asset, quote)
    db.commit()
    return stored


async def sync_market(db: Session, tickers: set[str] | None = None) -> int:
    """Preços, proventos e desdobramentos de cada ativo. A falha de um ativo é registrada e não para os outros."""
    total = 0
    query = select(Asset).where(Asset.active)
    if tickers:
        query = query.where(Asset.ticker.in_(tickers))
    for asset in list(db.scalars(query)):
        try:
            total += await _sync_asset_market(db, asset)
        except Exception:
            db.rollback()
            log.exception("falha ao atualizar %s", asset.ticker)
    return total


async def _run_steps(db: Session, only: set[str] | None, tickers: set[str] | None = None) -> None:
    global _current_step
    steps: dict[str, Callable[[], Awaitable[int]]] = {
        "universo": lambda: _sync_wrap(seed_universe(db) + load_sector_metrics(db)),
        "macro": lambda: sync_macro(db),
        "tesouro": lambda: sync_treasury(db),
        "cvm": lambda: sync_cvm(db),
        "itr": lambda: sync_itr(db),
        "comunicados": lambda: sync_filings(db),
        "bancos": lambda: sync_banks(db),
        "fiis": lambda: sync_fii(db),
        "etfs": lambda: sync_etf(db),
        "mercado": lambda: sync_market(db, tickers),
        "avaliacoes": lambda: _sync_wrap(evaluate_all(db)),
    }
    try:
        for name in STEPS:
            if not only or name in only:
                await _step(db, name, steps[name])
    finally:
        _current_step = None


async def run_full_sync(db: Session, only: set[str] | None = None, tickers: set[str] | None = None) -> bool:
    """Roda a coleta no event loop atual (CLI e testes). Devolve False se já havia um sync rodando."""
    if not _lock.acquire(blocking=False):
        return False
    try:
        await _run_steps(db, only, tickers)
    finally:
        _lock.release()
    return True


def _run_in_thread(only: set[str] | None, tickers: set[str] | None) -> None:
    """Corpo da thread de sync. O lock já foi adquirido por start_background_sync e é liberado aqui, no fim."""
    db = SessionLocal()
    try:
        asyncio.run(_run_steps(db, only, tickers))
    except Exception:
        log.exception("sync em segundo plano falhou")
    finally:
        db.close()
        _lock.release()


def start_background_sync(only: set[str] | None = None, tickers: set[str] | None = None) -> bool:
    """Dispara a coleta numa thread com event loop próprio, para o parse da CVM e as avaliações
    (CPU e SQLite síncronos) não travarem a API. Devolve False se já havia um sync rodando."""
    if not _lock.acquire(blocking=False):
        return False
    try:
        threading.Thread(target=_run_in_thread, args=(only, tickers), name="sync", daemon=True).start()
    except Exception:
        _lock.release()
        raise
    return True


async def _sync_wrap(n: int) -> int:
    return n

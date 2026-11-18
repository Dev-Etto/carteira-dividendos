"""Orquestração da coleta (services/sync) com providers falsos e banco próprio."""

import threading
from collections.abc import Iterator
from datetime import date, datetime, timedelta

import httpx
import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import (
    Asset,
    Base,
    Dividend,
    EtfReport,
    Evaluation,
    FiiQuarterlyReport,
    FiiReport,
    Fundamental,
    MacroRate,
    PriceDaily,
    QuarterlyFundamental,
    SectorMetric,
    SyncRun,
    TreasuryBond,
)
from app.db.models import Filing as FilingRow
from app.providers.b3 import CashDividend
from app.providers.base import DividendEvent, PricePoint, SplitInfo
from app.providers.bcb_ifdata import Basel, Overdue, OverdueReport
from app.providers.cvm import AnnualStatement, QuarterStatement
from app.providers.cvm_etf import IndexFund, name_key
from app.providers.cvm_fii import FiiMonthly, FiiQuarterly
from app.providers.cvm_ipe import Filing
from app.providers.tesouro import BondQuote
from app.services import sync
from app.services.snapshot import build_stock_snapshot

TODAY = date.today()
TAEE_CNPJ = "07859971000130"
KNCR_CNPJ = "16706958000132"
HGLG_CNPJ = "11728688000147"


def informe(cnpj: str, ticker: str, month: int, **kw) -> FiiMonthly:
    base = {
        "cnpj": cnpj,
        "ref_date": date(TODAY.year, month, 1),
        "ticker": ticker,
        "name": ticker,
        "started_on": date(2012, 1, 1),
        "listed": True,
        "segment": "Multicategoria",
        "holders": 500_000,
        "equity": 10e9,
        "shares": 1e8,
        "nav_per_share": 100.0,
        "admin_fee": 0.0008,
        "paper": 0.8,
        "brick": 0.0,
        "fof": 0.1,
        "cash": 0.1,
    }
    return FiiMonthly(**(base | kw))


@pytest.fixture
def session_factory(tmp_path) -> sessionmaker[Session]:
    engine = create_engine(f"sqlite:///{tmp_path / 'sync.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture
def db(session_factory) -> Iterator[Session]:
    with session_factory() as s:
        sync.seed_universe(s)
        yield s


class FakeYahoo:
    """Histórico falso. Registra as chamadas para conferir a recarga após desdobramento."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, date | None]] = []
        self.splits: list[SplitInfo] = []

    async def __call__(
        self, ticker: str, start: date | None = None
    ) -> tuple[list[PricePoint], list[DividendEvent], list[SplitInfo], float | None]:
        self.calls.append((ticker, start))
        if ticker == "BBAS3":
            raise RuntimeError("yahoo fora do ar")
        prices = [PricePoint(TODAY - timedelta(days=i), 30.0, 1e6) for i in range(30)]
        divs = [DividendEvent(TODAY - timedelta(days=40), 1.0)]
        return prices, divs, (self.splits if start else []), 1e9


@pytest.fixture
def yahoo(monkeypatch) -> FakeYahoo:
    fake = FakeYahoo()

    async def fetch_series(name: str) -> list[tuple[date, float]]:
        return [(TODAY, 0.15)]

    async def fetch_bonds() -> list[BondQuote]:
        return [BondQuote("Tesouro Selic", date(TODAY.year + 3, 3, 1), TODAY, 0.0005, 0.0006, 15000.0, 14990.0)]

    async def fetch_ticker_map(year: int) -> dict[str, str]:
        return {"TAEE11": TAEE_CNPJ}

    async def fetch_dfp(year: int, cnpjs: set[str]) -> dict[str, AnnualStatement]:
        if year == TODAY.year - 1:
            raise httpx.HTTPStatusError("404", request=httpx.Request("GET", "https://cvm"), response=httpx.Response(404))
        return {TAEE_CNPJ: AnnualStatement(TAEE_CNPJ, year, None, {"net_income": 1e9, "equity": 6e9})}

    async def fetch_itr(year: int, cnpjs: set[str]) -> list[QuarterStatement]:
        ends = {1: date(year, 3, 31), 2: date(year, 6, 30), 3: date(year, 9, 30)}
        return [
            QuarterStatement(TAEE_CNPJ, year, q, end, {"net_income": 2e8, "equity": 5.5e9 + q * 1e8})
            for q, end in ends.items()
            if TAEE_CNPJ in cnpjs
        ]

    async def fetch_filings(year: int, cnpjs: set[str]) -> list[Filing]:
        fato = Filing(TAEE_CNPJ, f"P{year}", date(year, 3, 1), "fato_relevante", "Fato Relevante", "Aquisição", "https://cvm/1")
        return [fato] if TAEE_CNPJ in cnpjs else []

    async def brapi_quote(ticker: str) -> None:
        return None

    async def fetch_monthly(year: int, tickers: set[str]) -> dict[str, list[FiiMonthly]]:
        if year != TODAY.year:
            return {}
        reports = {
            "KNCR11": [informe(KNCR_CNPJ, "KNCR11", 1), informe(KNCR_CNPJ, "KNCR11", 2, nav_per_share=101.0)],
            "HGLG11": [informe(HGLG_CNPJ, "HGLG11", 1, paper=0.0, brick=0.95, fof=0.0, cash=0.05, segment="Logística")],
        }
        return {t: r for t, r in reports.items() if t in tickers}

    async def fetch_quarterly(year: int, cnpjs: set[str]) -> dict[str, FiiQuarterly]:
        if year == TODAY.year:
            raise httpx.HTTPStatusError("404", request=httpx.Request("GET", "https://cvm"), response=httpx.Response(404))
        reports = {
            KNCR_CNPJ: FiiQuarterly(KNCR_CNPJ, date(year, 12, 31), None, None, None, 400e6),
            HGLG_CNPJ: FiiQuarterly(HGLG_CNPJ, date(year, 12, 31), 30, 0.05, 0.08, None),
        }
        return {c: q for c, q in reports.items() if c in cnpjs}

    monkeypatch.setattr(sync.bcb, "fetch_series", fetch_series)
    monkeypatch.setattr(sync.tesouro, "fetch_bonds", fetch_bonds)
    monkeypatch.setattr(sync.cvm, "fetch_ticker_map", fetch_ticker_map)
    monkeypatch.setattr(sync.cvm, "fetch_dfp", fetch_dfp)
    monkeypatch.setattr(sync.cvm, "fetch_itr", fetch_itr)
    monkeypatch.setattr(sync.cvm_ipe, "fetch_filings", fetch_filings)

    async def fetch_basel() -> list[Basel]:
        return [Basel(BANK_CNPJ[:8], "BANCO - PRUDENCIAL", 15.35, "2T26"), Basel(BANK_CNPJ[:8], "BANCO", 9.0, "2T26")]

    monkeypatch.setattr(sync.bcb_ifdata, "fetch_basel", fetch_basel)

    async def fetch_overdue() -> OverdueReport:
        return OverdueReport([Overdue(BANK_CNPJ[:8], "BANCO - PRUDENCIAL", 2.96, "2T26")], 3.57, "2T26")

    monkeypatch.setattr(sync.bcb_ifdata, "fetch_overdue", fetch_overdue)

    async def fetch_cash_dividends(ticker: str) -> list[CashDividend]:
        if ticker != "TAEE11":
            return []
        return [
            CashDividend("UNT", TODAY - timedelta(days=41), 1.0, "dividendo"),
            CashDividend("UNT", TODAY - timedelta(days=20), 0.5, "jcp"),
            CashDividend("ON", TODAY - timedelta(days=20), 0.17, "jcp"),
            CashDividend("UNT", TODAY - timedelta(days=400), 2.0, "dividendo"),
        ]

    monkeypatch.setattr(sync.b3, "fetch_cash_dividends", fetch_cash_dividends)
    monkeypatch.setattr(sync.market, "yahoo_history", fake)
    monkeypatch.setattr(sync.market, "brapi_quote", brapi_quote)

    async def fetch_index_funds() -> dict[str, IndexFund]:
        fund = IndexFund("10406511000161", "ISHARES IBOVESPA CLASSE DE ÍNDICE", 18e9, date(TODAY.year, 1, 2))
        return {name_key(fund.name): fund}

    async def yahoo_long_name(ticker: str) -> str | None:
        return {"BOVA11": "iShares Ibovespa Classe de Índice"}.get(ticker)

    monkeypatch.setattr(sync.cvm_etf, "fetch_index_funds", fetch_index_funds)
    monkeypatch.setattr(sync.market, "yahoo_long_name", yahoo_long_name)
    monkeypatch.setattr(sync.cvm_fii, "fetch_monthly", fetch_monthly)
    monkeypatch.setattr(sync.cvm_fii, "fetch_quarterly", fetch_quarterly)
    return fake


def _runs(db: Session) -> dict[str, SyncRun]:
    return {r.source: r for r in db.scalars(select(SyncRun))}


async def test_sync_completo_grava_todas_as_etapas(db, yahoo):
    assert await sync.run_full_sync(db) is True
    runs = _runs(db)
    assert set(runs) == set(sync.STEPS)
    assert all(r.status == "ok" and r.finished_at for r in runs.values()), {k: r.error for k, r in runs.items()}
    assert db.scalar(select(func.count(MacroRate.id))) == len(sync.bcb.SERIES)
    assert db.scalar(select(func.count(TreasuryBond.id))) == 1
    taee = db.scalar(select(Asset).where(Asset.ticker == "TAEE11"))
    assert taee is not None
    assert taee.cnpj == TAEE_CNPJ
    assert taee.last_price == 30.0
    dfp_indisponivel = TODAY.year - 1
    years = set(db.scalars(select(Fundamental.year).where(Fundamental.asset_id == taee.id)))
    assert dfp_indisponivel not in years
    assert len(years) == sync.get_settings().cvm_years - 1


async def test_erro_inesperado_na_cvm_falha_a_etapa(db, yahoo, monkeypatch):
    """Só erro de download significa "ano ainda não publicado"; um bug no parse precisa aparecer."""

    async def parse_quebrado(year: int, cnpjs: set[str]) -> dict[str, AnnualStatement]:
        raise KeyError("CD_CONTA")

    monkeypatch.setattr(sync.cvm, "fetch_dfp", parse_quebrado)
    await sync.run_full_sync(db, {"universo", "cvm"})
    assert _runs(db)["cvm"].status == "error"


async def test_falha_em_um_ativo_nao_para_os_outros(db, yahoo):
    await sync.run_full_sync(db, {"universo", "mercado"})
    assert _runs(db)["mercado"].status == "ok"
    bbas = db.scalar(select(Asset).where(Asset.ticker == "BBAS3"))
    assert bbas is not None
    assert bbas.last_price is None
    assert db.scalar(select(func.count(PriceDaily.id)).where(PriceDaily.asset_id == bbas.id)) == 0


async def test_etapa_que_falha_nao_impede_as_seguintes(db, yahoo, monkeypatch):
    async def quebrado() -> list[BondQuote]:
        raise ValueError("CSV mudou de formato")

    monkeypatch.setattr(sync.tesouro, "fetch_bonds", quebrado)
    await sync.run_full_sync(db, {"macro", "tesouro", "avaliacoes"})
    runs = _runs(db)
    assert runs["tesouro"].status == "error"
    assert "CSV mudou de formato" in (runs["tesouro"].error or "")
    assert runs["macro"].status == "ok"
    assert runs["avaliacoes"].status == "ok"


async def test_mercado_so_dos_tickers_pedidos(db, yahoo):
    await sync.run_full_sync(db, {"mercado"}, tickers={"TAEE11"})
    assert {t for t, _ in yahoo.calls} == {"TAEE11"}


async def test_so_roda_etapas_pedidas(db, yahoo):
    await sync.run_full_sync(db, {"macro"})
    assert set(_runs(db)) == {"macro"}
    assert sync.current_step() is None


async def test_desdobramento_recarrega_historico(db, yahoo):
    taee = db.scalar(select(Asset).where(Asset.ticker == "TAEE11"))
    assert taee is not None
    antigo = TODAY - timedelta(days=3000)
    db.add_all(
        [
            PriceDaily(asset_id=taee.id, date=antigo, close=99.0, volume=1, source="yahoo"),
            PriceDaily(asset_id=taee.id, date=TODAY - timedelta(days=2), close=99.0, volume=1, source="yahoo"),
            Dividend(asset_id=taee.id, ex_date=antigo, amount=9.0, source="yahoo"),
        ]
    )
    db.commit()
    yahoo.splits = [SplitInfo(TODAY - timedelta(days=1), 2.0)]

    await sync.sync_market(db)

    taee_calls = [start for t, start in yahoo.calls if t == "TAEE11"]
    assert taee_calls == [TODAY - timedelta(days=12), None]
    closes = set(db.scalars(select(PriceDaily.close).where(PriceDaily.asset_id == taee.id)))
    assert closes == {30.0}
    assert db.scalar(select(func.count(Dividend.id)).where(Dividend.asset_id == taee.id, Dividend.ex_date == antigo)) == 0


async def test_nao_roda_dois_syncs_ao_mesmo_tempo(db, yahoo):
    assert sync._lock.acquire(blocking=False)
    try:
        assert sync.is_running()
        assert await sync.run_full_sync(db) is False
        assert sync.start_background_sync() is False
    finally:
        sync._lock.release()
    assert db.scalar(select(func.count(SyncRun.id))) == 0


def test_sync_em_segundo_plano_roda_em_outra_thread(session_factory, yahoo, monkeypatch):
    monkeypatch.setattr(sync, "SessionLocal", session_factory)
    assert sync.start_background_sync({"macro"}) is True
    worker = next(t for t in threading.enumerate() if t.name == "sync")
    assert worker is not threading.current_thread()
    worker.join(timeout=10)
    assert not sync.is_running()
    with session_factory() as s:
        assert _runs(s)["macro"].status == "ok"


def test_carga_inicial_so_quando_nunca_houve_sync(db):
    assert sync.needs_initial_sync(db)
    db.add(SyncRun(source="macro", started_at=datetime.now(), status="error"))
    db.commit()
    assert not sync.needs_initial_sync(db)


def _asset(db: Session, ticker: str) -> Asset:
    asset = db.scalar(select(Asset).where(Asset.ticker == ticker))
    assert asset is not None
    return asset


def test_seed_nao_sobrescreve_o_tipo_do_fii(db):
    kncr = _asset(db, "KNCR11")
    assert (kncr.asset_class, kncr.sector) == ("fii", "papel")
    kncr.sector, kncr.segment = "hibrido", "Multicategoria"
    db.commit()
    sync.seed_universe(db)
    assert (_asset(db, "KNCR11").sector, _asset(db, "KNCR11").segment) == ("hibrido", "Multicategoria")


async def test_sync_fii_grava_informes_e_classifica_pela_carteira(db, yahoo):
    await sync.sync_fii(db)
    kncr, hglg = _asset(db, "KNCR11"), _asset(db, "HGLG11")
    assert (kncr.cnpj, kncr.sector) == (KNCR_CNPJ, "papel")
    assert (hglg.cnpj, hglg.sector, hglg.segment) == (HGLG_CNPJ, "tijolo", "Logística")
    navs = db.scalars(select(FiiReport.nav_per_share).where(FiiReport.asset_id == kncr.id).order_by(FiiReport.ref_date))
    assert list(navs) == [100.0, 101.0]
    trimestral = db.scalar(select(FiiQuarterlyReport).where(FiiQuarterlyReport.asset_id == hglg.id))
    assert trimestral is not None
    assert trimestral.ref_date == date(TODAY.year - 1, 12, 31)
    assert (trimestral.properties, trimestral.vacancy) == (30, 0.05)


async def test_sync_fii_sem_fiis_nao_baixa_nada(db, monkeypatch):
    for asset in db.scalars(select(Asset).where(Asset.asset_class == "fii")):
        asset.asset_class = "acao"
    db.commit()

    async def nao_chamar(*_: object) -> None:
        raise AssertionError("não deveria baixar informes")

    monkeypatch.setattr(sync.cvm_fii, "fetch_monthly", nao_chamar)
    assert await sync.sync_fii(db) == 0


async def test_sync_completo_avalia_os_fiis(db, yahoo):
    assert await sync.run_full_sync(db) is True
    kncr = _asset(db, "KNCR11")
    avaliacao = db.scalar(select(Evaluation).where(Evaluation.asset_id == kncr.id))
    assert avaliacao is not None
    assert avaliacao.engine_version.startswith("fii-")
    regras = {r["id"]: r for r in avaliacao.rules}
    assert regras["fii-patrimonio"]["status"] == "ok"
    assert regras["fii-concentracao-credito"]["value"] == pytest.approx(400e6 / 10e9)
    assert avaliacao.extras["valor_patrimonial_cota"] == 101.0


async def test_sync_etf_liga_pelo_nome_do_yahoo_e_grava_o_patrimonio(db, yahoo):
    await sync.sync_etf(db)
    bova, divo = _asset(db, "BOVA11"), _asset(db, "DIVO11")
    assert bova.cnpj == "10406511000161"
    assert divo.cnpj is None
    assert db.scalar(select(EtfReport.equity).where(EtfReport.asset_id == bova.id)) == 18e9


async def test_sync_completo_avalia_os_etfs(db, yahoo):
    assert await sync.run_full_sync(db) is True
    bova = _asset(db, "BOVA11")
    avaliacao = db.scalar(select(Evaluation).where(Evaluation.asset_id == bova.id))
    assert avaliacao is not None
    assert avaliacao.engine_version.startswith("etf-")
    assert avaliacao.verdict in {"neutro", "evitar"}
    regras = {r["id"]: r for r in avaliacao.rules}
    assert regras["etf-patrimonio"]["status"] == "ok"
    assert regras["etf-taxa-adm"]["status"] == "na"


async def test_itr_grava_trimestres_e_calcula_o_quarto_pela_dfp(db, yahoo):
    assert await sync.run_full_sync(db) is True
    taee = _asset(db, "TAEE11")
    rows = {
        (q.year, q.quarter): q for q in db.scalars(select(QuarterlyFundamental).where(QuarterlyFundamental.asset_id == taee.id))
    }
    com_dfp = TODAY.year - 2
    assert {q for (y, q) in rows if y == com_dfp} == {1, 2, 3, 4}
    quarto = rows[(com_dfp, 4)]
    assert quarto.source == "dfp-itr"
    assert quarto.net_income == pytest.approx(1e9 - 3 * 2e8)
    assert quarto.equity == 6e9
    assert (TODAY.year - 1, 4) not in rows


async def test_comunicados_gravados_por_ativo_sem_duplicar(db, yahoo):
    assert await sync.run_full_sync(db) is True
    assert await sync.sync_filings(db) == sync.FILING_YEARS
    taee = _asset(db, "TAEE11")
    gravados = list(db.scalars(select(FilingRow).where(FilingRow.asset_id == taee.id)))
    assert len(gravados) == sync.FILING_YEARS
    assert {f.category for f in gravados} == {"fato_relevante"}


def _dividends(db: Session, ticker: str) -> list[tuple[str, float, str]]:
    rows = db.scalars(select(Dividend).where(Dividend.asset_id == _asset(db, ticker).id).order_by(Dividend.ex_date))
    return [(d.source, d.amount, d.kind) for d in rows]


async def test_b3_completa_os_proventos_que_faltam_no_yahoo(db, yahoo):
    """O provento que o Yahoo já tem (data ex a um dia) não duplica; o anterior ao primeiro do Yahoo fica de fora."""
    await sync.run_full_sync(db, {"mercado", "proventos"}, tickers={"TAEE11"})
    assert _runs(db)["proventos"].status == "ok"
    esperado = [("yahoo", 1.0, "dividendo"), ("b3", 0.5, "jcp")]
    assert _dividends(db, "TAEE11") == esperado
    await sync.sync_b3_dividends(db, {"TAEE11"})
    assert _dividends(db, "TAEE11") == esperado


async def test_b3_fora_do_ar_mantem_o_que_ja_havia(db, yahoo, monkeypatch):
    await sync.run_full_sync(db, {"mercado", "proventos"}, tickers={"TAEE11"})

    async def fora_do_ar(ticker: str) -> list[CashDividend]:
        raise httpx.ConnectError("sem rede")

    monkeypatch.setattr(sync.b3, "fetch_cash_dividends", fora_do_ar)
    await sync.run_full_sync(db, {"proventos"})
    assert _runs(db)["proventos"].status == "ok"
    assert ("b3", 0.5, "jcp") in _dividends(db, "TAEE11")


BANK_CNPJ = "60872504000123"


async def test_basileia_do_ifdata_substitui_a_manual(db, yahoo):
    await sync.run_full_sync(db)
    itub = _asset(db, "ITUB4")
    itub.cnpj = BANK_CNPJ
    db.add(SectorMetric(asset_id=itub.id, key="basileia", value=12.0, source="manual", updated_at=TODAY))
    db.commit()
    assert await sync.sync_banks(db) == 4
    metric = db.scalar(select(SectorMetric).where(SectorMetric.asset_id == itub.id, SectorMetric.key == "basileia"))
    assert (metric.value, metric.reference, metric.source) == (15.35, "2T26", "BCB IF.data")


def test_cnpj_do_universo_cobre_ticker_que_o_fca_nao_liga():
    assert sync.universe_cnpjs()["BPAC11"] == "30306294000145"
    assert "ITUB4" not in sync.universe_cnpjs()


async def test_cnpj_do_fca_prevalece_sobre_o_do_universo(db, yahoo, monkeypatch):
    monkeypatch.setattr(sync, "universe_cnpjs", lambda: {"TAEE11": "99999999000199", "BPAC11": "30306294000145"})
    await sync.run_full_sync(db)
    assert _asset(db, "TAEE11").cnpj == TAEE_CNPJ
    assert _asset(db, "BPAC11").cnpj == "30306294000145"


async def test_credito_vencido_do_banco_e_do_sistema_vem_do_ifdata(db, yahoo):
    await sync.run_full_sync(db)
    itub = _asset(db, "ITUB4")
    itub.cnpj = BANK_CNPJ
    db.commit()
    assert await sync.sync_banks(db) == 4
    banco = build_stock_snapshot(db, itub)
    assert (banco.sector_metrics["inadimplencia"], banco.sector_metrics["inadimplencia_sistema"]) == (2.96, 3.57)
    assert "inadimplencia_sistema" not in build_stock_snapshot(db, _asset(db, "TAEE11")).sector_metrics

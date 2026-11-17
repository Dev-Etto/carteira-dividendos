"""Orquestração da coleta (services/sync) com providers falsos e banco próprio."""

import threading
from collections.abc import Iterator
from datetime import date, datetime, timedelta

import httpx
import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import Asset, Base, Dividend, Fundamental, MacroRate, PriceDaily, SyncRun, TreasuryBond
from app.providers.base import DividendEvent, PricePoint, SplitInfo
from app.providers.cvm import AnnualStatement
from app.providers.tesouro import BondQuote
from app.services import sync

TODAY = date.today()
TAEE_CNPJ = "07859971000130"


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

    async def brapi_quote(ticker: str) -> None:
        return None

    monkeypatch.setattr(sync.bcb, "fetch_series", fetch_series)
    monkeypatch.setattr(sync.tesouro, "fetch_bonds", fetch_bonds)
    monkeypatch.setattr(sync.cvm, "fetch_ticker_map", fetch_ticker_map)
    monkeypatch.setattr(sync.cvm, "fetch_dfp", fetch_dfp)
    monkeypatch.setattr(sync.market, "yahoo_history", fake)
    monkeypatch.setattr(sync.market, "brapi_quote", brapi_quote)
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

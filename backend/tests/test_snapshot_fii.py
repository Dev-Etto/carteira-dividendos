from collections.abc import Iterator
from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import Asset, Base, Dividend, FiiQuarterlyReport, FiiReport, MacroRate, PriceDaily, TreasuryBond
from app.services.macro import ntnb_real_rate
from app.services.snapshot import build_fii_snapshot

HOJE = date(2026, 11, 17)


@pytest.fixture
def db(tmp_path) -> Iterator[Session]:
    engine = create_engine(f"sqlite:///{tmp_path / 'snap.db'}")
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as s:
        yield s


def _fundo(db: Session, sector: str = "papel") -> Asset:
    asset = Asset(ticker="KNCR11", name="Kinea", asset_class="fii", sector=sector, segment="Multicategoria", last_price=99.0)
    db.add(asset)
    db.flush()
    return asset


def test_snapshot_sem_informes_fica_vazio(db):
    snap = build_fii_snapshot(db, _fundo(db), HOJE)
    assert (snap.kind, snap.price, snap.equity, snap.dividends_ttm, snap.vacancy) == ("papel", 99.0, None, None, None)


def test_snapshot_junta_informes_proventos_e_juros(db):
    asset = _fundo(db)
    db.add_all(
        [
            FiiReport(
                asset_id=asset.id, ref_date=date(2026, 9, 1), equity=9e9, nav_per_share=98.0, paper=0.8, brick=0, fof=0, cash=0.2
            ),
            FiiReport(
                asset_id=asset.id,
                ref_date=date(2026, 10, 1),
                equity=10e9,
                nav_per_share=100.0,
                holders=600_000,
                admin_fee=0.0008,
                started_on=date(2012, 10, 15),
                listed=True,
                paper=0.8,
                brick=0,
                fof=0,
                cash=0.2,
            ),
            FiiQuarterlyReport(asset_id=asset.id, ref_date=date(2026, 9, 30), largest_credit_value=500e6),
            Dividend(asset_id=asset.id, ex_date=HOJE - timedelta(days=30), amount=1.0, source="yahoo"),
            Dividend(asset_id=asset.id, ex_date=HOJE - timedelta(days=300), amount=1.5, source="yahoo"),
            Dividend(asset_id=asset.id, ex_date=HOJE - timedelta(days=400), amount=2.0, source="yahoo"),
            Dividend(asset_id=asset.id, ex_date=HOJE - timedelta(days=100), amount=9.0, kind="amortizacao", source="yahoo"),
            Dividend(asset_id=asset.id, ex_date=HOJE - timedelta(days=800), amount=7.0, source="yahoo"),
            MacroRate(series="cdi", date=HOJE, value=0.1365),
            *[
                PriceDaily(asset_id=asset.id, date=HOJE - timedelta(days=i), close=100.0, volume=50_000, source="yahoo")
                for i in range(30)
            ],
        ]
    )
    db.commit()
    snap = build_fii_snapshot(db, asset, HOJE)
    assert (snap.equity, snap.nav_per_share, snap.holders, snap.started_on) == (10e9, 100.0, 600_000, date(2012, 10, 15))
    assert (snap.dividends_ttm, snap.dividends_prev_ttm) == (2.5, 2.0)
    assert snap.largest_credit_share == pytest.approx(0.05)
    assert snap.avg_daily_volume_brl == pytest.approx(5_000_000)
    assert snap.cdi == 0.1365
    assert snap.ntnb_real is None


def test_tipo_desconhecido_vira_hibrido(db):
    assert build_fii_snapshot(db, _fundo(db, sector="perene"), HOJE).kind == "hibrido"


def test_ntnb_usa_o_vencimento_mais_longo_do_dia_mais_recente(db):
    def bond(name: str, maturity: int, day: date, rate: float | None) -> TreasuryBond:
        return TreasuryBond(name=name, maturity=date(maturity, 5, 15), date=day, buy_rate=rate)

    db.add_all(
        [
            bond("Tesouro IPCA+", 2035, HOJE, 0.074),
            bond("Tesouro IPCA+ com Juros Semestrais", 2060, HOJE, 0.0754),
            bond("Tesouro Prefixado", 2070, HOJE, 0.13),
            bond("Tesouro IPCA+", 2080, HOJE, None),
            bond("Tesouro IPCA+", 2090, HOJE - timedelta(days=1), 0.09),
        ]
    )
    db.commit()
    assert ntnb_real_rate(db) == 0.0754

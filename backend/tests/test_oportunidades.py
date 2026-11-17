from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Asset, Base, Evaluation
from app.services.assets import buy_opportunities

HOJE = date(2026, 11, 17)


def test_oportunidades_intercalam_acoes_e_fiis(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'op.db'}")
    Base.metadata.create_all(engine)
    ativos = [
        ("KNCR11", "fii", 100, "comprar"),
        ("MXRF11", "fii", 99, "comprar"),
        ("HGLG11", "fii", 98, "comprar"),
        ("TAEE11", "acao", 85, "comprar"),
        ("BBSE3", "acao", 90, "comprar"),
        ("PETR4", "acao", 95, "aguardar"),
    ]
    with sessionmaker(bind=engine)() as db:
        for ticker, classe, nota, veredito in ativos:
            asset = Asset(ticker=ticker, name=ticker, asset_class=classe, sector="papel", active=True)
            db.add(asset)
            db.flush()
            db.add(Evaluation(asset_id=asset.id, date=HOJE, score=nota, verdict=veredito, rules=[], engine_version="t"))
        db.commit()
        assert [r.ticker for r in buy_opportunities(db, 4)] == ["BBSE3", "KNCR11", "TAEE11", "MXRF11"]
        assert [r.ticker for r in buy_opportunities(db, 10)][-1] == "HGLG11"

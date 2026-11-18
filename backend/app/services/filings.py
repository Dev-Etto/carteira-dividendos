"""Comunicados das companhias (IPE da CVM): os de um ativo e os recentes da carteira."""

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Asset, Filing
from app.schemas.api import FilingOut

ASSET_LIMIT = 15
PORTFOLIO_DAYS = 30
PORTFOLIO_CATEGORIES = ("fato_relevante", "aviso_acionistas")
"""No painel entram só fatos relevantes e avisos aos acionistas: são os que pedem atenção de quem tem a ação."""


def _out(filing: Filing, ticker: str) -> FilingOut:
    return FilingOut(
        ticker=ticker,
        delivered_on=filing.delivered_on,
        category=filing.category,
        kind=filing.kind,
        subject=filing.subject,
        link=filing.link,
    )


def asset_filings(db: Session, asset: Asset, limit: int = ASSET_LIMIT) -> list[FilingOut]:
    """Comunicados mais recentes do ativo."""
    rows = db.scalars(
        select(Filing).where(Filing.asset_id == asset.id).order_by(Filing.delivered_on.desc(), Filing.id.desc()).limit(limit)
    )
    return [_out(f, asset.ticker) for f in rows]


def portfolio_filings(db: Session, asset_ids: list[int], today: date | None = None) -> list[FilingOut]:
    """Fatos relevantes e avisos aos acionistas dos últimos 30 dias das ações da carteira, do mais novo ao mais velho."""
    since = (today or date.today()) - timedelta(days=PORTFOLIO_DAYS)
    rows = db.execute(
        select(Filing, Asset.ticker)
        .join(Asset, Asset.id == Filing.asset_id)
        .where(Filing.asset_id.in_(asset_ids), Filing.delivered_on >= since, Filing.category.in_(PORTFOLIO_CATEGORIES))
        .order_by(Filing.delivered_on.desc(), Filing.id.desc())
    )
    return [_out(f, ticker) for f, ticker in rows]

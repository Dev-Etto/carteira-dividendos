from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.api import AssetCreate, AssetDetail, AssetHistory, AssetRow, AssetUpdate
from app.services import assets

router = APIRouter(prefix="/api/ativos", tags=["ativos"])


@router.get("", response_model=list[AssetRow])
def list_assets(
    db: Session = Depends(get_db),
    classe: str | None = None,
    setor: str | None = None,
    veredito: str | None = None,
    nota_min: int | None = Query(default=None, ge=0, le=100),
    busca: str | None = None,
) -> list[AssetRow]:
    return assets.list_assets(db, asset_class=classe, sector=setor, verdict=veredito, min_score=nota_min, search=busca)


@router.get("/{ticker}", response_model=AssetDetail)
def asset_detail(ticker: str, db: Session = Depends(get_db)) -> AssetDetail:
    return assets.asset_detail(db, ticker)


@router.get("/{ticker}/historico", response_model=AssetHistory)
def asset_history(ticker: str, anos: int = Query(default=5, ge=1, le=20), db: Session = Depends(get_db)) -> AssetHistory:
    return assets.asset_history(db, ticker, anos)


@router.post("", response_model=AssetRow, status_code=201)
def create_asset(body: AssetCreate, db: Session = Depends(get_db)) -> AssetRow:
    return assets.create_asset(db, body)


@router.patch("/{ticker}", response_model=AssetDetail)
def update_asset(ticker: str, body: AssetUpdate, db: Session = Depends(get_db)) -> AssetDetail:
    return assets.update_asset(db, ticker, body)

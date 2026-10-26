from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.api import SyncStatus
from app.services import sync

router = APIRouter(prefix="/api", tags=["sistema"])


@router.post("/sync", response_model=SyncStatus, status_code=202)
def trigger_sync(etapas: str | None = None, db: Session = Depends(get_db)) -> SyncStatus:
    sync.start_background_sync(sync.parse_steps(etapas))
    return sync.sync_status(db)


@router.get("/sync/status", response_model=SyncStatus)
def sync_status(db: Session = Depends(get_db)) -> SyncStatus:
    return sync.sync_status(db)


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "date": date.today().isoformat()}

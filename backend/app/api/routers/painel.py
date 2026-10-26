from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.api import DashboardOut, MacroOut
from app.services.dashboard import build_dashboard
from app.services.macro import latest_macro

router = APIRouter(prefix="/api", tags=["painel"])


@router.get("/painel", response_model=DashboardOut)
def dashboard(db: Session = Depends(get_db)) -> DashboardOut:
    return build_dashboard(db)


@router.get("/macro", response_model=MacroOut)
def read_macro(db: Session = Depends(get_db)) -> MacroOut:
    return latest_macro(db)

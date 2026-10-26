from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.api import PlanIn, PlanOut, RegisterPlanIn, RegisterPlanOut
from app.services import planner

router = APIRouter(prefix="/api/aporte", tags=["aporte"])


@router.post("/plano", response_model=PlanOut)
def plan(body: PlanIn, db: Session = Depends(get_db)) -> PlanOut:
    return planner.make_plan(db, body.amount)


@router.post("/registrar", response_model=RegisterPlanOut, status_code=201)
def register_plan(body: RegisterPlanIn, db: Session = Depends(get_db)) -> RegisterPlanOut:
    return planner.register_plan(db, body)

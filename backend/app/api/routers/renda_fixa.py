from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.api import CompareIn, CompareOut, FixedIncomeIn, FixedIncomeOut, TreasuryOut
from app.services import fixed_income

router = APIRouter(prefix="/api/renda-fixa", tags=["renda fixa"])


@router.get("", response_model=list[FixedIncomeOut])
def list_holdings(db: Session = Depends(get_db)) -> list[FixedIncomeOut]:
    return fixed_income.list_holdings(db)


@router.post("", response_model=FixedIncomeOut, status_code=201)
def create_holding(body: FixedIncomeIn, db: Session = Depends(get_db)) -> FixedIncomeOut:
    return fixed_income.create_holding(db, body)


@router.put("/{holding_id}", response_model=FixedIncomeOut)
def update_holding(holding_id: int, body: FixedIncomeIn, db: Session = Depends(get_db)) -> FixedIncomeOut:
    return fixed_income.update_holding(db, holding_id, body)


@router.delete("/{holding_id}", status_code=204)
def delete_holding(holding_id: int, db: Session = Depends(get_db)) -> None:
    fixed_income.delete_holding(db, holding_id)


@router.get("/tesouro", response_model=list[TreasuryOut])
def treasury(db: Session = Depends(get_db)) -> list[TreasuryOut]:
    return fixed_income.list_treasury(db)


@router.post("/comparar", response_model=CompareOut)
def compare(body: CompareIn, db: Session = Depends(get_db)) -> CompareOut:
    return fixed_income.compare(db, body)

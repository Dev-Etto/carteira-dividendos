from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.api import PortfolioOut, TransactionIn, TransactionOut
from app.services import transactions
from app.services.portfolio import build_portfolio

router = APIRouter(prefix="/api", tags=["carteira"])


@router.get("/carteira", response_model=PortfolioOut)
def portfolio(db: Session = Depends(get_db)) -> PortfolioOut:
    return build_portfolio(db)


@router.get("/transacoes", response_model=list[TransactionOut])
def list_transactions(db: Session = Depends(get_db)) -> list[TransactionOut]:
    return transactions.list_transactions(db)


@router.post("/transacoes", response_model=TransactionOut, status_code=201)
def create_transaction(body: TransactionIn, db: Session = Depends(get_db)) -> TransactionOut:
    return transactions.create_transaction(db, body)


@router.put("/transacoes/{tx_id}", response_model=TransactionOut)
def update_transaction(tx_id: int, body: TransactionIn, db: Session = Depends(get_db)) -> TransactionOut:
    return transactions.update_transaction(db, tx_id, body)


@router.delete("/transacoes/{tx_id}", status_code=204)
def delete_transaction(tx_id: int, db: Session = Depends(get_db)) -> None:
    transactions.delete_transaction(db, tx_id)

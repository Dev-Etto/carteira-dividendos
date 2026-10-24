"""Operações de compra e venda: cadastro, edição, exclusão e registro das compras do aporte."""

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import BusinessRuleError, NotFoundError
from app.db.models import Split, Transaction
from app.engine.carteira import SplitEvent, Tx, compute_position
from app.schemas.api import PlanPurchaseIn, TransactionIn, TransactionOut
from app.services.assets import get_asset


def tx_out(t: Transaction) -> TransactionOut:
    return TransactionOut(
        id=t.id,
        ticker=t.asset.ticker,
        date=t.date,
        kind=t.kind,
        quantity=t.quantity,
        price=t.price,
        fees=t.fees,
        origin=t.origin,
    )


def ensure_not_future(day: date) -> None:
    if day > date.today():
        raise BusinessRuleError("A data não pode estar no futuro")


def _ensure_valid_sequence(db: Session, asset_id: int, extra: Transaction | None = None, drop_id: int | None = None) -> None:
    """Garante que nenhuma venda deixa a posição negativa depois da mudança."""
    txs = [t for t in db.scalars(select(Transaction).where(Transaction.asset_id == asset_id)) if t.id != drop_id]
    if extra is not None:
        txs.append(extra)
    if not txs:
        return
    first = min(t.date for t in txs)
    splits = [
        SplitEvent(s.date, Decimal(str(s.ratio)))
        for s in db.scalars(select(Split).where(Split.asset_id == asset_id))
        if s.date > first
    ]
    try:
        compute_position([Tx(t.date, t.kind, t.quantity, t.price, t.fees) for t in txs], splits)
    except ValueError as e:
        raise BusinessRuleError(str(e)) from e


def _get_transaction(db: Session, tx_id: int) -> Transaction:
    t = db.get(Transaction, tx_id)
    if t is None:
        raise NotFoundError("Operação não encontrada")
    return t


def list_transactions(db: Session) -> list[TransactionOut]:
    query = select(Transaction).order_by(Transaction.date.desc(), Transaction.id.desc())
    return [tx_out(t) for t in db.scalars(query)]


def create_transaction(db: Session, body: TransactionIn) -> TransactionOut:
    ensure_not_future(body.date)
    asset = get_asset(db, body.ticker)
    t = Transaction(
        asset_id=asset.id,
        asset=asset,
        date=body.date,
        kind=body.kind,
        quantity=body.quantity,
        price=body.price,
        fees=body.fees,
        origin="manual",
    )
    _ensure_valid_sequence(db, asset.id, extra=t)
    db.add(t)
    db.commit()
    return tx_out(t)


def update_transaction(db: Session, tx_id: int, body: TransactionIn) -> TransactionOut:
    t = _get_transaction(db, tx_id)
    ensure_not_future(body.date)
    asset = get_asset(db, body.ticker)
    candidate = Transaction(
        asset_id=asset.id, date=body.date, kind=body.kind, quantity=body.quantity, price=body.price, fees=body.fees
    )
    _ensure_valid_sequence(db, asset.id, extra=candidate, drop_id=tx_id)
    if t.asset_id != asset.id:
        _ensure_valid_sequence(db, t.asset_id, drop_id=tx_id)
    t.asset, t.date, t.kind, t.quantity, t.price, t.fees = asset, body.date, body.kind, body.quantity, body.price, body.fees
    db.commit()
    db.refresh(t)
    return tx_out(t)


def delete_transaction(db: Session, tx_id: int) -> None:
    t = _get_transaction(db, tx_id)
    _ensure_valid_sequence(db, t.asset_id, drop_id=tx_id)
    db.delete(t)
    db.commit()


def add_plan_purchases(db: Session, day: date, purchases: list[PlanPurchaseIn]) -> list[Transaction]:
    """Adiciona à sessão as compras feitas a partir do plano de aporte. Quem chama faz o commit."""
    ensure_not_future(day)
    txs = [
        Transaction(
            asset=get_asset(db, p.ticker),
            date=day,
            kind="compra",
            quantity=p.quantity,
            price=p.price,
            fees=p.fees,
            origin="aporte",
        )
        for p in purchases
    ]
    db.add_all(txs)
    return txs

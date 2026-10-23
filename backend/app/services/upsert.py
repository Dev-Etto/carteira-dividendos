"""Upsert portátil (SQLite e Postgres)."""

from collections.abc import Callable, Sequence
from typing import Any, cast

from sqlalchemy import CursorResult
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.orm import Session

from app.db.models import Base

InsertFn = Callable[[type[Base]], sqlite.Insert]


def _insert_fn(db: Session) -> InsertFn:
    """INSERT do dialeto em uso. Postgres e SQLite expõem a mesma API de ON CONFLICT; o tipo segue o do SQLite."""
    if db.get_bind().dialect.name == "postgresql":
        return cast(InsertFn, postgresql.insert)
    return sqlite.insert


def _on_conflict(stmt: sqlite.Insert, keys: list[str], update: list[str] | None) -> sqlite.Insert:
    """Atualiza as colunas `update` quando a linha já existe; sem `update`, mantém a linha antiga."""
    if not update:
        return stmt.on_conflict_do_nothing(index_elements=keys)
    return stmt.on_conflict_do_update(index_elements=keys, set_={c: stmt.excluded[c] for c in update})


def upsert(
    db: Session, model: type[Base], rows: Sequence[dict[str, Any]], keys: list[str], update: list[str] | None = None
) -> int:
    if not rows:
        return 0
    insert = _insert_fn(db)
    total = 0
    for i in range(0, len(rows), 500):
        stmt = _on_conflict(insert(model).values(list(rows[i : i + 500])), keys, update)
        total += cast(CursorResult[Any], db.execute(stmt)).rowcount or 0
    return total

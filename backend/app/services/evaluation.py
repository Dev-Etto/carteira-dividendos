"""Roda o motor para os ativos e grava a avaliação do dia."""

from collections.abc import Iterable
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Asset, Evaluation, RuleConfig
from app.engine.acoes import evaluate_stock
from app.engine.fii import evaluate_fii
from app.engine.types import Evaluation as EvalModel
from app.services.snapshot import build_fii_snapshot, build_stock_snapshot
from app.services.upsert import upsert

EVALUATED_CLASSES = ("acao", "fii")


def rule_overrides(db: Session) -> dict[str, float]:
    return {r.key: r.value for r in db.scalars(select(RuleConfig))}


def evaluate_asset(db: Session, asset: Asset, overrides: dict[str, float] | None = None) -> EvalModel:
    rules = overrides if overrides is not None else rule_overrides(db)
    if asset.asset_class == "fii":
        return evaluate_fii(build_fii_snapshot(db, asset), rules)
    return evaluate_stock(build_stock_snapshot(db, asset), rules)


def save_evaluation(db: Session, asset: Asset, ev: EvalModel, day: date | None = None) -> None:
    upsert(
        db,
        Evaluation,
        [
            {
                "asset_id": asset.id,
                "date": day or date.today(),
                "score": ev.score,
                "verdict": ev.verdict,
                "ceiling_price": ev.ceiling_price,
                "margin_pct": ev.margin_pct,
                "dividend_yield": ev.dividend_yield,
                "summary": ev.summary,
                "rules": [r.model_dump() for r in ev.rules],
                "extras": ev.extras,
                "engine_version": ev.engine_version,
            }
        ],
        keys=["asset_id", "date"],
        update=[
            "score",
            "verdict",
            "ceiling_price",
            "margin_pct",
            "dividend_yield",
            "summary",
            "rules",
            "extras",
            "engine_version",
        ],
    )


def evaluate_all(db: Session) -> int:
    overrides = rule_overrides(db)
    n = 0
    for asset in db.scalars(select(Asset).where(Asset.active, Asset.asset_class.in_(EVALUATED_CLASSES))):
        save_evaluation(db, asset, evaluate_asset(db, asset, overrides))
        n += 1
    db.commit()
    return n


def latest_evaluations(db: Session, asset_ids: Iterable[int] | None = None) -> dict[int, Evaluation]:
    """Avaliação mais recente de cada ativo, numa única consulta."""
    latest = select(Evaluation.asset_id, func.max(Evaluation.date).label("day")).group_by(Evaluation.asset_id)
    if asset_ids is not None:
        latest = latest.where(Evaluation.asset_id.in_(list(asset_ids)))
    sub = latest.subquery()
    query = select(Evaluation).join(sub, (Evaluation.asset_id == sub.c.asset_id) & (Evaluation.date == sub.c.day))
    return {e.asset_id: e for e in db.scalars(query)}


def latest_evaluation(db: Session, asset_id: int) -> Evaluation | None:
    return db.scalars(select(Evaluation).where(Evaluation.asset_id == asset_id).order_by(Evaluation.date.desc()).limit(1)).first()

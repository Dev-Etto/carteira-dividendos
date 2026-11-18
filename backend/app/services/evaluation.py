"""Roda os motores, grava as avaliações do dia e lê a avaliação que vale para o usuário.

Ações têm uma avaliação por metodologia de seleção registrada (`app/engine/metodos/registro.py`),
todas calculadas juntas na atualização; o que muda com a escolha do usuário é qual delas é lida.
FIIs e ETFs têm um motor só, e a avaliação deles é gravada com a própria classe como método.
"""

from collections.abc import Callable, Iterable, Mapping
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Asset, Evaluation, Profile, RuleConfig
from app.engine.etf import evaluate_etf
from app.engine.fii import evaluate_fii
from app.engine.metodos.registro import DEFAULT_SELECTION, SELECTION_METHODS
from app.engine.types import Evaluation as EvalModel
from app.services.snapshot import build_etf_snapshot, build_fii_snapshot, build_stock_snapshot
from app.services.upsert import upsert

STOCK_CLASS = "acao"
ClassEvaluator = Callable[[Session, Asset, dict[str, float]], EvalModel]
CLASS_EVALUATORS: dict[str, ClassEvaluator] = {
    "fii": lambda db, asset, rules: evaluate_fii(build_fii_snapshot(db, asset), rules),
    "etf": lambda db, asset, rules: evaluate_etf(build_etf_snapshot(db, asset), rules),
}
EVALUATED_CLASSES = (STOCK_CLASS, *CLASS_EVALUATORS)
SAVED_FIELDS = [
    "score",
    "verdict",
    "ceiling_price",
    "margin_pct",
    "dividend_yield",
    "summary",
    "rules",
    "extras",
    "engine_version",
]


def rule_overrides(db: Session) -> dict[str, float]:
    return {r.key: r.value for r in db.scalars(select(RuleConfig))}


def selected_method(db: Session) -> str:
    """Metodologia de seleção escolhida no perfil; sem perfil, ou com um método que saiu do registro, o padrão."""
    key = db.scalar(select(Profile.selection_method).limit(1))
    return key if key in SELECTION_METHODS else DEFAULT_SELECTION


def visible_methods(db: Session) -> tuple[str, ...]:
    """Métodos cujas avaliações as telas mostram: o escolhido para ações e o motor único de cada outra classe."""
    return (selected_method(db), *CLASS_EVALUATORS)


def save_evaluation(db: Session, asset: Asset, ev: EvalModel, method: str, day: date | None = None) -> None:
    row = {"asset_id": asset.id, "date": day or date.today(), "method": method} | {
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
    upsert(db, Evaluation, [row], keys=["asset_id", "date", "method"], update=SAVED_FIELDS)


def evaluate_stocks(db: Session, assets: Iterable[Asset], rules: Mapping[str, float]) -> int:
    """Avalia o lote de ações por todas as metodologias de seleção. O lote vai inteiro para cada método,
    porque métodos de ranking comparam as ações entre si."""
    by_ticker = {a.ticker: a for a in assets}
    snapshots = [build_stock_snapshot(db, a) for a in by_ticker.values()]
    n = 0
    for key, method in SELECTION_METHODS.items():
        for ticker, ev in method.evaluate(snapshots, rules).items():
            save_evaluation(db, by_ticker[ticker], ev, key)
            n += 1
    return n


def _active(db: Session, asset_class: str) -> list[Asset]:
    return list(db.scalars(select(Asset).where(Asset.active, Asset.asset_class == asset_class)))


def evaluate_all(db: Session) -> int:
    """Avalia todos os ativos ativos; devolve quantos ativos foram avaliados."""
    rules = rule_overrides(db)
    stocks = _active(db, STOCK_CLASS)
    evaluate_stocks(db, stocks, rules)
    others = [a for cls in CLASS_EVALUATORS for a in _active(db, cls)]
    for asset in others:
        save_evaluation(db, asset, CLASS_EVALUATORS[asset.asset_class](db, asset, rules), asset.asset_class)
    db.commit()
    return len(stocks) + len(others)


def refresh_asset(db: Session, asset: Asset) -> None:
    """Reavalia um ativo agora. Uma ação reavalia o lote de ações inteiro, porque o resultado dela
    pode depender das outras nos métodos de ranking."""
    rules = rule_overrides(db)
    if asset.asset_class == STOCK_CLASS:
        evaluate_stocks(db, _active(db, STOCK_CLASS), rules)
        db.commit()
        return
    save_evaluation(db, asset, CLASS_EVALUATORS[asset.asset_class](db, asset, rules), asset.asset_class)
    db.commit()


def latest_evaluations(
    db: Session, asset_ids: Iterable[int] | None = None, methods: Iterable[str] | None = None
) -> dict[int, Evaluation]:
    """Avaliação mais recente de cada ativo nos métodos pedidos (padrão: os visíveis), numa única consulta."""
    wanted = list(methods if methods is not None else visible_methods(db))
    latest = (
        select(Evaluation.asset_id, func.max(Evaluation.date).label("day"))
        .where(Evaluation.method.in_(wanted))
        .group_by(Evaluation.asset_id)
    )
    if asset_ids is not None:
        latest = latest.where(Evaluation.asset_id.in_(list(asset_ids)))
    sub = latest.subquery()
    query = select(Evaluation).join(sub, (Evaluation.asset_id == sub.c.asset_id) & (Evaluation.date == sub.c.day))
    return {e.asset_id: e for e in db.scalars(query.where(Evaluation.method.in_(wanted)))}


def latest_evaluation(db: Session, asset_id: int) -> Evaluation | None:
    return latest_evaluations(db, [asset_id]).get(asset_id)


def evaluations_by_method(db: Session, asset_id: int) -> dict[str, Evaluation]:
    """Avaliação mais recente do ativo em cada metodologia de seleção, para comparar na ficha."""
    found = {key: latest_evaluations(db, [asset_id], [key]).get(asset_id) for key in SELECTION_METHODS}
    return {key: ev for key, ev in found.items() if ev is not None}

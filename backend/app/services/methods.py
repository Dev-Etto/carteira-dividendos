"""Metodologias de investimento: as disponíveis e a escolha do usuário."""

from sqlalchemy.orm import Session

from app.core.errors import BusinessRuleError
from app.engine.metodos.base import MethodInfo
from app.engine.metodos.registro import ALLOCATION_METHODS, SELECTION_METHODS, allocation_method
from app.schemas.api import MethodChoiceIn, MethodOut, MethodsOut, ProfileOut
from app.services.profile import get_profile, profile_out, replace_targets


def method_out(info: MethodInfo) -> MethodOut:
    return MethodOut(key=info.key, label=info.label, author=info.author, summary=info.summary, focus=info.focus)


def list_methods() -> MethodsOut:
    return MethodsOut(
        selection=[method_out(m.info) for m in SELECTION_METHODS.values()],
        allocation=[method_out(m.info) for m in ALLOCATION_METHODS.values()],
    )


def choose_methods(db: Session, body: MethodChoiceIn) -> ProfileOut:
    """Guarda as metodologias escolhidas. Trocar a de divisão troca a divisão-alvo pela sugerida por ela,
    como acontece ao refazer o questionário."""
    if body.selection_method not in SELECTION_METHODS:
        raise BusinessRuleError(f"Metodologia de seleção desconhecida: {body.selection_method}")
    if body.allocation_method not in ALLOCATION_METHODS:
        raise BusinessRuleError(f"Metodologia de divisão desconhecida: {body.allocation_method}")
    profile = get_profile(db)
    changed_allocation = profile.allocation_method != body.allocation_method
    profile.selection_method = body.selection_method
    profile.allocation_method = body.allocation_method
    if changed_allocation:
        replace_targets(db, allocation_method(body.allocation_method).targets(profile.risk_profile))
    db.commit()
    return profile_out(profile)

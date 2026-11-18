"""Perfil do investidor, divisão-alvo da carteira e limites das regras do motor."""

from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.errors import BusinessRuleError
from app.db.models import AllocationTarget, Profile, RuleConfig
from app.engine.config import DEFAULT_RULES, merged_rules, rule_errors
from app.engine.metodos.registro import allocation_method
from app.engine.perfil import DESCRIPTIONS, QUESTIONS, profile_from_answers
from app.engine.renda_fixa import emergency_target, reserve_months_for
from app.schemas.api import AllocationItem, ProfileIn, ProfileOut, Question, QuestionOption, RuleConfigItem
from app.services.evaluation import evaluate_all

ASSET_CLASSES = ("renda_fixa", "acoes", "fiis", "etfs")


def get_profile(db: Session) -> Profile:
    """Perfil único do app (uso pessoal). Cria o registro padrão na primeira leitura."""
    profile = db.scalar(select(Profile).limit(1))
    if profile is not None:
        return profile
    profile = Profile()
    db.add(profile)
    db.commit()
    return profile


def reserve_target(profile: Profile) -> float:
    return emergency_target(float(profile.monthly_expenses), profile.emergency_months)


def profile_out(profile: Profile) -> ProfileOut:
    out = ProfileOut.model_validate(profile)
    out.risk_description = DESCRIPTIONS.get(profile.risk_profile, "")
    out.emergency_target = Decimal(str(reserve_target(profile)))
    return out


def questionnaire() -> list[Question]:
    return [
        Question(
            id=q["id"], text=q["text"], options=[QuestionOption(label=label, points=points) for label, points in q["options"]]
        )
        for q in QUESTIONS
    ]


def replace_targets(db: Session, weights: dict[str, float]) -> None:
    db.execute(delete(AllocationTarget))
    db.add_all(AllocationTarget(asset_class=cls, weight_pct=w) for cls, w in weights.items())


def save_profile(db: Session, body: ProfileIn) -> ProfileOut:
    """Salva as respostas do questionário. A divisão-alvo passa a ser a sugerida para o perfil calculado,
    a menos que `keep_allocation` peça para manter a atual."""
    expected = {q["id"] for q in QUESTIONS}
    if set(body.answers) != expected:
        raise BusinessRuleError(f"Responda todas as perguntas: {sorted(expected)}")
    profile = get_profile(db)
    profile.answers = body.answers
    profile.risk_profile = profile_from_answers(body.answers)
    profile.income_stability = body.income_stability
    profile.emergency_months = reserve_months_for(body.income_stability)
    profile.monthly_expenses = body.monthly_expenses
    profile.monthly_contribution = body.monthly_contribution
    profile.passive_income_goal = body.passive_income_goal
    profile.onboarded = True
    if not body.keep_allocation:
        replace_targets(db, allocation_method(profile.allocation_method).targets(profile.risk_profile))
    db.commit()
    return profile_out(profile)


def targets(db: Session) -> dict[str, float]:
    """Divisão-alvo salva; sem nenhuma salva, a sugerida pela metodologia de divisão do perfil."""
    saved = {t.asset_class: t.weight_pct for t in db.scalars(select(AllocationTarget))}
    profile = get_profile(db)
    return saved or allocation_method(profile.allocation_method).targets(profile.risk_profile)


def read_allocation(db: Session) -> list[AllocationItem]:
    current = targets(db)
    return [AllocationItem(asset_class=cls, weight_pct=current.get(cls, 0.0)) for cls in ASSET_CLASSES]


def save_allocation(db: Session, items: list[AllocationItem]) -> list[AllocationItem]:
    if abs(sum(i.weight_pct for i in items) - 100) > 0.01:
        raise BusinessRuleError("Os pesos precisam somar 100%")
    replace_targets(db, {i.asset_class: i.weight_pct for i in items})
    db.commit()
    return items


def read_rules(db: Session) -> list[RuleConfigItem]:
    current = {r.key: r.value for r in db.scalars(select(RuleConfig))}
    return [RuleConfigItem(key=k, value=current.get(k, v), default=v) for k, v in DEFAULT_RULES.items()]


def _store_rule(db: Session, key: str, value: float) -> None:
    """Guarda só o que difere do padrão; voltar ao padrão apaga a linha."""
    row = db.get(RuleConfig, key)
    is_default = value == DEFAULT_RULES[key]
    if is_default and row is not None:
        db.delete(row)
        return
    if is_default:
        return
    if row is None:
        db.add(RuleConfig(key=key, value=value))
        return
    row.value = value


def save_rules(db: Session, items: dict[str, float]) -> list[RuleConfigItem]:
    """Salva os limites e reavalia todas as ações com eles."""
    unknown = set(items) - set(DEFAULT_RULES)
    if unknown:
        raise BusinessRuleError(f"Regras desconhecidas: {sorted(unknown)}")
    current = {r.key: r.value for r in db.scalars(select(RuleConfig))}
    errors = rule_errors(merged_rules(current | items))
    if errors:
        raise BusinessRuleError("; ".join(errors))
    for key, value in items.items():
        _store_rule(db, key, value)
    db.commit()
    evaluate_all(db)
    return read_rules(db)

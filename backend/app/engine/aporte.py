"""Planejador de aporte (puro). Ordem: reserva → classes → ativos → quantidades.

Nunca sugere vendas: a carteira se reequilibra pelos aportes.
"""

import math
from dataclasses import dataclass, field

from app.engine import fmt

CLASS_LABEL = {"renda_fixa": "Renda fixa", "acoes": "Ações", "fiis": "FIIs", "etfs": "ETFs"}
DEFAULT_LONG_TERM_FIXED_INCOME = "Tesouro IPCA+ (vencimento longo) ou CDB ≥ 100% do CDI"
NEW_SECTOR_BOOST = 1.5


@dataclass
class Candidate:
    ticker: str
    name: str
    price: float
    score: int
    margin: float
    sector: str
    held_value: float = 0.0


@dataclass
class PlanLine:
    asset_class: str
    product: str
    ticker: str | None
    quantity: int | None
    unit_price: float | None
    amount: float
    reason: str


@dataclass
class Plan:
    amount: float
    lines: list[PlanLine] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    leftover: float = 0.0


def split_by_class(total: float, current: dict[str, float], targets: dict[str, float], amount: float) -> dict[str, float]:
    """Divide o aporte entre classes proporcionalmente ao déficit de cada uma."""
    after = total + amount
    deficits = {k: max(0.0, after * targets.get(k, 0) / 100 - current.get(k, 0.0)) for k in targets}
    tot = sum(deficits.values())
    if tot <= 0:
        return {k: amount * targets[k] / 100 for k in targets}
    return {k: amount * d / tot for k, d in deficits.items()}


def _pick_stocks(
    budget: float,
    candidates: list[Candidate],
    class_target_value: float,
    max_asset_share: float,
    max_sector_share: float,
    min_assets: int,
) -> tuple[list[PlanLine], float]:
    """Escolhe as ações por nota × margem, respeitando os limites por ativo e por setor.

    Enquanto a carteira tem menos de `min_assets` ações, setores ainda ausentes ganham prioridade
    (NEW_SECTOR_BOOST). Com valores pequenos, se nenhuma cota cabe nos limites, compra um ativo novo
    por vez e a diversificação acontece ao longo dos meses."""
    lines: list[PlanLine] = []
    held = {c.ticker: c.held_value for c in candidates}
    sector_val: dict[str, float] = {}
    for c in candidates:
        sector_val[c.sector] = sector_val.get(c.sector, 0.0) + c.held_value
    n_held = sum(1 for v in held.values() if v > 0)
    cap_asset = class_target_value * max(max_asset_share, 1 / min_assets)
    cap_sector = class_target_value * max_sector_share
    held_sectors = {s for s, v in sector_val.items() if v > 0}

    def priority(c: Candidate) -> float:
        room = max(0.0, 1 - held[c.ticker] / cap_asset) if cap_asset else 1.0
        p = c.score * (1 + max(c.margin, 0)) * room
        if n_held < min_assets and c.sector not in held_sectors:
            p *= NEW_SECTOR_BOOST
        return p

    remaining = budget
    for c in sorted(candidates, key=priority, reverse=True):
        if remaining < c.price:
            continue
        room = min(cap_asset - held[c.ticker], cap_sector - sector_val.get(c.sector, 0.0), remaining)
        qty = math.floor(room / c.price) if room > 0 else 0
        if qty < 1 and held[c.ticker] == 0 and not lines:
            qty = math.floor(remaining / c.price)
        if qty < 1:
            continue
        value = qty * c.price
        reason = f"nota {c.score}, {fmt.pct(c.margin)} abaixo do preço-teto" + (
            ", setor ainda ausente na carteira" if c.sector not in held_sectors else ""
        )
        lines.append(PlanLine("acoes", c.name, c.ticker, qty, c.price, value, reason))
        held[c.ticker] += value
        sector_val[c.sector] = sector_val.get(c.sector, 0.0) + value
        held_sectors.add(c.sector)
        remaining -= value
    return lines, remaining


def _add_stocks(
    plan: Plan,
    budget: float,
    stock_candidates: list[Candidate],
    class_target_value: float,
    max_asset_share: float,
    max_sector_share: float,
    min_assets: int,
) -> float:
    """Acrescenta as compras de ações ao plano e devolve quanto do orçamento foi usado."""
    eligible = [c for c in stock_candidates if c.price > 0]
    lines, rest = _pick_stocks(budget, eligible, class_target_value, max_asset_share, max_sector_share, min_assets)
    plan.lines += lines
    if not eligible:
        plan.notes.append("Nenhuma ação com veredito 'comprar' hoje. A parte de ações ficou em Tesouro Selic.")
    return budget - rest


def build_plan(
    *,
    amount: float,
    reserve_current: float,
    reserve_target: float,
    class_current: dict[str, float],
    targets: dict[str, float],
    stock_candidates: list[Candidate],
    long_term_fixed_income: str = DEFAULT_LONG_TERM_FIXED_INCOME,
    max_asset_share: float = 0.10,
    max_sector_share: float = 0.30,
    min_assets: int = 5,
) -> Plan:
    """Monta o plano em duas etapas: primeiro completa a reserva de emergência; o que sobrar é
    dividido entre as classes abaixo do alvo e, dentro de ações, entre os melhores ativos."""
    plan = Plan(amount=amount)
    missing = max(0.0, reserve_target - reserve_current)
    to_reserve = min(amount, missing) if missing > 0 else 0.0
    if missing > 0:
        plan.lines.append(
            PlanLine(
                "reserva",
                "Tesouro Selic (reserva de emergência)",
                None,
                None,
                None,
                to_reserve,
                f"faltam {fmt.brl(missing)} para a reserva de {fmt.brl(reserve_target)}",
            )
        )
    left = amount - to_reserve
    if missing > 0 and left <= 0:
        plan.notes.append("Todo o aporte foi para a reserva. Investimentos começam quando ela estiver completa.")
        return plan

    total = sum(class_current.values())
    per_class = split_by_class(total, class_current, targets, left)
    after_total = total + left
    parked: list[tuple[str, float]] = []

    for cls, budget in sorted(per_class.items(), key=lambda kv: -kv[1]):
        if budget < 1:
            continue
        if cls == "renda_fixa":
            plan.lines.append(
                PlanLine(
                    "renda_fixa",
                    long_term_fixed_income,
                    None,
                    None,
                    None,
                    budget,
                    f"renda fixa está abaixo do alvo de {fmt.num(targets[cls], 0)}%",
                )
            )
            left -= budget
            continue
        if cls == "acoes":
            class_target_value = after_total * targets[cls] / 100
            used = _add_stocks(plan, budget, stock_candidates, class_target_value, max_asset_share, max_sector_share, min_assets)
            left -= used
            parked += _unspent_stock_budget(used, budget)
            continue
        parked.append((f"{CLASS_LABEL[cls]} aguardando o motor da próxima fase", budget))
        plan.notes.append(
            f"{CLASS_LABEL[cls]}: o motor desta classe chega na próxima fase; {fmt.brl(budget)} ficam em Tesouro Selic até lá."
        )

    if left > 0.01:
        plan.lines.append(
            PlanLine("caixa", "Tesouro Selic (caixa a investir)", None, None, None, left, _cash_reason(parked, left))
        )
        plan.leftover = left
    return plan


def _unspent_stock_budget(used: float, budget: float) -> list[tuple[str, float]]:
    """A verba de ações fica em caixa inteira quando nenhuma ação pôde ser comprada."""
    if used:
        return []
    return [("ações sem veredito 'comprar' hoje", budget)]


def _cash_reason(parked: list[tuple[str, float]], cash: float) -> str:
    """Explica de onde vem o dinheiro que fica em caixa: classes sem motor, ações sem compra e arredondamento."""
    rounding = cash - sum(value for _, value in parked)
    reasons = [f"{label}: {fmt.brl(value)}" for label, value in parked]
    if rounding > 0.01:
        reasons.append(f"sobra que não fecha uma cota: {fmt.brl(rounding)}")
    return "; ".join(reasons) + ". Entra no próximo aporte."

"""Planejador de aporte (puro). Ordem: reserva → classes → ativos → quantidades.

Nunca sugere vendas: a carteira se reequilibra pelos aportes.
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass, field

from app.engine import fmt

CLASS_LABEL = {"renda_fixa": "Renda fixa", "acoes": "Ações", "fiis": "FIIs", "etfs": "ETFs", "internacional": "Internacional"}
DEFAULT_LONG_TERM_FIXED_INCOME = "Tesouro IPCA+ (vencimento longo) ou CDB ≥ 100% do CDI"
NEW_SECTOR_BOOST = 1.5
MAX_FII_KIND_SHARE = 0.60
"""Peso máximo de um tipo de FII (papel ou tijolo) na parte de FIIs: só há dois grupos relevantes."""


@dataclass
class Candidate:
    """Ativo com veredito "comprar". sector: setor da ação ou tipo do FII (papel, tijolo...), o grupo
    usado para limitar a concentração."""

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


@dataclass(frozen=True)
class ClassPolicy:
    """Como escolher os ativos de uma classe: limite por grupo (setor ou tipo) e os textos do plano.

    equal_weight: em vez de ranquear por nota × margem, divide a classe em partes iguais entre os
    candidatos (ETFs favoritos do usuário)."""

    plan_class: str
    max_group_share: float
    margin_label: str
    new_group_label: str
    empty_note: str
    unspent_label: str
    equal_weight: bool = False


def stock_policy(max_sector_share: float) -> ClassPolicy:
    return ClassPolicy(
        plan_class="acoes",
        max_group_share=max_sector_share,
        margin_label="abaixo do preço-teto",
        new_group_label="setor ainda ausente na carteira",
        empty_note="Nenhuma ação com veredito 'comprar' hoje. A parte de ações ficou em Tesouro Selic.",
        unspent_label="ações sem veredito 'comprar' hoje",
    )


FII_POLICY = ClassPolicy(
    plan_class="fiis",
    max_group_share=MAX_FII_KIND_SHARE,
    margin_label="abaixo do preço máximo pelo P/VP",
    new_group_label="tipo de FII ainda ausente na carteira",
    empty_note="Nenhum FII com veredito 'comprar' hoje. A parte de FIIs ficou em Tesouro Selic.",
    unspent_label="FIIs sem veredito 'comprar' hoje",
)


ETF_POLICY = ClassPolicy(
    plan_class="etfs",
    max_group_share=1.0,
    margin_label="",
    new_group_label="",
    empty_note="Nenhum ETF favorito apto. Marque favoritos na aba ETFs do Explorar; a parte de ETFs ficou em Tesouro Selic.",
    unspent_label="ETFs sem favorito apto",
    equal_weight=True,
)


INTERNATIONAL_POLICY = ClassPolicy(
    plan_class="internacional",
    max_group_share=1.0,
    margin_label="",
    new_group_label="",
    empty_note="Nenhum ETF internacional favorito apto. Marque como favorito um ETF de índice estrangeiro (ex.: IVVB11); a parte internacional ficou em Tesouro Selic.",
    unspent_label="ETFs internacionais sem favorito apto",
    equal_weight=True,
)


@dataclass
class Plan:
    amount: float
    lines: list[PlanLine] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    leftover: float = 0.0


def class_deficits(total: float, current: dict[str, float], targets: dict[str, float], amount: float) -> dict[str, float]:
    """Quanto falta em cada classe para chegar ao alvo depois do aporte."""
    after = total + amount
    return {k: max(0.0, after * targets.get(k, 0) / 100 - current.get(k, 0.0)) for k in targets}


def fund_one_unit(per_class: dict[str, float], cheapest: dict[str, float], deficits: dict[str, float]) -> dict[str, float]:
    """Garante uma cota às classes cuja parte do aporte não paga nem a cota mais barata (um ETF de R$ 480
    com R$ 440 de verba, por exemplo). Só quando a classe está abaixo do alvo em pelo menos uma cota e as
    outras classes têm verba para ceder; a diferença sai delas, na proporção do que cada uma recebeu. Sem
    isso, a verba da classe iria toda para o caixa, mês após mês."""
    out = dict(per_class)
    for cls in sorted(cheapest, key=lambda c: -deficits.get(c, 0.0)):
        price = cheapest[cls]
        need = price - out.get(cls, 0.0)
        others = {k: v for k, v in out.items() if k != cls and v > 0}
        pool = sum(others.values())
        if need <= 0 or price > deficits.get(cls, 0.0) or need > pool:
            continue
        out |= {k: v - need * v / pool for k, v in others.items()}
        out[cls] = price
    return out


def split_by_class(total: float, current: dict[str, float], targets: dict[str, float], amount: float) -> dict[str, float]:
    """Divide o aporte entre classes proporcionalmente ao déficit de cada uma."""
    after = total + amount
    deficits = {k: max(0.0, after * targets.get(k, 0) / 100 - current.get(k, 0.0)) for k in targets}
    tot = sum(deficits.values())
    if tot <= 0:
        return {k: amount * targets[k] / 100 for k in targets}
    return {k: amount * d / tot for k, d in deficits.items()}


def _pick_assets(
    policy: ClassPolicy,
    budget: float,
    candidates: list[Candidate],
    class_target_value: float,
    max_asset_share: float,
    min_assets: int,
) -> tuple[list[PlanLine], float]:
    """Escolhe os ativos da classe por nota × margem, respeitando os limites por ativo e por grupo.

    Enquanto a classe tem menos de `min_assets` ativos na carteira, grupos ainda ausentes ganham
    prioridade (NEW_SECTOR_BOOST). Com valores pequenos, se nenhuma cota cabe nos limites, compra um
    ativo novo por vez e a diversificação acontece ao longo dos meses."""
    lines: list[PlanLine] = []
    held = {c.ticker: c.held_value for c in candidates}
    sector_val: dict[str, float] = {}
    for c in candidates:
        sector_val[c.sector] = sector_val.get(c.sector, 0.0) + c.held_value
    n_held = sum(1 for v in held.values() if v > 0)
    cap_asset = class_target_value * max(max_asset_share, 1 / min_assets)
    cap_sector = class_target_value * policy.max_group_share
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
        reason = f"nota {c.score}, {fmt.pct(c.margin)} {policy.margin_label}" + (
            f", {policy.new_group_label}" if c.sector not in held_sectors else ""
        )
        lines.append(PlanLine(policy.plan_class, c.name, c.ticker, qty, c.price, value, reason))
        held[c.ticker] += value
        sector_val[c.sector] = sector_val.get(c.sector, 0.0) + value
        held_sectors.add(c.sector)
        remaining -= value
    return lines, remaining


def _pick_equal(
    policy: ClassPolicy,
    budget: float,
    candidates: list[Candidate],
    class_target_value: float,
    max_asset_share: float,
    min_assets: int,
) -> tuple[list[PlanLine], float]:
    """Divide a classe em partes iguais entre os candidatos: cada um caminha para a mesma fatia do alvo,
    e o mais distante dela compra primeiro. Se nenhuma cota cabe na fatia, compra o mais distante que
    couber no orçamento, e o equilíbrio vem nos próximos aportes."""
    if not candidates:
        return [], budget
    share = class_target_value / len(candidates)
    by_distance = sorted(candidates, key=lambda c: c.held_value)
    lines: list[PlanLine] = []
    remaining = budget
    for c in by_distance:
        room = min(share - c.held_value, remaining)
        qty = math.floor(room / c.price) if room > 0 else 0
        if qty < 1:
            continue
        lines.append(
            PlanLine(
                policy.plan_class,
                c.name,
                c.ticker,
                qty,
                c.price,
                qty * c.price,
                f"favorito; cada ETF caminha para {fmt.brl(share)}",
            )
        )
        remaining -= qty * c.price
    if lines:
        return lines, remaining
    return _buy_cheapest_gap(policy, by_distance, remaining)


def _buy_cheapest_gap(policy: ClassPolicy, by_distance: list[Candidate], budget: float) -> tuple[list[PlanLine], float]:
    """Compra, com todo o orçamento, o candidato mais distante da sua fatia cuja cota caiba nele."""
    affordable = [c for c in by_distance if c.price <= budget]
    if not affordable:
        return [], budget
    c = affordable[0]
    qty = math.floor(budget / c.price)
    line = PlanLine(policy.plan_class, c.name, c.ticker, qty, c.price, qty * c.price, "favorito mais abaixo da sua fatia")
    return [line], budget - qty * c.price


def _add_assets(
    plan: Plan,
    policy: ClassPolicy,
    budget: float,
    candidates: Sequence[Candidate],
    class_target_value: float,
    max_asset_share: float,
    min_assets: int,
) -> float:
    """Acrescenta as compras da classe ao plano e devolve quanto do orçamento foi usado."""
    eligible = [c for c in candidates if c.price > 0]
    pick = _pick_equal if policy.equal_weight else _pick_assets
    lines, rest = pick(policy, budget, eligible, class_target_value, max_asset_share, min_assets)
    plan.lines += lines
    if not eligible:
        plan.notes.append(policy.empty_note)
    return budget - rest


def build_plan(
    *,
    amount: float,
    reserve_current: float,
    reserve_target: float,
    class_current: dict[str, float],
    targets: dict[str, float],
    stock_candidates: Sequence[Candidate],
    fii_candidates: Sequence[Candidate] = (),
    etf_candidates: Sequence[Candidate] = (),
    international_candidates: Sequence[Candidate] = (),
    long_term_fixed_income: str = DEFAULT_LONG_TERM_FIXED_INCOME,
    max_asset_share: float = 0.10,
    max_sector_share: float = 0.30,
    min_assets: int = 5,
) -> Plan:
    """Monta o plano em duas etapas: primeiro completa a reserva de emergência; o que sobrar é
    dividido entre as classes abaixo do alvo; dentro de ações e FIIs, entre os melhores ativos, e
    dentro de ETFs e da classe internacional, em partes iguais entre os favoritos aptos."""
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
    after_total = total + left
    parked: list[tuple[str, float]] = []
    by_class = {
        "acoes": (stock_policy(max_sector_share), stock_candidates),
        "fiis": (FII_POLICY, fii_candidates),
        "etfs": (ETF_POLICY, etf_candidates),
        "internacional": (INTERNATIONAL_POLICY, international_candidates),
    }
    cheapest = {
        cls: min(c.price for c in candidates if c.price > 0)
        for cls, (_, candidates) in by_class.items()
        if cls in targets and any(c.price > 0 for c in candidates)
    }
    per_class = fund_one_unit(
        split_by_class(total, class_current, targets, left), cheapest, class_deficits(total, class_current, targets, left)
    )

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
        if cls in by_class:
            policy, candidates = by_class[cls]
            class_target_value = after_total * targets[cls] / 100
            used = _add_assets(plan, policy, budget, candidates, class_target_value, max_asset_share, min_assets)
            left -= used
            parked += _unspent_budget(policy, used, budget, candidates)
            continue
        parked.append((f"{CLASS_LABEL.get(cls, cls)} sem regra de compra", budget))

    if left > 0.01:
        plan.lines.append(
            PlanLine("caixa", "Tesouro Selic (caixa a investir)", None, None, None, left, _cash_reason(parked, left))
        )
        plan.leftover = left
    return plan


def _unspent_budget(policy: ClassPolicy, used: float, budget: float, candidates: Sequence[Candidate]) -> list[tuple[str, float]]:
    """A verba da classe fica em caixa inteira quando nenhum ativo dela pôde ser comprado: ou não há
    candidato, ou a cota mais barata custa mais do que a parte da classe neste aporte."""
    if used:
        return []
    priced = [c for c in candidates if c.price > 0]
    if not priced:
        return [(policy.unspent_label, budget)]
    cheapest = min(priced, key=lambda c: c.price)
    label = f"{CLASS_LABEL.get(policy.plan_class, policy.plan_class)}: a cota de {cheapest.ticker} ({fmt.brl(cheapest.price)}) não coube na parte da classe"
    return [(label, budget)]


def _cash_reason(parked: list[tuple[str, float]], cash: float) -> str:
    """Explica de onde vem o dinheiro que fica em caixa: classes sem motor, classes sem compra e arredondamento."""
    rounding = cash - sum(value for _, value in parked)
    reasons = [f"{label}: {fmt.brl(value)}" for label, value in parked]
    if rounding > 0.01:
        reasons.append(f"sobra que não fecha uma cota: {fmt.brl(rounding)}")
    return "; ".join(reasons) + ". Entra no próximo aporte."

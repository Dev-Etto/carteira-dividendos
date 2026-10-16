"""Cálculos de renda fixa: IR regressivo, equivalência isento × tributado, FGC,
rendimento líquido e regras da reserva de emergência."""

from dataclasses import dataclass

FGC_LIMIT = 250_000.0

IR_TABLE = [
    (180, 0.225),
    (360, 0.20),
    (720, 0.175),
    (10**9, 0.15),
]

TAX_EXEMPT = {"lci", "lca", "cri", "cra", "debenture_incentivada"}


def ir_rate(days: int) -> float:
    """Alíquota do IR regressivo. IR_TABLE traz pares (até N dias, alíquota)."""
    for limit, rate in IR_TABLE:
        if days <= limit:
            return rate
    return 0.15


def annual_gross_rate(indexer: str, rate: float, cdi: float, ipca: float, selic: float) -> float:
    """Taxa bruta anual estimada. rate: % do CDI (ex.: 110) ou taxa a.a. em decimal.

    No Tesouro Selic, rate é o ágio/deságio sobre a Selic (na prática, perto de zero)."""
    match indexer:
        case "cdi":
            return cdi * rate / 100
        case "selic":
            return selic + rate
        case "ipca":
            return (1 + ipca) * (1 + rate) - 1
        case "pre":
            return rate
    raise ValueError(f"indexador desconhecido: {indexer}")


def net_annual_rate(gross: float, kind: str, days: int) -> float:
    if kind in TAX_EXEMPT:
        return gross
    return gross * (1 - ir_rate(days))


def exempt_equivalent(taxed_gross: float, days: int) -> float:
    """Taxa que um título isento precisa pagar para empatar com um tributado."""
    return taxed_gross * (1 - ir_rate(days))


def taxed_equivalent(exempt_rate: float, days: int) -> float:
    """Taxa bruta que um título tributado precisa pagar para empatar com um isento."""
    return exempt_rate / (1 - ir_rate(days))


@dataclass
class ReserveCheck:
    ok: bool
    reason: str


def check_reserve_eligibility(kind: str, indexer: str, daily_liquidity: bool, rate: float, fgc_covered: bool) -> ReserveCheck:
    if kind == "tesouro" and indexer == "selic":
        return ReserveCheck(True, "Tesouro Selic: liquidez diária e o menor risco do país.")
    if not daily_liquidity:
        return ReserveCheck(False, "Reserva de emergência precisa de liquidez diária.")
    if indexer != "cdi":
        return ReserveCheck(False, "Para a reserva, prefira pós-fixado (CDI ou Selic): não oscila de preço.")
    if rate < 100:
        return ReserveCheck(False, "Rende menos que 100% do CDI; o Tesouro Selic é melhor.")
    if not fgc_covered:
        return ReserveCheck(False, "Sem cobertura do FGC: risco desnecessário para a reserva.")
    return ReserveCheck(True, "Liquidez diária, ≥ 100% do CDI e coberto pelo FGC.")


def emergency_target(monthly_expenses: float, months: int) -> float:
    return monthly_expenses * months


def reserve_months_for(stability: str) -> int:
    return {"estavel": 6, "variavel": 9, "instavel": 12}.get(stability, 6)

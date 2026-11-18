"""Método Bazin (Décio Bazin, *Faça Fortuna com Ações*, 1992): comprar empresas que pagam pelo menos
6% ao ano em proventos, com pagamento regular e dívida moderada; vender quando o yield cai a 4%.

Fontes: resenha de Jean Tosetto (Suno, suno.com.br/?p=9561) e Investidor10. O livro não define a
medida de dívida; dívida líquida ÷ patrimônio ≤ 1 é escolha do app. Bancos e seguradoras não passam
pela regra de dívida, porque dívida é a matéria-prima do negócio deles.
"""

from typing import Any

from app.engine import fmt
from app.engine.acoes import FINANCEIRO, current_dy, rule_liquidez
from app.engine.config import merged_rules
from app.engine.metodos.base import MethodInfo, MetodoPorAtivo, Rules
from app.engine.score import build_evaluation
from app.engine.types import Evaluation, RuleResult, StockSnapshot, YearFundamentals

ENGINE_VERSION = "bazin-1.0"
PRICE_RULE = "bazin-yield"


def _na(base: dict[str, Any], explanation: str) -> RuleResult:
    return RuleResult(**base, status="na", value=None, value_display="sem dado", explanation=explanation)


def bazin_ceiling(s: StockSnapshot, yield_target: float) -> float | None:
    """Preço-teto de Bazin: proventos dos últimos 12 meses ÷ yield-alvo."""
    if not s.dividends_ttm:
        return None
    return s.dividends_ttm / yield_target


def rule_yield(s: StockSnapshot, c: Rules) -> RuleResult:
    """Regra de preço. Tem peso zero porque decide o veredito (comprar ou aguardar) sem rebaixar a nota,
    que mede só a qualidade: com poucas regras, um yield baixo puxaria uma boa empresa para "neutro"."""
    base = {
        "id": PRICE_RULE,
        "label": "Dividend yield dos últimos 12 meses",
        "learn_more": "metodo-bazin",
        "weight": 0,
        "group": "preco",
        "threshold": f"≥ {fmt.pct(c['bazin_yield_alvo'], 0)} ao ano",
    }
    dy = current_dy(s)
    if dy is None:
        return _na(base, "Precisa de preço atual e dos proventos dos últimos 12 meses.")
    shown = {"value": dy, "value_display": fmt.pct(dy)}
    if dy >= c["bazin_yield_alvo"]:
        return RuleResult(
            **base,
            **shown,
            status="ok",
            explanation=f"Pagou {fmt.pct(dy)} sobre o preço de hoje nos últimos 12 meses, acima dos {fmt.pct(c['bazin_yield_alvo'], 0)} que o Bazin exigia.",
        )
    return RuleResult(
        **base,
        **shown,
        status="fail",
        explanation=f"Pagou {fmt.pct(dy)} nos últimos 12 meses, abaixo de {fmt.pct(c['bazin_yield_alvo'], 0)}. Pela regra do Bazin, espere o preço cair.",
    )


def rule_venda(s: StockSnapshot, c: Rules) -> RuleResult:
    """Informativa (peso zero): Bazin vendia quando o yield caía abaixo de 4%. O app nunca sugere vender,
    só avisa."""
    base = {
        "id": "bazin-venda",
        "label": "Yield abaixo do ponto de venda",
        "learn_more": "metodo-bazin",
        "weight": 0,
        "group": "preco",
        "threshold": f"Bazin vendia abaixo de {fmt.pct(c['bazin_yield_venda'], 0)}",
    }
    dy = current_dy(s)
    if dy is None:
        return _na(base, "Precisa de preço atual e dos proventos dos últimos 12 meses.")
    shown = {"value": dy, "value_display": fmt.pct(dy)}
    if dy < c["bazin_yield_venda"]:
        return RuleResult(
            **base,
            **shown,
            status="warn",
            explanation=f"Yield de {fmt.pct(dy)}: o Bazin venderia. Só um aviso: o app não sugere vendas.",
        )
    return RuleResult(**base, **shown, status="ok", explanation="O yield está acima do ponto em que o Bazin venderia.")


def paid_every_year(s: StockSnapshot, years: int) -> tuple[int, int]:
    """Quantos dos últimos `years` anos completos tiveram proventos, e quantos anos foram olhados."""
    window = range(s.current_year - years, s.current_year)
    return sum(s.dividends_by_year.get(y, 0.0) > 0 for y in window), years


def rule_regularidade(s: StockSnapshot, c: Rules) -> RuleResult:
    years = int(c["bazin_anos_pagando"])
    base = {
        "id": "bazin-regularidade",
        "label": "Pagou proventos todo ano",
        "learn_more": "historico-proventos",
        "weight": 2,
        "eliminatory": True,
        "threshold": f"pagou em cada um dos últimos {fmt.years(years)}",
    }
    if not s.dividends_by_year:
        return _na(base, "Histórico de proventos ainda não carregado.")
    paid, looked = paid_every_year(s, years)
    shown = {"value": float(paid), "value_display": f"{paid} de {looked} anos"}
    if paid == looked:
        return RuleResult(**base, **shown, status="ok", explanation=f"Pagou proventos em todos os últimos {fmt.years(looked)}.")
    return RuleResult(
        **base,
        **shown,
        status="fail",
        explanation=f"Pagou em {paid} dos últimos {fmt.years(looked)}. O Bazin só comprava quem paga com regularidade — regra eliminatória.",
    )


def latest_balance(s: StockSnapshot) -> YearFundamentals | None:
    """Balanço mais recente com dívida e patrimônio."""
    usable = [f for f in s.fundamentals.values() if f.net_debt is not None and f.equity]
    return max(usable, key=lambda f: f.year, default=None)


def rule_divida(s: StockSnapshot, c: Rules) -> RuleResult:
    base = {
        "id": "bazin-divida",
        "label": "Dívida líquida ÷ patrimônio",
        "learn_more": "metodo-bazin",
        "weight": 2,
        "threshold": f"≤ {fmt.num(c['bazin_divida_pl_max'], 1)} (escolha do app)",
    }
    f = latest_balance(s)
    if f is None or f.net_debt is None or not f.equity:
        return _na(base, "Balanços ainda não carregados.")
    ratio = f.net_debt / f.equity
    shown = {"value": ratio, "value_display": fmt.num(ratio)}
    if ratio <= c["bazin_divida_pl_max"]:
        return RuleResult(
            **base,
            **shown,
            status="ok",
            explanation=f"Dívida líquida de {fmt.num(ratio)} vez o patrimônio em {f.year}: endividamento moderado.",
        )
    return RuleResult(
        **base,
        **shown,
        status="fail",
        explanation=f"Dívida líquida de {fmt.num(ratio)} vezes o patrimônio em {f.year}: a empresa deve mais do que vale para os sócios.",
    )


class Bazin(MetodoPorAtivo):
    info = MethodInfo(
        key="bazin",
        label="Bazin",
        author="Décio Bazin",
        summary="Empresas que pagam ao menos 6% ao ano em proventos, todo ano, com dívida moderada.",
        focus="renda",
    )

    def evaluate_one(self, snapshot: StockSnapshot, rules: Rules) -> Evaluation:
        c = merged_rules(dict(rules))
        checks = [rule_yield(snapshot, c), rule_regularidade(snapshot, c), rule_liquidez(snapshot, c)]
        if snapshot.sector not in FINANCEIRO:
            checks.append(rule_divida(snapshot, c))
        checks.append(rule_venda(snapshot, c))
        teto = bazin_ceiling(snapshot, c["bazin_yield_alvo"])
        margin = (teto - snapshot.price) / teto if teto and snapshot.price else None
        return build_evaluation(
            ticker=snapshot.ticker,
            rules=checks,
            cfg=c,
            price_rule_id=PRICE_RULE,
            has_core_data=snapshot.price is not None and snapshot.dividends_ttm is not None,
            ceiling=teto,
            margin=margin,
            dy=current_dy(snapshot),
            extras={"yield_alvo": c["bazin_yield_alvo"], "yield_venda": c["bazin_yield_venda"]},
            engine_version=ENGINE_VERSION,
        )

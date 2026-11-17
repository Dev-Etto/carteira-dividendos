"""Checklist de ETFs — liquidez, patrimônio, taxa de administração e distribuição de proventos.

ETFs replicam um índice: não há empresa para avaliar pelo método Barsi. O checklist só informa
se o fundo é negociável, grande e barato de manter, e se paga proventos (a maioria dos ETFs
brasileiros reinveste). O veredito é "evitar" quando reprova na liquidez e "neutro" nos demais
casos: quem escolhe os ETFs do aporte é o usuário, marcando favoritos.
"""

from typing import Any

from app.engine import fmt
from app.engine.acoes import Rules, grade
from app.engine.config import merged_rules
from app.engine.score import compute_score
from app.engine.types import EtfSnapshot, Evaluation, RuleResult, Verdict

ENGINE_VERSION = "etf-1.0"


def _na(base: dict[str, Any], explanation: str) -> RuleResult:
    return RuleResult(**base, status="na", value=None, value_display="sem dado", explanation=explanation)


def dividend_yield(s: EtfSnapshot) -> float | None:
    if not s.price or s.dividends_ttm is None:
        return None
    return s.dividends_ttm / s.price


def rule_liquidez(s: EtfSnapshot, c: Rules) -> RuleResult:
    base = {
        "id": "etf-liquidez",
        "label": "Liquidez",
        "learn_more": "liquidez",
        "weight": 2,
        "eliminatory": True,
        "threshold": f"≥ {fmt.brl(c['etf_liquidez_ok'])} por dia (mínimo {fmt.brl(c['etf_liquidez_min'])})",
    }
    v = s.avg_daily_volume_brl
    if v is None:
        return _na(base, "Histórico de negociação insuficiente (menos de 20 pregões).")
    status = grade(v >= c["etf_liquidez_ok"], v >= c["etf_liquidez_min"])
    exp = {
        "ok": "Negocia bastante: o preço acompanha de perto o valor do índice e dá para vender quando quiser.",
        "warn": "Negocia o suficiente, mas a diferença entre compra e venda pode pesar em ordens maiores.",
        "fail": "Negocia pouco: o preço pode se afastar do índice e vender pode ser difícil — regra eliminatória.",
    }[status]
    return RuleResult(**base, status=status, value=v, value_display=f"{fmt.brl(v)}/dia", explanation=exp)


def rule_patrimonio(s: EtfSnapshot, c: Rules) -> RuleResult:
    base = {
        "id": "etf-patrimonio",
        "label": "Tamanho do ETF",
        "learn_more": "etf",
        "weight": 1,
        "threshold": f"≥ {fmt.brl(c['etf_pl_ok'])} (mínimo {fmt.brl(c['etf_pl_min'])})",
    }
    if s.equity is None:
        return _na(base, "Patrimônio não encontrado no cadastro da CVM para este ETF.")
    status = grade(s.equity >= c["etf_pl_ok"], s.equity >= c["etf_pl_min"])
    exp = {
        "ok": "ETF grande: é menos provável que a gestora o encerre por falta de interesse.",
        "warn": "ETF de tamanho médio: funciona, mas acompanhe se continua crescendo.",
        "fail": "ETF pequeno: há risco de a gestora encerrá-lo e devolver o dinheiro numa hora ruim.",
    }[status]
    return RuleResult(**base, status=status, value=s.equity, value_display=fmt.brl(s.equity), explanation=exp)


def rule_taxa(s: EtfSnapshot, c: Rules) -> RuleResult:
    base = {
        "id": "etf-taxa-adm",
        "label": "Taxa de administração",
        "learn_more": "taxa-administracao",
        "weight": 2,
        "threshold": f"≤ {fmt.pct(c['etf_taxa_adm_ok'], 2)} ao ano (máximo {fmt.pct(c['etf_taxa_adm_max'], 2)})",
    }
    if s.admin_fee is None:
        return _na(base, "Informe a taxa na ficha do ETF: ela está no site da gestora.")
    status = grade(s.admin_fee <= c["etf_taxa_adm_ok"], s.admin_fee <= c["etf_taxa_adm_max"])
    exp = {
        "ok": "Taxa baixa: quase todo o retorno do índice fica com você.",
        "warn": "Taxa média: compare com outros ETFs do mesmo índice.",
        "fail": "Taxa alta para um ETF: em muitos anos, ela consome uma parte relevante do retorno.",
    }[status]
    return RuleResult(
        **base, status=status, value=s.admin_fee, value_display=f"{fmt.pct(s.admin_fee, 2)} ao ano", explanation=exp
    )


def rule_distribui(s: EtfSnapshot) -> RuleResult:
    base = {
        "id": "etf-distribui",
        "label": "Distribui proventos",
        "learn_more": "etf-distribui",
        "weight": 1,
        "threshold": "pagou proventos nos últimos 12 meses",
    }
    if s.dividends_ttm is None:
        return _na(base, "Histórico de proventos ainda não carregado.")
    if s.dividends_ttm > 0:
        dy = dividend_yield(s)
        exp = "Repassa os dividendos das empresas do índice: gera renda passiva em dinheiro."
        return RuleResult(**base, status="ok", value=dy, value_display=f"DY {fmt.pct(dy)}", explanation=exp)
    exp = "Reinveste os dividendos dentro do fundo: o retorno vem só da valorização da cota. Para renda mensal, prefira um que distribua."
    return RuleResult(**base, status="warn", value=0.0, value_display="reinveste", explanation=exp)


def _verdict(rules: list[RuleResult], has_price: bool) -> tuple[Verdict, str]:
    failed = [r for r in rules if r.eliminatory and r.status == "fail"]
    if failed:
        return "evitar", f"Reprovado em regra eliminatória: {failed[0].label.lower()}."
    if not has_price:
        return "neutro", "Dados insuficientes. Rode a atualização de dados."
    ok = sum(r.status == "ok" for r in rules)
    known = sum(r.status != "na" for r in rules)
    return "neutro", f"{ok} de {known} critérios ok. ETFs não recebem veredito de compra: o aporte usa os seus favoritos."


def evaluate_etf(s: EtfSnapshot, overrides: dict[str, float] | None = None) -> Evaluation:
    c = merged_rules(overrides)
    rules = [rule_liquidez(s, c), rule_patrimonio(s, c), rule_taxa(s, c), rule_distribui(s)]
    verdict, summary = _verdict(rules, s.price is not None)
    return Evaluation(
        ticker=s.ticker,
        score=compute_score(rules),
        verdict=verdict,
        summary=summary,
        dividend_yield=dividend_yield(s),
        rules=rules,
        extras={"patrimonio": s.equity, "taxa_adm_ano": s.admin_fee, "rendimentos_12m": s.dividends_ttm},
        engine_version=ENGINE_VERSION,
    )

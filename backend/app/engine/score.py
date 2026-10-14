"""Nota 0–100 e veredito, comuns a todas as classes de ativo."""

from app.engine.types import STATUS_POINTS, Evaluation, RuleResult, Verdict


def compute_score(rules: list[RuleResult]) -> int:
    scored = [r for r in rules if r.status != "na" and r.weight > 0]
    total = sum(r.weight for r in scored)
    if not total:
        return 0
    return round(100 * sum(r.weight * STATUS_POINTS[r.status] for r in scored) / total)


def decide_verdict(
    rules: list[RuleResult], score: int, cfg: dict[str, float], price_rule_id: str, has_core_data: bool
) -> tuple[Verdict, str]:
    failed_elim = [r for r in rules if r.eliminatory and r.status == "fail"]
    if failed_elim:
        return "evitar", f"Reprovado em regra eliminatória: {failed_elim[0].label.lower()}."
    if not has_core_data:
        return "neutro", "Dados insuficientes para um veredito. Rode a atualização de dados."
    price_rule = next((r for r in rules if r.id == price_rule_id), None)
    price_above_limit = price_rule is not None and price_rule.status == "fail"
    if score < cfg["nota_evitar"]:
        return "evitar", f"Nota {score}: muitos critérios de qualidade não foram atendidos."
    if score >= cfg["nota_comprar"] and price_above_limit:
        return "aguardar", f"Nota {score}: bom ativo, mas o preço está acima do limite. Vale esperar."
    if score >= cfg["nota_comprar"]:
        return "comprar", f"Nota {score}: passa nos critérios e o preço está dentro do limite."
    return "neutro", f"Nota {score}: ativo mediano pelos critérios do método."


def build_evaluation(
    *,
    ticker: str,
    rules: list[RuleResult],
    cfg: dict[str, float],
    price_rule_id: str,
    has_core_data: bool,
    ceiling: float | None,
    margin: float | None,
    dy: float | None,
    extras: dict,
    engine_version: str,
) -> Evaluation:
    score = compute_score(rules)
    verdict, summary = decide_verdict(rules, score, cfg, price_rule_id, has_core_data)
    missing = sum(r.status == "na" for r in rules)
    if missing and verdict != "evitar":
        summary += f" {missing} critério(s) sem dado não entraram na nota."
    return Evaluation(
        ticker=ticker,
        score=score,
        verdict=verdict,
        summary=summary,
        ceiling_price=ceiling,
        margin_pct=margin,
        dividend_yield=dy,
        rules=rules,
        extras=extras,
        engine_version=engine_version,
    )

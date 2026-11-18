"""Método Graham: os critérios do investidor defensivo (Benjamin Graham, *O Investidor Inteligente*,
cap. 14) com a adaptação ao Brasil de Palazzo et al. (Revista de Contabilidade e Finanças, USP, 2018).

O livro exige 10 anos de lucro e 20 de dividendos, o que elimina quase todo o mercado brasileiro e
os dados abertos da CVM, que começam em 2010; a adaptação usa 5 anos. O P/L máximo de 15 foi pensado
para os juros americanos de 1972; o app liga o P/L máximo ao juro real do Tesouro IPCA+ (1 ÷ juro
real), podendo voltar ao fixo em Configurações. O valor de Graham, √(22,5 × LPA × VPA), não está no
livro: deriva do critério P/L × P/VP ≤ 22,5. Bancos e seguradoras não passam pela liquidez corrente,
porque o balanço deles não separa circulante.
"""

from statistics import mean
from typing import Any

from app.engine import fmt
from app.engine.acoes import FINANCEIRO, consecutive_paying_years, current_dy, graham_value, rule_liquidez
from app.engine.config import merged_rules
from app.engine.metodos.base import MethodInfo, MetodoPorAtivo, Rules
from app.engine.score import build_evaluation
from app.engine.types import Evaluation, RuleResult, StockSnapshot, YearFundamentals

ENGINE_VERSION = "graham-1.0"
PRICE_RULE = "graham-preco"
GROWTH_WINDOW = 3
"""Anos de cada ponta na comparação do lucro: média dos 3 mais antigos × média dos 3 mais recentes."""


def _na(base: dict[str, Any], explanation: str) -> RuleResult:
    return RuleResult(**base, status="na", value=None, value_display="sem dado", explanation=explanation)


def _years(s: StockSnapshot) -> list[YearFundamentals]:
    return [s.fundamentals[y] for y in sorted(s.fundamentals) if y < s.current_year]


def _latest(s: StockSnapshot) -> YearFundamentals | None:
    years = _years(s)
    return years[-1] if years else None


def rule_tamanho(s: StockSnapshot, c: Rules) -> RuleResult:
    base = {
        "id": "graham-tamanho",
        "label": "Tamanho (receita anual)",
        "learn_more": "metodo-graham",
        "weight": 1,
        "threshold": f"> {fmt.brl(c['graham_receita_min'])}",
    }
    f = _latest(s)
    if f is None or f.revenue is None:
        return _na(base, "Balanços ainda não carregados.")
    shown = {"value": f.revenue, "value_display": fmt.brl(f.revenue)}
    if f.revenue > c["graham_receita_min"]:
        return RuleResult(
            **base, **shown, status="ok", explanation=f"Receita de {fmt.brl(f.revenue)} em {f.year}: empresa grande o bastante."
        )
    return RuleResult(
        **base,
        **shown,
        status="fail",
        explanation=f"Receita de {fmt.brl(f.revenue)} em {f.year}: pequena para o investidor defensivo.",
    )


def rule_liquidez_corrente(s: StockSnapshot, c: Rules) -> RuleResult:
    base = {
        "id": "graham-liquidez-corrente",
        "label": "Liquidez corrente",
        "learn_more": "liquidez-corrente",
        "weight": 2,
        "threshold": f"ativo circulante ≥ {fmt.num(c['graham_liquidez_corrente_min'])} × passivo circulante",
    }
    f = _latest(s)
    if f is None or not f.current_assets or not f.current_liabilities:
        return _na(base, "Ativo e passivo circulante ainda não carregados.")
    ratio = f.current_assets / f.current_liabilities
    shown = {"value": ratio, "value_display": fmt.num(ratio)}
    if ratio >= c["graham_liquidez_corrente_min"]:
        return RuleResult(
            **base,
            **shown,
            status="ok",
            explanation=f"Para cada R$ 1 que vence em um ano, tem {fmt.brl(ratio)} a receber ou em caixa.",
        )
    return RuleResult(
        **base,
        **shown,
        status="fail",
        explanation=f"Tem só {fmt.brl(ratio)} de curto prazo para cada R$ 1 que vence em um ano: folga financeira apertada.",
    )


def rule_lucro(s: StockSnapshot, c: Rules) -> RuleResult:
    years = int(c["graham_anos_lucro"])
    base = {
        "id": "graham-lucro",
        "label": "Lucro em todos os anos",
        "learn_more": "lucro",
        "weight": 2,
        "eliminatory": True,
        "threshold": f"lucro em cada um dos últimos {fmt.years(years)}",
    }
    recent = [f for f in _years(s) if f.net_income is not None][-years:]
    if len(recent) < years:
        return _na(base, f"Precisa de {fmt.years(years)} de balanços; há {len(recent)}.")
    losses = [f.year for f in recent if (f.net_income or 0) <= 0]
    shown = {"value": float(years - len(losses)), "value_display": f"{years - len(losses)} de {years} anos"}
    if not losses:
        return RuleResult(**base, **shown, status="ok", explanation=f"Lucrou em todos os últimos {fmt.years(years)}.")
    listed = ", ".join(str(y) for y in losses)
    return RuleResult(
        **base,
        **shown,
        status="fail",
        explanation=f"Teve prejuízo em {listed}. O investidor defensivo evita — regra eliminatória.",
    )


def rule_proventos(s: StockSnapshot, c: Rules) -> RuleResult:
    years = int(c["graham_anos_proventos"])
    base = {
        "id": "graham-proventos",
        "label": "Proventos sem interrupção",
        "learn_more": "historico-proventos",
        "weight": 2,
        "threshold": f"≥ {fmt.years(years)} seguidos",
    }
    if not s.dividends_by_year:
        return _na(base, "Histórico de proventos ainda não carregado.")
    paid = consecutive_paying_years(s)
    shown = {"value": float(paid), "value_display": fmt.years(paid)}
    if paid >= years:
        return RuleResult(**base, **shown, status="ok", explanation=f"Pagou proventos nos últimos {fmt.years(paid)} sem falhar.")
    return RuleResult(**base, **shown, status="fail", explanation=f"Pagou só nos últimos {fmt.years(paid)} seguidos.")


def profit_growth(s: StockSnapshot) -> tuple[float, int, int] | None:
    """Crescimento anual composto do lucro entre a média dos 3 anos mais antigos e a dos 3 mais recentes,
    com os anos de início e fim. Precisa de 6 anos e de lucro médio positivo na ponta antiga."""
    profits = [(f.year, f.net_income) for f in _years(s) if f.net_income is not None]
    if len(profits) < 2 * GROWTH_WINDOW:
        return None
    old = mean(v for _, v in profits[:GROWTH_WINDOW])
    new = mean(v for _, v in profits[-GROWTH_WINDOW:])
    span = len(profits) - GROWTH_WINDOW
    if old <= 0 or new <= 0:
        return None
    return (new / old) ** (1 / span) - 1, profits[0][0], profits[-1][0]


def rule_crescimento(s: StockSnapshot, c: Rules) -> RuleResult:
    base = {
        "id": "graham-crescimento",
        "label": "Crescimento do lucro",
        "learn_more": "metodo-graham",
        "weight": 1,
        "threshold": f"≥ {fmt.pct(c['graham_crescimento_min'], 2)} ao ano",
    }
    growth = profit_growth(s)
    if growth is None:
        return _na(base, "Precisa de 6 anos de balanços com lucro médio positivo.")
    rate, start, end = growth
    shown = {"value": rate, "value_display": f"{fmt.pct(rate)} ao ano"}
    if rate >= c["graham_crescimento_min"]:
        return RuleResult(
            **base, **shown, status="ok", explanation=f"O lucro cresceu {fmt.pct(rate)} ao ano entre {start} e {end}."
        )
    return RuleResult(
        **base, **shown, status="fail", explanation=f"O lucro variou {fmt.pct(rate)} ao ano entre {start} e {end}: cresceu pouco."
    )


def max_pe(s: StockSnapshot, c: Rules) -> tuple[float, str]:
    """P/L máximo e de onde ele veio: 1 ÷ juro real do Tesouro IPCA+, ou o fixo quando o usuário desliga
    essa opção ou o juro real não está disponível."""
    linked = c["graham_pl_ligado_juros"] >= 1 and s.ntnb_real is not None and s.ntnb_real > 0
    if linked and s.ntnb_real is not None:
        return 1 / s.ntnb_real, f"1 ÷ juro real de {fmt.pct(s.ntnb_real)}"
    return c["graham_pl_max"], "fixo"


def multiples(s: StockSnapshot) -> tuple[float, float] | None:
    """P/L sobre o lucro médio de 3 anos e P/VP sobre o último patrimônio."""
    years = _years(s)
    profits = [f.net_income for f in years[-GROWTH_WINDOW:] if f.net_income is not None]
    latest = years[-1] if years else None
    if not s.price or not s.shares_outstanding or len(profits) < GROWTH_WINDOW or latest is None or not latest.equity:
        return None
    avg_profit = mean(profits)
    if avg_profit <= 0 or latest.equity <= 0:
        return None
    market_cap = s.price * s.shares_outstanding
    return market_cap / avg_profit, market_cap / latest.equity


def rule_preco(s: StockSnapshot, c: Rules) -> RuleResult:
    """Regra de preço. Peso zero: decide entre comprar e aguardar sem rebaixar a nota de qualidade."""
    pe_limit, origin = max_pe(s, c)
    base = {
        "id": PRICE_RULE,
        "label": "P/L e P/L × P/VP",
        "learn_more": "metodo-graham",
        "weight": 0,
        "group": "preco",
        "threshold": f"P/L ≤ {fmt.num(pe_limit, 1)} ({origin}) e P/L × P/VP ≤ {fmt.num(c['graham_pl_x_pvp_max'], 1)}",
    }
    m = multiples(s)
    if m is None:
        return _na(base, "Precisa de preço, número de ações, 3 anos de lucro positivo e patrimônio positivo.")
    pe, pb = m
    product = pe * pb
    shown = {"value": product, "value_display": f"P/L {fmt.num(pe, 1)} · P/VP {fmt.num(pb)}"}
    checks = [
        (pe > pe_limit, f"P/L de {fmt.num(pe, 1)} acima de {fmt.num(pe_limit, 1)}"),
        (
            product > c["graham_pl_x_pvp_max"],
            f"P/L × P/VP de {fmt.num(product, 1)} acima de {fmt.num(c['graham_pl_x_pvp_max'], 1)}",
        ),
    ]
    problems = [message for broken, message in checks if broken]
    if not problems:
        return RuleResult(
            **base,
            **shown,
            status="ok",
            explanation=f"P/L de {fmt.num(pe, 1)} e P/L × P/VP de {fmt.num(product, 1)}: preço defensivo.",
        )
    return RuleResult(**base, **shown, status="fail", explanation=f"{'; '.join(problems)}. Pelo Graham, espere o preço cair.")


class Graham(MetodoPorAtivo):
    info = MethodInfo(
        key="graham",
        label="Graham",
        author="Benjamin Graham",
        summary="Empresas grandes, com folga financeira, lucro e proventos estáveis, compradas a múltiplos baixos.",
        focus="valor",
    )

    def evaluate_one(self, snapshot: StockSnapshot, rules: Rules) -> Evaluation:
        c = merged_rules(dict(rules))
        checks = [rule_tamanho(snapshot, c)]
        if snapshot.sector not in FINANCEIRO:
            checks.append(rule_liquidez_corrente(snapshot, c))
        checks += [
            rule_lucro(snapshot, c),
            rule_proventos(snapshot, c),
            rule_crescimento(snapshot, c),
            rule_liquidez(snapshot, c),
            rule_preco(snapshot, c),
        ]
        teto = graham_value(snapshot, c["graham_pl_x_pvp_max"])
        margin = (teto - snapshot.price) / teto if teto and snapshot.price else None
        pe_limit, _ = max_pe(snapshot, c)
        return build_evaluation(
            ticker=snapshot.ticker,
            rules=checks,
            cfg=c,
            price_rule_id=PRICE_RULE,
            has_core_data=snapshot.price is not None and bool(snapshot.fundamentals),
            ceiling=teto,
            margin=margin,
            dy=current_dy(snapshot),
            extras={"pl_max": pe_limit, "juro_real": snapshot.ntnb_real},
            engine_version=ENGINE_VERSION,
        )

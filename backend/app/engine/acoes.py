"""Motor de avaliação de ações — método Barsi + regras setoriais + sustentabilidade.

Cada regra devolve um RuleResult com status, valor, limite e uma explicação em
linguagem simples. Nenhuma regra acessa banco ou rede.

As regras seguem o mesmo formato: guardas para dado ausente ("sem dado"), depois uma
função `_avalia_*` que devolve (status, explicação) com retorno antecipado por faixa.
"""

import math
from collections.abc import Callable
from statistics import mean
from typing import Any

from app.engine import fmt
from app.engine.config import merged_rules
from app.engine.score import build_evaluation
from app.engine.types import Evaluation, RuleResult, RuleStatus, StockSnapshot, YearFundamentals

ENGINE_VERSION = "acoes-1.0"

BEST = {"bancos", "seguros", "energia", "saneamento", "telecom"}
FINANCEIRO = {"bancos", "seguros"}
ALAVANCADOS = {"energia", "saneamento"}

SECTOR_LABEL = {
    "bancos": "Bancos",
    "seguros": "Seguros",
    "energia": "Energia elétrica",
    "saneamento": "Saneamento",
    "telecom": "Telecomunicações",
    "perene": "Setor perene (fora do BEST)",
    "ciclico": "Setor cíclico",
}

BALANCOS_AUSENTES = "Balanços ainda não carregados."
INDICADOR_SETORIAL_AUSENTE = "Indicador setorial ainda não cadastrado (data/sector_metrics.csv)."

Assessment = tuple[RuleStatus, str]
Rules = dict[str, float]


def _rule(**kw: Any) -> RuleResult:
    return RuleResult(**kw)


def _na(base: dict[str, Any], explanation: str) -> RuleResult:
    return RuleResult(**base, status="na", value=None, value_display="sem dado", explanation=explanation)


def grade(ok: bool, warn: bool) -> RuleStatus:
    """Status de uma faixa: ok se a condição ideal vale, warn se a mínima vale, senão fail."""
    if ok:
        return "ok"
    if warn:
        return "warn"
    return "fail"


def _last_full_years(snap: StockSnapshot, n: int) -> list[int]:
    last = snap.current_year - 1
    return list(range(last - n + 1, last + 1))


def _recent_fundamentals(snap: StockSnapshot, n: int) -> list[YearFundamentals]:
    ys = sorted(snap.fundamentals)[-n:]
    return [snap.fundamentals[y] for y in ys]


def percentile_of(value: float, series: list[float]) -> float:
    """Percentual de valores da série menores ou iguais ao valor (0–100)."""
    if not series:
        return math.nan
    below = sum(1 for v in series if v <= value)
    return 100.0 * below / len(series)


def _avalia_setor(sector: str, label: str) -> Assessment:
    if sector in BEST:
        return (
            "ok",
            f"{label} faz parte do BEST, setores que o Barsi considera perenes: as pessoas precisam desses serviços em qualquer cenário.",
        )
    if sector == "perene":
        return "warn", "Setor com demanda estável, mas fora do BEST clássico do Barsi."
    return (
        "fail",
        "Setor cíclico: lucros e dividendos sobem e descem muito com a economia, o que dificulta uma renda previsível.",
    )


def rule_setor(s: StockSnapshot) -> RuleResult:
    label = SECTOR_LABEL.get(s.sector, s.sector)
    status, exp = _avalia_setor(s.sector, label)
    return _rule(
        id="setor-perene",
        label="Setor perene",
        status=status,
        value=None,
        value_display=label,
        threshold="BEST: bancos, energia, seguros, saneamento, telecom",
        explanation=exp,
        learn_more="besst",
        weight=2,
    )


def consecutive_paying_years(s: StockSnapshot) -> int:
    count = 0
    year = s.current_year - 1
    while s.dividends_by_year.get(year, 0) > 0:
        count += 1
        year -= 1
    return count


def _avalia_historico(n: int, c: Rules) -> Assessment:
    if n >= c["proventos_anos_ok"]:
        return (
            "ok",
            f"Pagou proventos em todos os últimos {fmt.years(n)}. Isso mostra compromisso com o acionista ao longo de vários ciclos econômicos.",
        )
    if n >= c["proventos_anos_min"]:
        return "warn", f"Paga há {fmt.years(n)} seguidos. É bom, mas ainda não atravessou muitos ciclos."
    return (
        "fail",
        f"Só {fmt.years(n)} seguidos pagando proventos. Para uma carteira de renda, é pouco histórico — regra eliminatória.",
    )


def rule_historico(s: StockSnapshot, c: Rules) -> RuleResult:
    base = {
        "id": "historico-proventos",
        "label": "Histórico de proventos",
        "learn_more": "historico-proventos",
        "weight": 3,
        "eliminatory": True,
        "threshold": f"≥ {int(c['proventos_anos_ok'])} anos seguidos (mínimo {int(c['proventos_anos_min'])})",
    }
    if not s.dividends_by_year:
        return _na(base, "Ainda não há histórico de proventos carregado para este ativo.")
    n = consecutive_paying_years(s)
    status, exp = _avalia_historico(n, c)
    return _rule(**base, status=status, value=float(n), value_display=fmt.years(n), explanation=exp)


def _avalia_consistencia(drops: list[int]) -> Assessment:
    if not drops:
        return "ok", "Os proventos não tiveram nenhuma queda forte nos últimos 5 anos."
    if len(drops) == 1:
        return "warn", f"Houve 1 queda forte (em {drops[0]}). Vale entender se foi pontual."
    return "fail", f"Quedas fortes em {', '.join(map(str, drops))}. A renda dessa empresa oscila bastante."


def rule_consistencia(s: StockSnapshot, c: Rules) -> RuleResult:
    base = {
        "id": "consistencia-proventos",
        "label": "Consistência dos proventos",
        "learn_more": "consistencia-proventos",
        "weight": 2,
        "threshold": f"nenhuma queda > {fmt.pct(c['queda_forte'], 0)} nos últimos 5 anos",
    }
    ys = _last_full_years(s, 6)
    vals = [s.dividends_by_year.get(y) for y in ys]
    if sum(v is not None and v > 0 for v in vals) < 3:
        return _na(base, "Histórico curto demais para medir a consistência.")
    drops = [
        y
        for prev, cur, y in zip(vals, vals[1:], ys[1:], strict=False)
        if prev and prev > 0 and (cur or 0) < prev * (1 - c["queda_forte"])
    ]
    status, exp = _avalia_consistencia(drops)
    n = len(drops)
    return _rule(**base, status=status, value=float(n), value_display=f"{n} queda(s)", explanation=exp)


def _avalia_lucro(losses: list[int], years_analysed: int) -> Assessment:
    if not losses:
        return "ok", f"Lucrou em todos os {years_analysed} anos analisados. Dividendo sai do lucro."
    if len(losses) == 1:
        return "warn", f"Teve prejuízo em {losses[0]}."
    return "fail", f"Prejuízo em {', '.join(map(str, losses))}. Sem lucro, o dividendo não se sustenta."


def rule_lucro(s: StockSnapshot) -> RuleResult:
    base = {
        "id": "lucro",
        "label": "Lucro nos últimos 5 anos",
        "learn_more": "lucro",
        "weight": 2,
        "threshold": "nenhum ano com prejuízo",
    }
    fs = [f for f in _recent_fundamentals(s, 5) if f.net_income is not None]
    if len(fs) < 3:
        return _na(base, BALANCOS_AUSENTES)
    losses = [f.year for f in fs if (f.net_income or 0) < 0]
    status, exp = _avalia_lucro(losses, len(fs))
    return _rule(
        **base, status=status, value=float(len(losses)), value_display=f"{len(losses)} ano(s) com prejuízo", explanation=exp
    )


def avg_roe(s: StockSnapshot) -> float | None:
    vals = [f.net_income / f.equity for f in _recent_fundamentals(s, 5) if f.net_income is not None and f.equity and f.equity > 0]
    return mean(vals) if len(vals) >= 3 else None


def _avalia_roe(roe: float, c: Rules) -> Assessment:
    if roe >= c["roe_ok"]:
        return "ok", f"Para cada R$ 100 de patrimônio, a empresa gera em média {fmt.pct(roe)} de lucro por ano. Muito eficiente."
    if roe >= c["roe_min"]:
        return "warn", f"ROE médio de {fmt.pct(roe)}: razoável, mas abaixo do ideal."
    return "fail", f"ROE médio de {fmt.pct(roe)}: a empresa rende pouco sobre o capital dos sócios."


def rule_roe(s: StockSnapshot, c: Rules) -> RuleResult:
    base = {
        "id": "roe-5a",
        "label": "Rentabilidade (ROE médio 5 anos)",
        "learn_more": "roe",
        "weight": 2,
        "threshold": f"≥ {fmt.pct(c['roe_ok'], 0)} (mínimo {fmt.pct(c['roe_min'], 0)})",
    }
    roe = avg_roe(s)
    if roe is None:
        return _na(base, BALANCOS_AUSENTES)
    status, exp = _avalia_roe(roe, c)
    return _rule(**base, status=status, value=roe, value_display=fmt.pct(roe), explanation=exp)


def _avalia_endividamento(ratio: float, ok: float, mx: float) -> Assessment:
    if ratio < ok:
        return "ok", f"Levaria {fmt.num(ratio, 1)} anos de geração de caixa para quitar a dívida. Confortável."
    if ratio <= mx:
        return "warn", f"Dívida equivale a {fmt.num(ratio, 1)} anos de geração de caixa. Atenção se os juros subirem."
    return (
        "fail",
        f"Dívida equivale a {fmt.num(ratio, 1)} anos de geração de caixa: alta. Juros da dívida competem com os dividendos.",
    )


def rule_endividamento(s: StockSnapshot, c: Rules) -> RuleResult:
    alav = s.sector in ALAVANCADOS
    ok, mx = (c["divida_alavancado_ok"], c["divida_alavancado_max"]) if alav else (c["divida_ok"], c["divida_max"])
    base = {
        "id": "endividamento",
        "label": "Endividamento (dívida líquida ÷ EBITDA)",
        "learn_more": "divida-ebitda",
        "weight": 2,
        "group": "setorial" if alav else "qualidade",
        "threshold": f"< {fmt.num(ok, 1)} (máximo {fmt.num(mx, 1)})" + (" — limite de setor regulado" if alav else ""),
    }
    fs = _recent_fundamentals(s, 1)
    f = fs[0] if fs else None
    if f is None or f.net_debt is None or f.ebitda is None:
        return _na(base, "Balanço ainda não carregado.")
    if f.net_debt <= 0:
        return _rule(
            **base,
            status="ok",
            value=f.net_debt / f.ebitda if f.ebitda else 0.0,
            value_display="caixa líquido",
            explanation="A empresa tem mais dinheiro em caixa do que dívidas. Excelente.",
        )
    if f.ebitda <= 0:
        return _rule(
            **base,
            status="fail",
            value=None,
            value_display="EBITDA negativo",
            explanation="A operação não está gerando caixa para pagar a dívida.",
        )
    ratio = f.net_debt / f.ebitda
    status, exp = _avalia_endividamento(ratio, ok, mx)
    return _rule(**base, status=status, value=ratio, value_display=f"{fmt.num(ratio, 1)}x", explanation=exp)


def avg_payout(s: StockSnapshot, n: int = 5) -> float | None:
    fs = [f for f in _recent_fundamentals(s, n) if f.net_income and f.dividends_paid is not None]
    ni = sum(f.net_income or 0 for f in fs)
    dp = sum(abs(f.dividends_paid or 0) for f in fs)
    if len(fs) < 3 or ni <= 0:
        return None
    return dp / ni


def _avalia_payout(p: float, c: Rules) -> Assessment:
    if c["payout_min"] <= p <= c["payout_ok_max"]:
        return "ok", f"Distribui {fmt.pct(p, 0)} do lucro e reinveste o resto para crescer. Equilíbrio saudável."
    if p < c["payout_min"]:
        return "warn", f"Distribui só {fmt.pct(p, 0)} do lucro. Pode ser bom para crescimento, mas rende pouco como renda."
    if p <= c["payout_max"]:
        return "warn", f"Distribui {fmt.pct(p, 0)} do lucro: quase tudo. Pouca margem se o lucro cair."
    return "fail", f"Distribui {fmt.pct(p, 0)} do lucro — mais do que ganha. Isso não se sustenta por muito tempo."


def rule_payout(s: StockSnapshot, c: Rules) -> RuleResult:
    base = {
        "id": "payout-5a",
        "label": "Payout médio (proventos ÷ lucro)",
        "learn_more": "payout",
        "weight": 1,
        "threshold": f"{fmt.pct(c['payout_min'], 0)} a {fmt.pct(c['payout_ok_max'], 0)}",
    }
    p = avg_payout(s)
    if p is None:
        return _na(base, BALANCOS_AUSENTES)
    status, exp = _avalia_payout(p, c)
    return _rule(**base, status=status, value=p, value_display=fmt.pct(p, 0), explanation=exp)


def _avalia_liquidez(v: float, c: Rules) -> Assessment:
    if v >= c["liquidez_ok"]:
        return "ok", f"Negocia {fmt.brl(v)} por dia em média. Você compra e vende fácil, sem mexer no preço."
    if v >= c["liquidez_min"]:
        return "warn", f"Negocia {fmt.brl(v)} por dia. Dá para operar, mas em dias calmos pode ser difícil vender."
    return "fail", f"Negocia só {fmt.brl(v)} por dia. Pouca liquidez — regra eliminatória."


def rule_liquidez(s: StockSnapshot, c: Rules) -> RuleResult:
    base = {
        "id": "liquidez",
        "label": "Liquidez (volume médio diário)",
        "learn_more": "liquidez",
        "weight": 1,
        "eliminatory": True,
        "threshold": f"≥ {fmt.brl(c['liquidez_ok'])} (mínimo {fmt.brl(c['liquidez_min'])})",
    }
    v = s.avg_daily_volume_brl
    if v is None:
        return _na(base, "Histórico de negociação ainda não carregado.")
    status, exp = _avalia_liquidez(v, c)
    return _rule(**base, status=status, value=v, value_display=fmt.brl(v), explanation=exp)


def linked_yield(fixed: float, linked: float, real_rate: float | None) -> float:
    """Yield-alvo efetivo. Barsi e Bazin usavam 6% nominal, calibrado para o Brasil de 1970–1990; com a
    opção ligada (linked ≥ 1), o alvo passa a ser o maior entre o fixo e o juro real do Tesouro IPCA+,
    para o dividendo render ao menos o que a renda fixa sem risco já paga acima da inflação."""
    if linked < 1 or real_rate is None:
        return fixed
    return max(fixed, real_rate)


def with_linked_yields(c: Rules, s: StockSnapshot) -> Rules:
    """Limites com os yields-alvo do Barsi e do Bazin já ajustados ao juro real, quando a opção está ligada.
    O yield exigente nunca fica abaixo do normal."""
    target = linked_yield(c["yield_alvo"], c["yield_ligado_juros"], s.ntnb_real)
    return c | {
        "yield_alvo": target,
        "yield_alvo_exigente": max(c["yield_alvo_exigente"], target),
        "bazin_yield_alvo": linked_yield(c["bazin_yield_alvo"], c["bazin_yield_ligado_juros"], s.ntnb_real),
    }


def ceiling_price(s: StockSnapshot, yield_target: float) -> float | None:
    vals = [s.dividends_by_year.get(y, 0.0) for y in _last_full_years(s, 5)]
    if sum(v > 0 for v in vals) < 3:
        return None
    return mean(vals) / yield_target


def _avalia_preco_teto(price: float, teto: float, margin: float, c: Rules) -> Assessment:
    if margin >= c["margem_ok"]:
        return (
            "ok",
            f"Preço de {fmt.brl(price)} está {fmt.pct(margin)} abaixo do teto de {fmt.brl(teto)}. Comprando aqui, a média de proventos dos últimos 5 anos renderia mais de {fmt.pct(c['yield_alvo'], 0)} ao ano.",
        )
    if margin >= 0:
        return (
            "warn",
            f"Preço de {fmt.brl(price)} está abaixo do teto de {fmt.brl(teto)}, mas com pouca margem de segurança ({fmt.pct(margin)}).",
        )
    return (
        "fail",
        f"Preço de {fmt.brl(price)} está {fmt.pct(-margin)} acima do teto de {fmt.brl(teto)}. Pela regra do Barsi, é melhor esperar.",
    )


def rule_preco_teto(s: StockSnapshot, c: Rules) -> tuple[RuleResult, float | None, float | None]:
    base = {
        "id": "preco-teto",
        "label": "Preço × preço-teto (Barsi)",
        "learn_more": "preco-teto",
        "weight": 3,
        "group": "preco",
        "threshold": f"margem ≥ {fmt.pct(c['margem_ok'], 0)} abaixo do teto (yield-alvo {fmt.pct(c['yield_alvo'], 0)})",
    }
    teto = ceiling_price(s, c["yield_alvo"])
    if teto is None or s.price is None:
        return _na(base, "Precisa de preço atual e de pelo menos 3 anos de proventos."), teto, None
    margin = (teto - s.price) / teto
    status, exp = _avalia_preco_teto(s.price, teto, margin, c)
    return _rule(**base, status=status, value=margin, value_display=f"margem {fmt.pct(margin)}", explanation=exp), teto, margin


def current_dy(s: StockSnapshot) -> float | None:
    if s.price and s.dividends_ttm is not None:
        return s.dividends_ttm / s.price
    return None


def avg_dy_5y(s: StockSnapshot) -> float | None:
    vals = [
        d / p for d, p in ((s.dividends_by_year.get(y), s.avg_price_by_year.get(y)) for y in _last_full_years(s, 5)) if d and p
    ]
    return mean(vals) if len(vals) >= 3 else None


def _avalia_dy_anormal(r: float, c: Rules) -> Assessment:
    if r < c["dy_anormal_alerta"]:
        return "ok", "O yield atual está dentro do padrão histórico da empresa."
    if r <= c["dy_anormal_max"]:
        return (
            "warn",
            f"Yield {fmt.num(r, 1)}× acima da média. Pode ser provento extraordinário ou queda do preço — vale investigar.",
        )
    return (
        "fail",
        f"Yield {fmt.num(r, 1)}× acima da média. Isso costuma indicar provento que não vai se repetir ou um problema derrubando o preço.",
    )


def rule_dy_anormal(s: StockSnapshot, c: Rules) -> RuleResult:
    base = {
        "id": "dy-anormal",
        "label": "Dividend yield fora do normal",
        "learn_more": "dy-anormal",
        "weight": 1,
        "group": "preco",
        "threshold": f"DY atual < {fmt.num(c['dy_anormal_alerta'], 1)}× a média de 5 anos",
    }
    dy, avg = current_dy(s), avg_dy_5y(s)
    if dy is None or avg is None or avg <= 0:
        return _na(base, "Dados insuficientes para comparar.")
    r = dy / avg
    status, exp = _avalia_dy_anormal(r, c)
    return _rule(**base, status=status, value=r, value_display=f"{fmt.pct(dy)} hoje × {fmt.pct(avg)} na média", explanation=exp)


def _avalia_barato_si(percentile: float, multiple: str, c: Rules) -> Assessment:
    if percentile <= c["percentil_barato"]:
        return (
            "ok",
            f"O {multiple} atual está entre os mais baixos dos últimos 5 anos: barato em relação ao próprio histórico.",
        )
    if percentile <= c["percentil_caro"]:
        return "warn", f"O {multiple} atual está na faixa intermediária do histórico."
    return "fail", f"O {multiple} atual está entre os mais altos dos últimos 5 anos: caro em relação ao próprio histórico."


def rule_barato_si(s: StockSnapshot, c: Rules) -> RuleResult:
    use_pb = s.sector == "bancos"
    name = "P/VP" if use_pb else "P/L"
    series = s.pb_history if use_pb else s.pe_history
    base = {
        "id": "barato-vs-historico",
        "label": f"Barato em relação a si mesmo ({name})",
        "learn_more": "percentil",
        "weight": 1,
        "group": "preco",
        "threshold": f"{name} entre os {int(c['percentil_barato'])}% menores dos últimos 5 anos",
    }
    valid = [v for v in series if v > 0]
    if len(valid) < 24 or s.price is None:
        return _na(base, "Histórico de múltiplos ainda curto.")
    current = valid[-1]
    p = percentile_of(current, valid)
    status, exp = _avalia_barato_si(p, name, c)
    return _rule(
        **base, status=status, value=p, value_display=f"{name} {fmt.num(current, 1)} (percentil {int(p)})", explanation=exp
    )


def _avalia_cobertura(r: float, c: Rules) -> Assessment:
    if r >= c["cobertura_ok"]:
        return (
            "ok",
            f"O caixa que sobra depois dos investimentos cobre {fmt.num(r, 1)}× os proventos pagos. Dividendo bem sustentado.",
        )
    if r >= c["cobertura_min"]:
        return "warn", f"O caixa livre cobre {fmt.num(r, 1)}× os proventos: no limite."
    return (
        "fail",
        f"O caixa livre cobre só {fmt.num(r, 1)}× os proventos. A diferença vem de dívida ou do caixa acumulado.",
    )


def rule_cobertura(s: StockSnapshot, c: Rules) -> RuleResult:
    base = {
        "id": "cobertura-caixa",
        "label": "Proventos cobertos pelo caixa",
        "learn_more": "fluxo-de-caixa-livre",
        "weight": 2,
        "group": "sustentabilidade",
        "threshold": f"fluxo de caixa livre ≥ {fmt.num(c['cobertura_ok'], 1)}× os proventos (média 3 anos)",
    }
    fs = [f for f in _recent_fundamentals(s, 3) if f.free_cash_flow is not None and f.dividends_paid]
    if len(fs) < 2:
        return _na(base, "Fluxo de caixa ainda não carregado.")
    fcf = sum(f.free_cash_flow or 0 for f in fs)
    div = sum(abs(f.dividends_paid or 0) for f in fs)
    r = fcf / div if div else math.inf
    status, exp = _avalia_cobertura(r, c)
    return _rule(**base, status=status, value=r, value_display=f"{fmt.num(r, 1)}x", explanation=exp)


def _debt_growth(start: float, end: float) -> float:
    """Crescimento da dívida líquida. Partindo de zero, qualquer dívida nova conta como crescimento infinito."""
    if start:
        return (end - start) / abs(start)
    if end > 0:
        return math.inf
    return 0


def rule_provento_divida(s: StockSnapshot) -> RuleResult:
    base = {
        "id": "provento-com-divida",
        "label": "Provento pago com dívida",
        "learn_more": "provento-com-divida",
        "weight": 2,
        "group": "sustentabilidade",
        "threshold": "dívida não cresce mais rápido que o EBITDA enquanto o payout passa de 80%",
    }
    fs = _recent_fundamentals(s, 4)
    if len(fs) < 4 or any(f.net_debt is None or f.ebitda is None for f in (fs[0], fs[-1])):
        return _na(base, "Balanços insuficientes.")
    first, last = fs[0], fs[-1]
    nd0, nd1 = first.net_debt or 0, last.net_debt or 0
    e0, e1 = first.ebitda or 0, last.ebitda or 0
    payout = avg_payout(s, 3)
    debt_growth = _debt_growth(nd0, nd1)
    ebitda_growth = (e1 - e0) / abs(e0) if e0 else 0
    if nd1 > nd0 and debt_growth > ebitda_growth and payout is not None and payout > 0.8:
        return _rule(
            **base,
            status="fail",
            value=debt_growth,
            value_display="sim",
            explanation=f"A dívida líquida cresceu {fmt.pct(debt_growth, 0)} em 3 anos (EBITDA {fmt.pct(ebitda_growth, 0)}) enquanto o payout foi de {fmt.pct(payout, 0)}. Parte do dividendo está sendo financiada com dívida.",
        )
    return _rule(
        **base,
        status="ok",
        value=debt_growth,
        value_display="não",
        explanation="Não há sinal de dividendos financiados por aumento de dívida.",
    )


def rule_basileia(s: StockSnapshot, c: Rules) -> RuleResult:
    base = {
        "id": "basileia",
        "label": "Índice de Basileia",
        "learn_more": "basileia",
        "weight": 2,
        "group": "setorial",
        "threshold": f"≥ {fmt.num(c['basileia_ok'], 0)}% (mínimo {fmt.num(c['basileia_min'], 0)}%)",
    }
    if "basileia" not in s.sector_metrics:
        return _na(base, INDICADOR_SETORIAL_AUSENTE)
    v = s.sector_metrics["basileia"]
    status = grade(v >= c["basileia_ok"], v >= c["basileia_min"])
    exp = {
        "ok": "Capital de sobra para absorver perdas com empréstimos.",
        "warn": "Capital suficiente, mas com folga pequena.",
        "fail": "Pouco capital para absorver perdas — o banco pode ter de reter dividendos.",
    }[status]
    return _rule(**base, status=status, value=v, value_display=f"{fmt.num(v, 1)}%", explanation=exp)


def rule_inadimplencia(s: StockSnapshot, c: Rules) -> RuleResult:
    base = {
        "id": "inadimplencia",
        "label": "Inadimplência (> 90 dias) × sistema",
        "learn_more": "inadimplencia",
        "weight": 2,
        "group": "setorial",
        "threshold": "abaixo da média do sistema financeiro",
    }
    m = s.sector_metrics
    if "inadimplencia" not in m or "inadimplencia_sistema" not in m:
        return _na(base, INDICADOR_SETORIAL_AUSENTE)
    v, sysv = m["inadimplencia"], m["inadimplencia_sistema"]
    diff = v - sysv
    status = grade(diff <= 0, diff <= c["inadimplencia_tolerancia"])
    exp = {
        "ok": "Os clientes do banco atrasam menos que a média do mercado.",
        "warn": "Inadimplência um pouco acima da média do sistema.",
        "fail": "Inadimplência bem acima da média: mais perdas com crédito pela frente.",
    }[status]
    return _rule(**base, status=status, value=diff, value_display=f"{fmt.num(v, 1)}% × {fmt.num(sysv, 1)}%", explanation=exp)


def rule_indice_combinado(s: StockSnapshot, c: Rules) -> RuleResult:
    base = {
        "id": "indice-combinado",
        "label": "Índice combinado",
        "learn_more": "indice-combinado",
        "weight": 2,
        "group": "setorial",
        "threshold": f"< {fmt.num(c['indice_combinado_ok'], 0)}% (máximo {fmt.num(c['indice_combinado_max'], 0)}%)",
    }
    if "indice_combinado" not in s.sector_metrics:
        return _na(base, INDICADOR_SETORIAL_AUSENTE)
    v = s.sector_metrics["indice_combinado"]
    status = grade(v < c["indice_combinado_ok"], v <= c["indice_combinado_max"])
    exp = {
        "ok": f"Gasta {fmt.num(v, 0)} de cada 100 reais de prêmio com sinistros e despesas: a operação de seguros dá lucro com folga.",
        "warn": f"Gasta {fmt.num(v, 0)} de cada 100 reais de prêmio: margem apertada.",
        "fail": f"Gasta {fmt.num(v, 0)} de cada 100 reais de prêmio: a operação de seguros quase não dá lucro.",
    }[status]
    return _rule(**base, status=status, value=v, value_display=f"{fmt.num(v, 1)}%", explanation=exp)


def _energy_segment_status(segment: str) -> RuleStatus:
    if segment == "transmissao":
        return "ok"
    if segment:
        return "warn"
    return "na"


ENERGY_SEGMENT_EXPLANATION: dict[RuleStatus, str] = {
    "ok": "Transmissão tem receita definida em contrato e corrigida pela inflação, independente de chuva ou consumo.",
    "warn": "Geração e distribuição dependem de chuvas, preços de energia ou consumo, então a receita varia mais.",
    "na": "Segmento ainda não cadastrado.",
}


def rule_segmento_energia(s: StockSnapshot, c: Rules) -> RuleResult:
    seg = s.segment or ""
    status = _energy_segment_status(seg)
    return _rule(
        id="segmento-energia",
        label="Segmento de energia",
        learn_more="segmentos-energia",
        weight=1,
        group="setorial",
        status=status,
        value=None,
        value_display=seg or "sem dado",
        threshold="transmissão (receita contratada)",
        explanation=ENERGY_SEGMENT_EXPLANATION[status],
    )


def rule_concessao(s: StockSnapshot, c: Rules) -> RuleResult:
    base = {
        "id": "concessao",
        "label": "Vencimento das concessões",
        "learn_more": "concessao",
        "weight": 2,
        "group": "setorial",
        "threshold": f"> {int(c['concessao_ok'])} anos (mínimo {int(c['concessao_min'])})",
    }
    if "concessao_anos" not in s.sector_metrics:
        return _na(base, INDICADOR_SETORIAL_AUSENTE)
    v = s.sector_metrics["concessao_anos"]
    status = grade(v > c["concessao_ok"], v >= c["concessao_min"])
    exp = {
        "ok": f"Principais concessões vencem em {fmt.num(v, 0)} anos: horizonte longo de receita.",
        "warn": f"Concessões vencem em {fmt.num(v, 0)} anos: acompanhe a renovação.",
        "fail": f"Concessões vencem em {fmt.num(v, 0)} anos: risco real de perder parte da receita.",
    }[status]
    return _rule(**base, status=status, value=v, value_display=f"{fmt.num(v, 0)} anos", explanation=exp)


SECTOR_RULES: dict[str, list[Callable[[StockSnapshot, Rules], RuleResult]]] = {
    "bancos": [rule_basileia, rule_inadimplencia],
    "seguros": [rule_indice_combinado],
    "energia": [rule_segmento_energia, rule_concessao],
    "saneamento": [rule_concessao],
}


def setoriais(s: StockSnapshot, c: Rules) -> list[RuleResult]:
    return [rule(s, c) for rule in SECTOR_RULES.get(s.sector, [])]


def graham_value(s: StockSnapshot, multiple: float = 22.5) -> float | None:
    """Valor de Graham, √(múltiplo × LPA × VPA), com o lucro e o patrimônio do último balanço.
    O múltiplo padrão, 22,5, é o P/L máximo de 15 vezes o P/VP máximo de 1,5."""
    fs = _recent_fundamentals(s, 1)
    if not fs or not s.shares_outstanding:
        return None
    f = fs[0]
    if not f.net_income or not f.equity or f.net_income <= 0 or f.equity <= 0:
        return None
    eps, bvps = f.net_income / s.shares_outstanding, f.equity / s.shares_outstanding
    return math.sqrt(multiple * eps * bvps)


def evaluate_stock(s: StockSnapshot, overrides: dict[str, float] | None = None) -> Evaluation:
    c = with_linked_yields(merged_rules(overrides), s)
    rules: list[RuleResult] = [
        rule_setor(s),
        rule_historico(s, c),
        rule_consistencia(s, c),
        rule_lucro(s),
        rule_roe(s, c),
    ]
    if s.sector not in FINANCEIRO:
        rules.append(rule_endividamento(s, c))
    rules.append(rule_payout(s, c))
    rules.append(rule_liquidez(s, c))
    teto_rule, teto, margin = rule_preco_teto(s, c)
    rules += [teto_rule, rule_dy_anormal(s, c), rule_barato_si(s, c)]
    if s.sector not in FINANCEIRO:
        rules += [rule_cobertura(s, c), rule_provento_divida(s)]
    rules += setoriais(s, c)

    teto_exigente = ceiling_price(s, c["yield_alvo_exigente"])
    extras = {
        "teto_exigente": teto_exigente,
        "bazin": (s.dividends_ttm / c["yield_alvo"]) if s.dividends_ttm else None,
        "graham": graham_value(s),
        "dy_medio_5a": avg_dy_5y(s),
        "roe_medio_5a": avg_roe(s),
        "payout_medio_5a": avg_payout(s),
        "anos_pagando": consecutive_paying_years(s),
        "yield_alvo": c["yield_alvo"],
        "yield_alvo_exigente": c["yield_alvo_exigente"],
    }
    has_core = s.price is not None and bool(s.dividends_by_year)
    return build_evaluation(
        ticker=s.ticker,
        rules=rules,
        cfg=c,
        price_rule_id="preco-teto",
        has_core_data=has_core,
        ceiling=teto,
        margin=margin,
        dy=current_dy(s),
        extras=extras,
        engine_version=ENGINE_VERSION,
    )

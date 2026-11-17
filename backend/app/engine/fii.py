"""Motor de avaliação de FIIs — filtro de entrada, estabilidade, rendimento e preço por P/VP.

As faixas mudam com o tipo do fundo: papel (recebíveis imobiliários, como CRI) é comparado
ao CDI e tem P/VP mais estreito; tijolo (imóveis) é comparado ao juro real da NTN-B, porque os
aluguéis acompanham a inflação. FoF e híbridos usam as faixas de tijolo. P/VP é tratado como
faixa de segurança, não como ranking: desconto grande costuma ser sinal de problema.

Mesmo formato do motor de ações: guardas para dado ausente ("sem dado") e uma função
`_avalia_*` que devolve (status, explicação) com retorno antecipado por faixa.
"""

from collections.abc import Callable
from typing import Any

from app.engine import fmt
from app.engine.acoes import Assessment, Rules, grade
from app.engine.config import merged_rules
from app.engine.score import build_evaluation
from app.engine.types import Evaluation, FiiKind, FiiSnapshot, RuleResult

ENGINE_VERSION = "fii-1.0"

KIND_LABEL = {
    "papel": "Papel (recebíveis imobiliários)",
    "tijolo": "Tijolo (imóveis)",
    "fof": "Fundo de fundos",
    "hibrido": "Híbrido",
}

IR_RENDA_FIXA_LONGA = 0.15
"""Menor alíquota de IR da renda fixa. O CDI líquido dela é a comparação justa com o rendimento isento do FII."""

KIND_MAJORITY = 0.5
"""Peso mínimo de crédito, imóveis ou cotas de FII (sem contar o caixa) para o fundo ser papel, tijolo ou FoF."""

DAYS_PER_YEAR = 365.25
INFORME_AUSENTE = "Informe da CVM ainda não carregado para este fundo."


def classify(paper: float, brick: float, fof: float) -> FiiKind:
    """Tipo do fundo pela composição do ativo. O segmento declarado à CVM não serve para isso:
    muitos fundos de papel aparecem como "Multicategoria" ou até "Logística"."""
    invested = paper + brick + fof
    if invested <= 0:
        return "hibrido"
    shares: dict[FiiKind, float] = {"papel": paper / invested, "tijolo": brick / invested, "fof": fof / invested}
    kind, share = max(shares.items(), key=lambda item: item[1])
    if share > KIND_MAJORITY:
        return kind
    return "hibrido"


def _na(base: dict[str, Any], explanation: str) -> RuleResult:
    return RuleResult(**base, status="na", value=None, value_display="sem dado", explanation=explanation)


def _pvp_range(kind: str, c: Rules) -> tuple[float, float, float]:
    """(atenção, mínimo ideal, máximo ideal) do P/VP para o tipo do fundo."""
    prefix = "fii_pvp_papel" if kind == "papel" else "fii_pvp_tijolo"
    return c[f"{prefix}_atencao"], c[f"{prefix}_min"], c[f"{prefix}_max"]


def price_to_book(s: FiiSnapshot) -> float | None:
    if not s.price or not s.nav_per_share or s.nav_per_share <= 0:
        return None
    return s.price / s.nav_per_share


def dividend_yield(s: FiiSnapshot) -> float | None:
    if not s.price or s.dividends_ttm is None:
        return None
    return s.dividends_ttm / s.price


def yearly_admin_fee(s: FiiSnapshot) -> float | None:
    if s.admin_fee_month is None:
        return None
    return s.admin_fee_month * 12


def net_cdi(s: FiiSnapshot) -> float | None:
    if s.cdi is None:
        return None
    return s.cdi * (1 - IR_RENDA_FIXA_LONGA)


def rule_patrimonio(s: FiiSnapshot, c: Rules) -> RuleResult:
    base = {
        "id": "fii-patrimonio",
        "label": "Tamanho do fundo",
        "learn_more": "patrimonio-fii",
        "weight": 2,
        "eliminatory": True,
        "threshold": f"patrimônio ≥ {fmt.brl(c['fii_pl_min'])}",
    }
    if s.equity is None:
        return _na(base, INFORME_AUSENTE)
    status = grade(s.equity >= c["fii_pl_min"], False)
    exp = {
        "ok": "Fundo grande: costuma ter gestão mais estruturada, mais diversificação e menos risco de um único problema pesar muito.",
        "fail": "Fundo pequeno: um único imóvel vago ou um crédito em atraso pesa muito no rendimento — regra eliminatória.",
    }[status]
    return RuleResult(**base, status=status, value=s.equity, value_display=fmt.brl(s.equity), explanation=exp)


def rule_liquidez(s: FiiSnapshot, c: Rules) -> RuleResult:
    base = {
        "id": "fii-liquidez",
        "label": "Liquidez",
        "learn_more": "liquidez",
        "weight": 2,
        "eliminatory": True,
        "threshold": f"≥ {fmt.brl(c['fii_liquidez_min'])} negociados por dia",
    }
    v = s.avg_daily_volume_brl
    if v is None:
        return _na(base, "Histórico de negociação insuficiente (menos de 20 pregões).")
    status = grade(v >= c["fii_liquidez_min"], False)
    exp = {
        "ok": "Negocia bastante todo dia: dá para comprar e vender sem mexer no preço.",
        "fail": "Negocia pouco: pode ser difícil vender sem aceitar um preço pior — regra eliminatória.",
    }[status]
    return RuleResult(**base, status=status, value=v, value_display=f"{fmt.brl(v)}/dia", explanation=exp)


def rule_historico(s: FiiSnapshot, c: Rules) -> RuleResult:
    base = {
        "id": "fii-historico",
        "label": "Tempo de funcionamento",
        "learn_more": "historico-fii",
        "weight": 2,
        "eliminatory": True,
        "threshold": f"≥ {fmt.years(int(c['fii_anos_min']))}",
    }
    if s.started_on is None:
        return _na(base, INFORME_AUSENTE)
    age = (s.today - s.started_on).days / DAYS_PER_YEAR
    status = grade(age >= c["fii_anos_min"], False)
    exp = {
        "ok": "Já passou por ciclos de juros e de mercado imobiliário: dá para julgar a gestão pelo histórico.",
        "fail": "Fundo novo: ainda não há histórico suficiente para avaliar a gestão em momentos ruins — regra eliminatória.",
    }[status]
    return RuleResult(**base, status=status, value=age, value_display=fmt.years(int(age)), explanation=exp)


def rule_isencao(s: FiiSnapshot, c: Rules) -> RuleResult:
    base = {
        "id": "fii-isencao",
        "label": "Rendimento isento de IR",
        "learn_more": "isencao-fii",
        "weight": 1,
        "threshold": f"negociado em bolsa e ≥ {int(c['fii_cotistas_min'])} cotistas",
    }
    if s.holders is None or s.listed is None:
        return _na(base, INFORME_AUSENTE)
    status = grade(s.listed and s.holders >= c["fii_cotistas_min"], False)
    exp = {
        "ok": "Cumpre as condições da lei para o rendimento ser isento de IR para pessoa física (desde que você tenha menos de 10% das cotas).",
        "fail": "Não cumpre as condições de isenção: os rendimentos podem ser tributados.",
    }[status]
    display = f"{fmt.num(s.holders, 0)} cotistas"
    return RuleResult(**base, status=status, value=float(s.holders), value_display=display, explanation=exp)


def _avalia_estabilidade(ratio: float, c: Rules) -> Assessment:
    if ratio >= c["fii_estabilidade_ok"]:
        return "ok", "Os rendimentos dos últimos 12 meses se mantiveram em relação aos 12 meses anteriores."
    if ratio >= c["fii_estabilidade_min"]:
        return (
            "warn",
            f"Os rendimentos caíram {fmt.pct(1 - ratio, 0)} em relação aos 12 meses anteriores. Vale entender o motivo.",
        )
    return "fail", f"Os rendimentos caíram {fmt.pct(1 - ratio, 0)} em 12 meses: a renda não está previsível."


def rule_estabilidade(s: FiiSnapshot, c: Rules) -> RuleResult:
    base = {
        "id": "fii-estabilidade",
        "label": "Estabilidade dos rendimentos",
        "learn_more": "estabilidade-rendimentos",
        "weight": 3,
        "group": "sustentabilidade",
        "threshold": f"12 meses ÷ 12 anteriores ≥ {fmt.num(c['fii_estabilidade_ok'])} (mínimo {fmt.num(c['fii_estabilidade_min'])})",
    }
    if s.dividends_ttm is None or not s.dividends_prev_ttm or s.dividends_prev_ttm <= 0:
        return _na(base, "É preciso ao menos 2 anos de rendimentos para comparar.")
    ratio = s.dividends_ttm / s.dividends_prev_ttm
    status, exp = _avalia_estabilidade(ratio, c)
    return RuleResult(**base, status=status, value=ratio, value_display=fmt.num(ratio), explanation=exp)


def _avalia_spread_papel(spread: float, c: Rules) -> Assessment:
    if spread > c["fii_spread_papel_estresse"]:
        return (
            "warn",
            "Rende muito acima do CDI líquido. Em fundos de papel isso costuma indicar créditos mais arriscados: confira a carteira.",
        )
    if spread >= 0:
        return "ok", "Rende acima do CDI líquido de IR, sem exagero: compensa trocar a renda fixa por ele."
    if spread >= -c["fii_spread_papel_tolerancia"]:
        return "warn", "Rende um pouco abaixo do CDI líquido de IR: a renda fixa paga quase o mesmo com menos risco."
    return "fail", "Rende bem abaixo do CDI líquido de IR: hoje a renda fixa paga mais com menos risco."


def _avalia_spread_tijolo(spread: float, c: Rules) -> Assessment:
    if spread >= c["fii_spread_tijolo_ok"]:
        return "ok", "Rende acima do juro real do Tesouro IPCA+: o prêmio compensa o risco dos imóveis."
    if spread >= 0:
        return "warn", "Rende quase o mesmo que o juro real do Tesouro IPCA+: o prêmio pelo risco é pequeno."
    return "fail", "Rende menos que o juro real do Tesouro IPCA+: hoje o título público paga mais com menos risco."


def _rendimento_papel(s: FiiSnapshot, c: Rules, base: dict[str, Any], dy: float) -> RuleResult:
    benchmark = net_cdi(s)
    base = {**base, "threshold": f"DY 12m ≥ CDI líquido (até +{fmt.pct(c['fii_spread_papel_estresse'], 0)})"}
    if benchmark is None:
        return _na(base, "CDI ainda não carregado. Rode a atualização de dados.")
    spread = dy - benchmark
    status, exp = _avalia_spread_papel(spread, c)
    display = f"DY {fmt.pct(dy)} × CDI líq. {fmt.pct(benchmark)}"
    return RuleResult(**base, status=status, value=spread, value_display=display, explanation=exp)


def _rendimento_tijolo(s: FiiSnapshot, c: Rules, base: dict[str, Any], dy: float) -> RuleResult:
    base = {**base, "threshold": f"DY 12m ≥ juro real da NTN-B + {fmt.pct(c['fii_spread_tijolo_ok'], 0)}"}
    if s.ntnb_real is None:
        return _na(base, "Taxas do Tesouro IPCA+ ainda não carregadas. Rode a atualização de dados.")
    spread = dy - s.ntnb_real
    status, exp = _avalia_spread_tijolo(spread, c)
    display = f"DY {fmt.pct(dy)} × NTN-B {fmt.pct(s.ntnb_real)}"
    return RuleResult(**base, status=status, value=spread, value_display=display, explanation=exp)


def rule_rendimento(s: FiiSnapshot, c: Rules) -> RuleResult:
    base = {
        "id": "fii-rendimento",
        "label": "Rendimento × alternativa sem risco",
        "learn_more": "spread-fii",
        "weight": 2,
        "group": "preco",
    }
    dy = dividend_yield(s)
    if dy is None:
        return _na({**base, "threshold": "DY 12m comparado à renda fixa"}, "Sem preço ou sem rendimentos dos últimos 12 meses.")
    if s.kind == "papel":
        return _rendimento_papel(s, c, base, dy)
    return _rendimento_tijolo(s, c, base, dy)


def _avalia_desconto(pvp: float, minimum: float) -> Assessment:
    if pvp >= minimum:
        return "ok", "A cota não está com desconto exagerado em relação ao patrimônio."
    return (
        "warn",
        "A cota está com desconto relevante em relação ao patrimônio. Pode ser oportunidade, mas confira se há crédito em atraso ou imóvel vago.",
    )


def rule_desconto(s: FiiSnapshot, c: Rules) -> RuleResult:
    attention, minimum, _ = _pvp_range(s.kind, c)
    base = {
        "id": "fii-desconto",
        "label": "Desconto sobre o patrimônio",
        "learn_more": "p-vp",
        "weight": 2,
        "threshold": f"P/VP ≥ {fmt.num(minimum)} (atenção a partir de {fmt.num(attention)})",
    }
    pvp = price_to_book(s)
    if pvp is None:
        return _na(base, "Sem preço ou sem valor patrimonial da cota.")
    if pvp < attention:
        exp = "Desconto muito grande: no mercado de FIIs isso costuma indicar um problema (calote, vacância, gestão), não uma pechincha."
        return RuleResult(**base, status="fail", value=pvp, value_display=f"P/VP {fmt.num(pvp)}", explanation=exp)
    status, exp = _avalia_desconto(pvp, minimum)
    return RuleResult(**base, status=status, value=pvp, value_display=f"P/VP {fmt.num(pvp)}", explanation=exp)


def rule_pvp(s: FiiSnapshot, c: Rules) -> tuple[RuleResult, float | None, float | None]:
    """Regra de preço: P/VP acima do máximo da faixa. Também devolve o preço máximo (VP × máximo) e a margem."""
    _, _, maximum = _pvp_range(s.kind, c)
    base = {
        "id": "fii-preco",
        "label": "Preço pelo P/VP",
        "learn_more": "p-vp",
        "weight": 2,
        "group": "preco",
        "threshold": f"P/VP ≤ {fmt.num(maximum)}",
    }
    pvp = price_to_book(s)
    if pvp is None or s.price is None or s.nav_per_share is None:
        return _na(base, "Sem preço ou sem valor patrimonial da cota."), None, None
    ceiling = s.nav_per_share * maximum
    margin = (ceiling - s.price) / ceiling
    status = grade(pvp <= maximum, False)
    exp = {
        "ok": f"O preço está dentro da faixa: até {fmt.brl(ceiling)} por cota ({fmt.num(maximum)} × o valor patrimonial).",
        "fail": f"Caro: a cota custa mais que {fmt.num(maximum)} × o patrimônio. Pelo critério, o preço máximo seria {fmt.brl(ceiling)}.",
    }[status]
    return RuleResult(**base, status=status, value=pvp, value_display=f"P/VP {fmt.num(pvp)}", explanation=exp), ceiling, margin


def rule_taxa_adm(s: FiiSnapshot, c: Rules) -> RuleResult:
    base = {
        "id": "fii-taxa-adm",
        "label": "Taxa de administração",
        "learn_more": "taxa-administracao",
        "weight": 1,
        "threshold": f"≤ {fmt.pct(c['fii_taxa_adm_ok'])} ao ano (máximo {fmt.pct(c['fii_taxa_adm_max'])})",
    }
    yearly = yearly_admin_fee(s)
    if yearly is None:
        return _na(base, INFORME_AUSENTE)
    status = grade(yearly <= c["fii_taxa_adm_ok"], yearly <= c["fii_taxa_adm_max"])
    exp = {
        "ok": "Taxa dentro do comum para FIIs: sobra mais do resultado para os cotistas.",
        "warn": "Taxa um pouco acima do comum: ela sai todo mês do resultado que seria distribuído.",
        "fail": "Taxa alta: consome uma parte relevante do resultado que seria seu.",
    }[status]
    return RuleResult(**base, status=status, value=yearly, value_display=f"{fmt.pct(yearly, 2)} ao ano", explanation=exp)


def rule_credito(s: FiiSnapshot, c: Rules) -> RuleResult:
    base = {
        "id": "fii-concentracao-credito",
        "label": "Concentração em um crédito",
        "learn_more": "concentracao-fii",
        "weight": 2,
        "threshold": f"maior ativo ≤ {fmt.pct(c['fii_credito_ok'], 0)} do patrimônio (máximo {fmt.pct(c['fii_credito_max'], 0)})",
    }
    v = s.largest_credit_share
    if v is None:
        return _na(base, "Informe trimestral com a carteira de crédito ainda não carregado.")
    status = grade(v <= c["fii_credito_ok"], v <= c["fii_credito_max"])
    exp = {
        "ok": "Nenhum crédito sozinho pesa muito: se um devedor atrasar, o rendimento sente pouco.",
        "warn": "Um crédito tem peso relevante: um atraso dele já apareceria no rendimento.",
        "fail": "Carteira concentrada: um único devedor em atraso derrubaria o rendimento.",
    }[status]
    return RuleResult(**base, status=status, value=v, value_display=f"maior: {fmt.pct(v)}", explanation=exp)


def rule_concentracao_imovel(s: FiiSnapshot, c: Rules) -> RuleResult:
    base = {
        "id": "fii-concentracao-imovel",
        "label": "Concentração em um imóvel",
        "learn_more": "concentracao-fii",
        "weight": 2,
        "threshold": f"maior imóvel ≤ {fmt.pct(c['fii_imovel_ok'], 0)} da receita (máximo {fmt.pct(c['fii_imovel_max'], 0)})",
    }
    v = s.largest_property_share
    if v is None:
        return _na(base, "Informe trimestral com a receita por imóvel ainda não carregado.")
    status = grade(v <= c["fii_imovel_ok"], v <= c["fii_imovel_max"])
    exp = {
        "ok": "A receita está espalhada: perder um inquilino não derruba o rendimento.",
        "warn": "Um imóvel responde por boa parte da receita: acompanhe o contrato dele.",
        "fail": "Receita concentrada: se o principal imóvel ficar vago, o rendimento cai muito.",
    }[status]
    return RuleResult(**base, status=status, value=v, value_display=f"maior: {fmt.pct(v)}", explanation=exp)


def rule_imoveis(s: FiiSnapshot, c: Rules) -> RuleResult:
    base = {
        "id": "fii-imoveis",
        "label": "Quantidade de imóveis",
        "learn_more": "concentracao-fii",
        "weight": 1,
        "threshold": f"≥ {int(c['fii_imoveis_ok'])} imóveis (mínimo {int(c['fii_imoveis_min'])})",
    }
    if s.properties is None:
        return _na(base, "Informe trimestral com os imóveis ainda não carregado.")
    n = s.properties
    status = grade(n >= c["fii_imoveis_ok"], n >= c["fii_imoveis_min"])
    exp = {
        "ok": "Carteira diversificada em vários imóveis.",
        "warn": "Poucos imóveis. Contratos atípicos longos (aluguel garantido por anos) podem compensar: confira.",
        "fail": "Muito poucos imóveis: o fundo depende demais de cada um deles.",
    }[status]
    return RuleResult(**base, status=status, value=float(n), value_display=f"{n} imóveis", explanation=exp)


def rule_vacancia(s: FiiSnapshot, c: Rules) -> RuleResult:
    base = {
        "id": "fii-vacancia",
        "label": "Vacância",
        "learn_more": "vacancia",
        "weight": 2,
        "threshold": f"≤ {fmt.pct(c['fii_vacancia_ok'], 0)} (máximo {fmt.pct(c['fii_vacancia_max'], 0)})",
    }
    v = s.vacancy
    if v is None:
        return _na(base, "Vacância não informada ou inconsistente no informe trimestral da CVM.")
    status = grade(v <= c["fii_vacancia_ok"], v <= c["fii_vacancia_max"])
    exp = {
        "ok": "Quase todos os imóveis estão alugados.",
        "warn": "Parte relevante da área está vaga: o rendimento pode subir se alugar, mas hoje pesa.",
        "fail": "Muita área vaga: além de não render, o fundo paga condomínio e IPTU desses espaços.",
    }[status]
    return RuleResult(**base, status=status, value=v, value_display=fmt.pct(v), explanation=exp)


KIND_RULES: dict[str, list[Callable[[FiiSnapshot, Rules], RuleResult]]] = {
    "papel": [rule_credito],
    "tijolo": [rule_concentracao_imovel, rule_imoveis, rule_vacancia],
    "hibrido": [rule_credito, rule_concentracao_imovel, rule_imoveis, rule_vacancia],
    "fof": [],
}


def evaluate_fii(s: FiiSnapshot, overrides: dict[str, float] | None = None) -> Evaluation:
    c = merged_rules(overrides)
    price_rule, ceiling, margin = rule_pvp(s, c)
    rules = [
        rule_patrimonio(s, c),
        rule_liquidez(s, c),
        rule_historico(s, c),
        rule_isencao(s, c),
        rule_estabilidade(s, c),
        rule_rendimento(s, c),
        rule_desconto(s, c),
        price_rule,
        rule_taxa_adm(s, c),
        *[rule(s, c) for rule in KIND_RULES[s.kind]],
    ]
    _, _, pvp_max = _pvp_range(s.kind, c)
    extras = {
        "tipo": s.kind,
        "tipo_label": KIND_LABEL[s.kind],
        "segmento": s.segment,
        "pvp": price_to_book(s),
        "pvp_max": pvp_max,
        "valor_patrimonial_cota": s.nav_per_share,
        "patrimonio": s.equity,
        "cotistas": s.holders,
        "imoveis": s.properties,
        "vacancia": s.vacancy,
        "taxa_adm_ano": yearly_admin_fee(s),
        "rendimentos_12m": s.dividends_ttm,
        "cdi_liquido": net_cdi(s),
        "ntnb_real": s.ntnb_real,
    }
    has_core = s.price is not None and s.nav_per_share is not None and s.dividends_ttm is not None
    return build_evaluation(
        ticker=s.ticker,
        rules=rules,
        cfg=c,
        price_rule_id="fii-preco",
        has_core_data=has_core,
        ceiling=ceiling,
        margin=margin,
        dy=dividend_yield(s),
        extras=extras,
        engine_version=ENGINE_VERSION,
    )

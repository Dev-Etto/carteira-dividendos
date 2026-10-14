"""Limites padrão das regras. Todos podem ser sobrescritos pela tabela rule_config
(tela de Configurações). As chaves aqui são as mesmas da tabela.

Grupos de limites:
- preço-teto: yield-alvo (normal e exigente) e margem de segurança desejada;
- histórico de proventos: anos seguidos pagando (ideal e mínimo);
- consistência: queda anual dos proventos considerada forte;
- ROE médio de 5 anos (ideal e mínimo);
- dívida líquida ÷ EBITDA, geral e para setores regulados (energia e saneamento);
- payout médio de 5 anos (faixa saudável e máximo);
- liquidez média diária em R$;
- dividend yield atual ÷ média de 5 anos (alerta e máximo);
- percentil do múltiplo no histórico de 5 anos (barato e caro);
- sustentabilidade: fluxo de caixa livre ÷ proventos, média de 3 anos;
- bancos (Basileia e inadimplência), seguradoras (índice combinado) e concessões (anos até o vencimento);
- veredito: nota mínima para comprar e nota abaixo da qual evitar.
"""

PRECO_TETO = {"yield_alvo": 0.06, "yield_alvo_exigente": 0.08, "margem_ok": 0.10}
HISTORICO_PROVENTOS = {"proventos_anos_ok": 10, "proventos_anos_min": 5}
CONSISTENCIA = {"queda_forte": 0.30}
ROE = {"roe_ok": 0.15, "roe_min": 0.10}
DIVIDA = {"divida_ok": 2.0, "divida_max": 3.0}
DIVIDA_SETOR_REGULADO = {"divida_alavancado_ok": 3.0, "divida_alavancado_max": 4.0}
PAYOUT = {"payout_min": 0.40, "payout_ok_max": 0.80, "payout_max": 1.00}
LIQUIDEZ_BRL = {"liquidez_ok": 5_000_000, "liquidez_min": 1_000_000}
DY_ANORMAL = {"dy_anormal_alerta": 1.5, "dy_anormal_max": 2.0}
PERCENTIL_MULTIPLO = {"percentil_barato": 30, "percentil_caro": 70}
COBERTURA_CAIXA = {"cobertura_ok": 1.2, "cobertura_min": 0.9}
BANCOS = {"basileia_ok": 13.0, "basileia_min": 11.0, "inadimplencia_tolerancia": 1.0}
SEGURADORAS = {"indice_combinado_ok": 85.0, "indice_combinado_max": 95.0}
CONCESSOES = {"concessao_ok": 10, "concessao_min": 5}
VEREDITO = {"nota_comprar": 70, "nota_evitar": 50}

DEFAULT_RULES: dict[str, float] = {
    **PRECO_TETO,
    **HISTORICO_PROVENTOS,
    **CONSISTENCIA,
    **ROE,
    **DIVIDA,
    **DIVIDA_SETOR_REGULADO,
    **PAYOUT,
    **LIQUIDEZ_BRL,
    **DY_ANORMAL,
    **PERCENTIL_MULTIPLO,
    **COBERTURA_CAIXA,
    **BANCOS,
    **SEGURADORAS,
    **CONCESSOES,
    **VEREDITO,
}


def merged_rules(overrides: dict[str, float] | None) -> dict[str, float]:
    cfg = dict(DEFAULT_RULES)
    if overrides:
        cfg.update({k: v for k, v in overrides.items() if k in DEFAULT_RULES})
    return cfg


ORDERED_LIMITS: tuple[tuple[str, str], ...] = (
    ("yield_alvo", "yield_alvo_exigente"),
    ("proventos_anos_min", "proventos_anos_ok"),
    ("roe_min", "roe_ok"),
    ("divida_ok", "divida_max"),
    ("divida_alavancado_ok", "divida_alavancado_max"),
    ("payout_min", "payout_ok_max"),
    ("payout_ok_max", "payout_max"),
    ("liquidez_min", "liquidez_ok"),
    ("dy_anormal_alerta", "dy_anormal_max"),
    ("percentil_barato", "percentil_caro"),
    ("cobertura_min", "cobertura_ok"),
    ("basileia_min", "basileia_ok"),
    ("indice_combinado_ok", "indice_combinado_max"),
    ("concessao_min", "concessao_ok"),
    ("nota_evitar", "nota_comprar"),
)
STRICTLY_POSITIVE = frozenset({"yield_alvo", "yield_alvo_exigente"})


def rule_errors(cfg: dict[str, float]) -> list[str]:
    """Inconsistências de um conjunto completo de limites: valores negativos, yield-alvo zero
    (o preço-teto divide por ele) e pares fora de ordem (o mínimo não pode passar do ideal)."""
    negative = [f"{key} não pode ser negativo" for key, value in cfg.items() if value < 0]
    zero = [f"{key} precisa ser maior que zero" for key in sorted(STRICTLY_POSITIVE) if cfg[key] == 0]
    unordered = [
        f"{low} ({cfg[low]:g}) não pode ser maior que {high} ({cfg[high]:g})"
        for low, high in ORDERED_LIMITS
        if cfg[low] > cfg[high]
    ]
    return negative + zero + unordered

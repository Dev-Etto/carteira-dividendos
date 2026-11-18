"""Limites padrão das regras. Todos podem ser sobrescritos pela tabela rule_config
(tela de Configurações). As chaves aqui são as mesmas da tabela.

Grupos de limites:
- preço-teto: yield-alvo (normal e exigente), margem de segurança desejada e se o yield-alvo acompanha
  o juro real do Tesouro IPCA+ (1 liga, 0 usa só o fixo);
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

Grupos de limites dos FIIs (prefixo fii_):
- porte e negociação: patrimônio líquido mínimo, liquidez média diária mínima e anos de funcionamento;
- isenção de IR dos rendimentos: número mínimo de cotistas;
- P/VP por tipo (papel e tijolo): faixa ideal e desconto a partir do qual o fundo merece atenção;
- estabilidade: proventos dos últimos 12 meses ÷ 12 meses anteriores (ideal e mínimo);
- rendimento: papel compara o DY com o CDI líquido de IR (tolerância abaixo e spread que indica
  estresse de crédito); tijolo compara com o juro real da NTN-B (spread ideal);
- concentração: maior ativo de crédito ÷ patrimônio (papel) e maior imóvel ÷ receita (tijolo);
- tijolo: número de imóveis e vacância física;
- taxa de administração ao ano.

Limites do método Bazin (prefixo bazin_): yield-alvo e yield de venda sobre os proventos dos últimos
12 meses, anos seguidos pagando, dívida líquida ÷ patrimônio máxima e se o yield-alvo acompanha o juro
real (1 liga, 0 usa só o fixo).

Limites do método Graham (prefixo graham_), critérios do investidor defensivo adaptados ao Brasil:
receita mínima, liquidez corrente, anos seguidos com lucro e com proventos, crescimento do lucro ao ano,
P/L máximo (fixo ou ligado ao juro real: 1 liga, 0 usa o fixo) e P/L × P/VP máximo.

Limites da Fórmula Mágica (prefixo fm_): fração do ranking que recebe "comprar" (o primeiro terço).

Limites dos ETFs (prefixo etf_): liquidez média diária (ideal e mínima, eliminatória), patrimônio
(ideal e mínimo), taxa de administração ao ano (ideal e máxima) e, nas divisões sem classe de ETFs
(ARCA), a parte da verba de ações que vai para os ETFs nacionais favoritos. ETFs não têm nota Barsi: o
checklist só informa, e o aporte escolhe entre os favoritos do usuário.
"""

PRECO_TETO = {"yield_alvo": 0.06, "yield_alvo_exigente": 0.08, "margem_ok": 0.10, "yield_ligado_juros": 0}
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

FII_PORTE = {"fii_pl_min": 500_000_000, "fii_liquidez_min": 1_000_000, "fii_anos_min": 4}
FII_ISENCAO = {"fii_cotistas_min": 100}
FII_PVP = {
    "fii_pvp_papel_atencao": 0.75,
    "fii_pvp_papel_min": 0.85,
    "fii_pvp_papel_max": 1.08,
    "fii_pvp_tijolo_atencao": 0.70,
    "fii_pvp_tijolo_min": 0.85,
    "fii_pvp_tijolo_max": 1.15,
}
FII_ESTABILIDADE = {"fii_estabilidade_ok": 0.90, "fii_estabilidade_min": 0.75}
FII_RENDIMENTO = {
    "fii_spread_papel_tolerancia": 0.02,
    "fii_spread_papel_estresse": 0.06,
    "fii_spread_tijolo_ok": 0.01,
}
FII_CONCENTRACAO = {
    "fii_credito_ok": 0.06,
    "fii_credito_max": 0.10,
    "fii_imovel_ok": 0.25,
    "fii_imovel_max": 0.40,
}
FII_TIJOLO = {"fii_imoveis_ok": 8, "fii_imoveis_min": 4, "fii_vacancia_ok": 0.10, "fii_vacancia_max": 0.20}
FII_TAXA = {"fii_taxa_adm_ok": 0.010, "fii_taxa_adm_max": 0.015}

BAZIN = {
    "bazin_yield_alvo": 0.06,
    "bazin_yield_venda": 0.04,
    "bazin_anos_pagando": 3,
    "bazin_divida_pl_max": 1.0,
    "bazin_yield_ligado_juros": 0,
}

GRAHAM = {
    "graham_receita_min": 300_000_000,
    "graham_liquidez_corrente_min": 1.22,
    "graham_anos_lucro": 5,
    "graham_anos_proventos": 5,
    "graham_crescimento_min": 0.0266,
    "graham_pl_max": 15.0,
    "graham_pl_ligado_juros": 1,
    "graham_pl_x_pvp_max": 22.5,
}

FORMULA_MAGICA = {"fm_fracao_comprar": 1 / 3}

ETF_LIMITES = {
    "etf_liquidez_ok": 5_000_000,
    "etf_liquidez_min": 1_000_000,
    "etf_pl_ok": 500_000_000,
    "etf_pl_min": 100_000_000,
    "etf_taxa_adm_ok": 0.005,
    "etf_taxa_adm_max": 0.010,
    "etf_fatia_nacional_acoes": 0.20,
}

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
    **FII_PORTE,
    **FII_ISENCAO,
    **FII_PVP,
    **FII_ESTABILIDADE,
    **FII_RENDIMENTO,
    **FII_CONCENTRACAO,
    **FII_TIJOLO,
    **FII_TAXA,
    **ETF_LIMITES,
    **BAZIN,
    **GRAHAM,
    **FORMULA_MAGICA,
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
    ("fii_pvp_papel_atencao", "fii_pvp_papel_min"),
    ("fii_pvp_papel_min", "fii_pvp_papel_max"),
    ("fii_pvp_tijolo_atencao", "fii_pvp_tijolo_min"),
    ("fii_pvp_tijolo_min", "fii_pvp_tijolo_max"),
    ("fii_estabilidade_min", "fii_estabilidade_ok"),
    ("fii_credito_ok", "fii_credito_max"),
    ("fii_imovel_ok", "fii_imovel_max"),
    ("fii_imoveis_min", "fii_imoveis_ok"),
    ("fii_vacancia_ok", "fii_vacancia_max"),
    ("fii_taxa_adm_ok", "fii_taxa_adm_max"),
    ("etf_liquidez_min", "etf_liquidez_ok"),
    ("etf_pl_min", "etf_pl_ok"),
    ("etf_taxa_adm_ok", "etf_taxa_adm_max"),
    ("bazin_yield_venda", "bazin_yield_alvo"),
)
STRICTLY_POSITIVE = frozenset(
    {
        "yield_alvo",
        "yield_alvo_exigente",
        "fii_pvp_papel_max",
        "fii_pvp_tijolo_max",
        "bazin_yield_alvo",
        "graham_pl_max",
        "graham_pl_x_pvp_max",
        "fm_fracao_comprar",
    }
)


AT_MOST_ONE = frozenset({"etf_fatia_nacional_acoes", "fm_fracao_comprar"})
"""Limites que são uma parte de um todo e não podem passar de 100%."""


def rule_errors(cfg: dict[str, float]) -> list[str]:
    """Inconsistências de um conjunto completo de limites: valores negativos, yield-alvo zero
    (o preço-teto divide por ele), partes acima de 100% e pares fora de ordem (o mínimo não pode passar do ideal)."""
    negative = [f"{key} não pode ser negativo" for key, value in cfg.items() if value < 0]
    zero = [f"{key} precisa ser maior que zero" for key in sorted(STRICTLY_POSITIVE) if cfg[key] == 0]
    above_whole = [f"{key} não pode passar de 100%" for key in sorted(AT_MOST_ONE) if cfg[key] > 1]
    unordered = [
        f"{low} ({cfg[low]:g}) não pode ser maior que {high} ({cfg[high]:g})"
        for low, high in ORDERED_LIMITS
        if cfg[low] > cfg[high]
    ]
    return negative + zero + above_whole + unordered

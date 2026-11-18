import { checkDecimal, checkInteger, checkMoney, checkPercent, type Checked } from "./validation";

/** Rótulo de cada limite editável. Chave fora daqui não aparece na tela. */
export const RULE_LABEL: Record<string, string> = {
  yield_alvo: "Yield-alvo do preço-teto (%)",
  yield_alvo_exigente: "Yield-alvo exigente (%)",
  margem_ok: "Margem de segurança desejada (%)",
  yield_ligado_juros: "Yield-alvo acompanha o juro real do Tesouro IPCA+ (1 = sim, 0 = não)",
  proventos_anos_ok: "Anos seguidos pagando (ideal)",
  proventos_anos_min: "Anos seguidos pagando (mínimo)",
  roe_ok: "ROE ideal (%)",
  roe_min: "ROE mínimo (%)",
  divida_ok: "Dívida/EBITDA ideal",
  divida_max: "Dívida/EBITDA máximo",
  liquidez_ok: "Liquidez diária ideal (R$)",
  liquidez_min: "Liquidez diária mínima (R$)",
  nota_comprar: "Nota mínima para comprar",
  nota_evitar: "Nota abaixo da qual evitar",
  fii_pl_min: "Patrimônio mínimo (R$)",
  fii_liquidez_min: "Liquidez diária mínima (R$)",
  fii_anos_min: "Anos de funcionamento (mínimo)",
  fii_pvp_papel_min: "Papel: P/VP mínimo ideal",
  fii_pvp_papel_max: "Papel: P/VP máximo",
  fii_pvp_papel_atencao: "Papel: P/VP de atenção",
  fii_pvp_tijolo_min: "Tijolo: P/VP mínimo ideal",
  fii_pvp_tijolo_max: "Tijolo: P/VP máximo",
  fii_pvp_tijolo_atencao: "Tijolo: P/VP de atenção",
  fii_estabilidade_ok: "Rendimentos 12m ÷ anteriores, ideal (%)",
  fii_estabilidade_min: "Rendimentos 12m ÷ anteriores, mínimo (%)",
  fii_spread_papel_tolerancia: "Papel: tolerância abaixo do CDI líquido (p.p.)",
  fii_spread_papel_estresse: "Papel: spread que indica estresse (p.p.)",
  fii_spread_tijolo_ok: "Tijolo: spread ideal sobre a NTN-B (p.p.)",
  fii_credito_ok: "Papel: maior crédito, ideal (% do PL)",
  fii_credito_max: "Papel: maior crédito, máximo (% do PL)",
  fii_imovel_ok: "Tijolo: maior imóvel, ideal (% da receita)",
  fii_imovel_max: "Tijolo: maior imóvel, máximo (% da receita)",
  fii_imoveis_ok: "Tijolo: número de imóveis (ideal)",
  fii_imoveis_min: "Tijolo: número de imóveis (mínimo)",
  fii_vacancia_ok: "Tijolo: vacância ideal (%)",
  fii_vacancia_max: "Tijolo: vacância máxima (%)",
  fii_taxa_adm_ok: "Taxa de administração ideal (% a.a.)",
  fii_taxa_adm_max: "Taxa de administração máxima (% a.a.)",
  etf_liquidez_ok: "Liquidez diária ideal (R$)",
  etf_liquidez_min: "Liquidez diária mínima (R$)",
  etf_pl_ok: "Patrimônio ideal (R$)",
  etf_pl_min: "Patrimônio mínimo (R$)",
  etf_taxa_adm_ok: "Taxa de administração ideal (% a.a.)",
  etf_taxa_adm_max: "Taxa de administração máxima (% a.a.)",
  bazin_yield_alvo: "Yield mínimo dos últimos 12 meses (%)",
  bazin_yield_venda: "Yield em que o Bazin venderia (%)",
  bazin_anos_pagando: "Anos seguidos pagando (mínimo)",
  bazin_divida_pl_max: "Dívida líquida ÷ patrimônio máxima",
  bazin_yield_ligado_juros: "Yield mínimo acompanha o juro real do Tesouro IPCA+ (1 = sim, 0 = não)",
  graham_receita_min: "Receita anual mínima (R$)",
  graham_liquidez_corrente_min: "Liquidez corrente mínima",
  graham_anos_lucro: "Anos seguidos com lucro (mínimo)",
  graham_anos_proventos: "Anos seguidos pagando (mínimo)",
  graham_crescimento_min: "Crescimento mínimo do lucro (% a.a.)",
  graham_pl_max: "P/L máximo fixo",
  graham_pl_ligado_juros: "P/L máximo ligado ao juro real (1 = sim, 0 = usa o fixo)",
  graham_pl_x_pvp_max: "P/L × P/VP máximo",
  fm_fracao_comprar: "Parte do ranking que recebe comprar (%)",
};

/** Limites guardados como fração (0,06) que a tela mostra e recebe em porcentagem (6). */
const PERCENT_RULES = new Set([
  "yield_alvo",
  "yield_alvo_exigente",
  "margem_ok",
  "roe_ok",
  "roe_min",
  "fii_estabilidade_ok",
  "fii_estabilidade_min",
  "fii_spread_papel_tolerancia",
  "fii_spread_papel_estresse",
  "fii_spread_tijolo_ok",
  "fii_credito_ok",
  "fii_credito_max",
  "fii_imovel_ok",
  "fii_imovel_max",
  "fii_vacancia_ok",
  "fii_vacancia_max",
  "fii_taxa_adm_ok",
  "fii_taxa_adm_max",
  "etf_taxa_adm_ok",
  "etf_taxa_adm_max",
  "bazin_yield_alvo",
  "bazin_yield_venda",
  "graham_crescimento_min",
  "fm_fracao_comprar",
]);

/** Percentuais que são diferença entre taxas, mostrados em pontos percentuais. */
const POINTS_RULES = new Set(["fii_spread_papel_tolerancia", "fii_spread_papel_estresse", "fii_spread_tijolo_ok"]);

/** Limites em reais (liquidez e patrimônio). */
const MONEY_RULES = new Set([
  "liquidez_ok",
  "liquidez_min",
  "fii_pl_min",
  "fii_liquidez_min",
  "etf_liquidez_ok",
  "etf_liquidez_min",
  "etf_pl_ok",
  "etf_pl_min",
  "graham_receita_min",
]);

/** Limites que só fazem sentido inteiros (anos, número de imóveis, chaves 0/1). */
const INTEGER_RULES = new Set([
  "proventos_anos_ok",
  "proventos_anos_min",
  "fii_anos_min",
  "fii_imoveis_ok",
  "fii_imoveis_min",
  "bazin_anos_pagando",
  "bazin_yield_ligado_juros",
  "yield_ligado_juros",
  "graham_anos_lucro",
  "graham_anos_proventos",
  "graham_pl_ligado_juros",
]);

const MAX_SCORE = 100;

/** Tipo do valor de um limite, que decide o campo e a validação. */
export type RuleKind = "percent" | "money" | "integer" | "score" | "decimal";

const CHECK: Record<RuleKind, (text: string) => Checked<number>> = {
  percent: (text) => checkPercent(text),
  money: (text) => checkMoney(text),
  integer: (text) => checkInteger(text),
  score: (text) => checkInteger(text, { max: MAX_SCORE }),
  decimal: (text) => checkDecimal(text),
};

export function ruleKind(key: string): RuleKind {
  if (PERCENT_RULES.has(key)) return "percent";
  if (MONEY_RULES.has(key)) return "money";
  if (key.startsWith("nota_")) return "score";
  if (INTEGER_RULES.has(key)) return "integer";
  return "decimal";
}

/** Valida o texto digitado de um limite; vazio também é erro, porque todo limite precisa de valor. */
export function checkRule(key: string, text: string): Checked<number> {
  const checked = CHECK[ruleKind(key)](text);
  if (checked.value === null && !checked.error) return { value: null, error: "Informe um valor." };
  return checked;
}

/**
 * Valor da regra como vai no campo: em % para as frações e com vírgula decimal. Só os valores em reais
 * levam separador de milhar ("5.000.000"), como a máscara de moeda.
 */
export function ruleText(key: string, value: number): string {
  const shown = PERCENT_RULES.has(key) ? value * 100 : value;
  return shown.toLocaleString("pt-BR", { maximumFractionDigits: 6, useGrouping: MONEY_RULES.has(key) });
}

const UNIT: Partial<Record<RuleKind, (text: string) => string>> = {
  percent: (text) => `${text}%`,
  money: (text) => `R$ ${text}`,
};

/** Valor da regra para ler, com a unidade ("6%", "R$ 5.000.000", "2,5"). */
export function ruleDisplay(key: string, value: number): string {
  const text = ruleText(key, value);
  if (POINTS_RULES.has(key)) return `${text} p.p.`;
  const unit = UNIT[ruleKind(key)];
  return unit ? unit(text) : text;
}

/** Converte o texto digitado de volta para o valor guardado pela API; null se não for número. */
export function ruleValue(key: string, text: string): number | null {
  const n = checkRule(key, text).value;
  if (n === null) return null;
  return PERCENT_RULES.has(key) ? n / 100 : n;
}

/** Grupo de limites: uma metodologia de seleção de ações, os FIIs ou os ETFs. */
export type RuleGroup = { key: string; title: string; description: string; prefix: string | null };

/** Grupos na ordem padrão. Barsi não tem prefixo: junta as chaves que não são de nenhum outro grupo. */
const BARSI_GROUP: RuleGroup = {
  key: "barsi",
  title: "Barsi",
  description: "Ações pelo método Barsi: preço-teto pelo yield, histórico de proventos, endividamento e liquidez.",
  prefix: null,
};

export const RULE_GROUPS: RuleGroup[] = [
  BARSI_GROUP,
  {
    key: "bazin",
    title: "Bazin",
    description: "Ações pelo Bazin: yield mínimo, constância dos proventos e dívida.",
    prefix: "bazin_",
  },
  {
    key: "graham",
    title: "Graham",
    description: "Ações pelo Graham: porte, solidez, histórico de lucros e preço máximo.",
    prefix: "graham_",
  },
  {
    key: "fm",
    title: "Fórmula Mágica",
    description: "Ações pela Fórmula Mágica: quanto do ranking recebe comprar.",
    prefix: "fm_",
  },
  {
    key: "fii",
    title: "FIIs",
    description: "Filtro de segurança dos fundos imobiliários, de papel e de tijolo.",
    prefix: "fii_",
  },
  { key: "etf", title: "ETFs", description: "Liquidez, patrimônio e taxa dos ETFs.", prefix: "etf_" },
];

/** Grupo de limites de cada metodologia de seleção de ações. */
const SELECTION_GROUP: Record<string, string> = { barsi: "barsi", bazin: "bazin", graham: "graham", "formula-magica": "fm" };

const DEFAULT_GROUP = "barsi";

/** Grupo da metodologia de seleção escolhida; metodologia desconhecida cai no Barsi. */
export function selectionGroup(selectionMethod: string): string {
  return SELECTION_GROUP[selectionMethod] ?? DEFAULT_GROUP;
}

/** Grupo pela chave; chave desconhecida cai no Barsi. */
export function findGroup(key: string): RuleGroup {
  return RULE_GROUPS.find((g) => g.key === key) ?? BARSI_GROUP;
}

/** Grupo de uma chave de limite. */
export function ruleGroupOf(key: string): string {
  return RULE_GROUPS.find((g) => g.prefix !== null && key.startsWith(g.prefix))?.key ?? DEFAULT_GROUP;
}

/** Grupos com o da metodologia escolhida primeiro; os demais seguem a ordem padrão. */
export function orderedGroups(selectionMethod: string): RuleGroup[] {
  const first = selectionGroup(selectionMethod);
  return [...RULE_GROUPS.filter((g) => g.key === first), ...RULE_GROUPS.filter((g) => g.key !== first)];
}

/** Grupo pedido na URL, se existir; senão o da metodologia escolhida. */
export function groupFromParam(param: string | null, selectionMethod: string): string {
  if (RULE_GROUPS.some((g) => g.key === param)) return param as string;
  return selectionGroup(selectionMethod);
}

export type LabeledRule = { key: string; label: string };
export type RuleSubsection = { title: string | null; rules: LabeledRule[] };

const SUBSECTION_PREFIXES = ["Papel", "Tijolo"];

function capitalize(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1);
}

/**
 * Separa os limites pelos prefixos "Papel:" e "Tijolo:" do rótulo (FIIs), tirando o prefixo do rótulo.
 * Os sem prefixo vêm primeiro, numa subseção sem título; subseções vazias ficam de fora.
 */
export function splitSubsections(rules: LabeledRule[]): RuleSubsection[] {
  const prefixOf = (label: string) => SUBSECTION_PREFIXES.find((p) => label.startsWith(`${p}: `)) ?? null;
  const titles = [null, ...SUBSECTION_PREFIXES];
  return titles
    .map((title) => ({
      title,
      rules: rules
        .filter((r) => prefixOf(r.label) === title)
        .map((r) => ({ key: r.key, label: title ? capitalize(r.label.slice(title.length + 2)) : r.label })),
    }))
    .filter((s) => s.rules.length > 0);
}

const SAME_VALUE_TOLERANCE = 1e-9;

/** Se o texto digitado representa o mesmo valor guardado (tolerando o arredondamento de % para fração). */
export function sameRuleValue(key: string, text: string, stored: number | undefined): boolean {
  const value = ruleValue(key, text);
  if (value === null || stored === undefined) return false;
  return Math.abs(value - stored) < SAME_VALUE_TOLERANCE;
}

/** Chaves editadas cujo texto difere do valor salvo (ou não é um número válido). */
export function pendingKeys(edits: Record<string, string>, saved: Record<string, number>): string[] {
  return Object.entries(edits)
    .filter(([key, text]) => !sameRuleValue(key, text, saved[key]))
    .map(([key]) => key);
}

/** Corpo do PUT /api/regras com as chaves pedidas, ou null se alguma não for um número válido. */
export function rulesBody(edits: Record<string, string>, keys: string[]): Record<string, number> | null {
  const body: Record<string, number> = {};
  for (const key of keys) {
    const value = ruleValue(key, edits[key] ?? "");
    if (value === null) return null;
    body[key] = value;
  }
  return body;
}

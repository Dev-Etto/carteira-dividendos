const brlFmt = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });

export function brl(v: number | string | null | undefined): string {
  if (v === null || v === undefined || v === "") return "—";
  return brlFmt.format(Number(v));
}

export function brlCompact(v: number | null | undefined): string {
  if (v === null || v === undefined) return "—";
  const a = Math.abs(v);
  if (a >= 1e9) return `R$ ${(v / 1e9).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} bi`;
  if (a >= 1e6) return `R$ ${(v / 1e6).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} mi`;
  return brl(v);
}

export function pct(v: number | null | undefined, digits = 1): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return `${(v * 100).toLocaleString("pt-BR", { minimumFractionDigits: digits, maximumFractionDigits: digits })}%`;
}

export function num(v: number | null | undefined, digits = 2): string {
  if (v === null || v === undefined) return "—";
  return v.toLocaleString("pt-BR", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

/**
 * Lê um número digitado pelo usuário, no formato brasileiro ou internacional.
 * Com vírgula, ela é a decimal e os pontos são de milhar ("1.500,50"). Sem vírgula, pontos em grupos
 * de 3 dígitos são de milhar ("1.500", "1.000.000"); senão o ponto é decimal ("10.5", "0.06").
 * Aceita "R$" e "%" em volta. Devolve null se não for um número.
 */
export function parseNumber(input: string | number | null | undefined): number | null {
  if (input === null || input === undefined) return null;
  if (typeof input === "number") return Number.isFinite(input) ? input : null;
  const s = normalizeSeparators(input.trim().replace(/^R\$/i, "").replace(/[\s%]/g, ""));
  if (!/^-?(\d+\.?\d*|\.\d+)$/.test(s)) return null;
  return Number(s);
}

function normalizeSeparators(s: string): string {
  if (s.includes(",")) return s.replace(/\./g, "").replace(",", ".");
  if (/^-?\d{1,3}(\.\d{3})+$/.test(s)) return s.replace(/\./g, "");
  return s;
}

/** parseNumber para campos Decimal da API, que trafegam como string. */
export function decimalStr(input: string | number | null | undefined): string | null {
  const n = parseNumber(input);
  return n === null ? null : String(n);
}

export function dateBr(v: string | null | undefined): string {
  if (!v) return "—";
  const [y, m, d] = v.slice(0, 10).split("-");
  return `${d}/${m}/${y}`;
}

export function todayIso(): string {
  const d = new Date();
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
}

export const CLASS_LABEL: Record<string, string> = {
  renda_fixa: "Renda fixa",
  acoes: "Ações",
  fiis: "FIIs",
  etfs: "ETFs",
  reserva: "Reserva",
  caixa: "Caixa",
  acao: "Ação",
};

export const SECTOR_LABEL: Record<string, string> = {
  bancos: "Bancos",
  seguros: "Seguros",
  energia: "Energia",
  saneamento: "Saneamento",
  telecom: "Telecom",
  perene: "Perene",
  ciclico: "Cíclico",
};

export const FII_KIND_LABEL: Record<string, string> = {
  papel: "Papel",
  tijolo: "Tijolo",
  fof: "Fundo de fundos",
  hibrido: "Híbrido",
};

/** Rótulo do grupo do ativo: o setor de uma ação ou o tipo de um FII. */
export function groupLabel(assetClass: string, sector: string): string {
  const labels = assetClass === "fii" ? FII_KIND_LABEL : SECTOR_LABEL;
  return labels[sector] ?? sector;
}

export const PROFILE_LABEL: Record<string, string> = {
  conservador: "Conservador",
  moderado: "Moderado",
  arrojado: "Arrojado",
};

export const SEGMENT_LABEL: Record<string, string> = {
  transmissao: "transmissão",
  geracao: "geração",
  distribuicao: "distribuição",
  integrada: "integrada",
};

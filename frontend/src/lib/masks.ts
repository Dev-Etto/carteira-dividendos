/**
 * Máscaras dos campos: recebem o texto bruto digitado (ou colado) e devolvem só o que cabe no campo.
 * Não convertem para número: o texto continua do jeito que o usuário escreve ("12," no meio da digitação
 * fica como está) e só vira número no envio, por parseNumber.
 */

export const MONEY_DECIMALS = 2;
export const PERCENT_DECIMALS = 4;
export const TICKER_MAX_LENGTH = 6;

/**
 * Número com vírgula decimal: fica só com dígitos, pontos e a primeira vírgula, e corta as casas depois
 * da vírgula em `decimals`. "R$ 1.500,509" → "1.500,50". Sem casas decimais, a vírgula some.
 */
export function maskDecimal(raw: string, decimals: number): string {
  const kept = raw.replace(/[^\d.,]/g, "");
  const comma = kept.indexOf(",");
  if (comma < 0) return kept;
  const whole = kept.slice(0, comma);
  if (decimals <= 0) return whole;
  const fraction = kept.slice(comma + 1).replace(/\D/g, "").slice(0, decimals);
  return `${whole},${fraction}`;
}

/** Valor em reais, com até 2 casas decimais. */
export function maskMoney(raw: string): string {
  return maskDecimal(raw, MONEY_DECIMALS);
}

/** Percentual, com até 4 casas decimais; o "%" digitado é descartado. */
export function maskPercent(raw: string): string {
  return maskDecimal(raw, PERCENT_DECIMALS);
}

/** Número inteiro: só dígitos. */
export function maskInteger(raw: string): string {
  return raw.replace(/\D/g, "");
}

/** Código de negociação: maiúsculas, só letras e dígitos, no máximo 6 caracteres ("taee 11" → "TAEE11"). */
export function maskTicker(raw: string): string {
  return raw
    .toUpperCase()
    .replace(/[^A-Z0-9]/g, "")
    .slice(0, TICKER_MAX_LENGTH);
}

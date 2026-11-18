import { dateBr, parseNumber } from "./format";

/**
 * Resultado da validação de um campo. Vazio é `{ value: null, error: null }`: não é erro, e quem exige o
 * campo confere `value`. Inválido traz a mensagem, em pt-BR, para mostrar embaixo do campo.
 */
export type Checked<T> = { value: T | null; error: string | null };

type NumberRule = {
  /** Exemplo mostrado quando o texto não é um número. */
  example: string;
  /** Zero não vale. */
  positive?: boolean;
  integer?: boolean;
  max?: number;
  /** Unidade colada ao máximo na mensagem ("%"). */
  unit?: string;
};

type NumberOptions = Pick<NumberRule, "positive" | "max">;

const EMPTY = { value: null, error: null } as const;
const TICKER_PATTERN = /^[A-Z0-9]{3}[A-Z]\d{1,2}$/;
const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;

function fail<T>(error: string): Checked<T> {
  return { value: null, error };
}

function plain(n: number): string {
  return n.toLocaleString("pt-BR", { maximumFractionDigits: 4 });
}

/** Valida um número digitado no formato brasileiro conforme a regra do campo. */
export function checkNumber(text: string, rule: NumberRule): Checked<number> {
  if (!text.trim()) return EMPTY;
  const n = parseNumber(text);
  if (n === null) return fail(`Número inválido. Use, por exemplo, ${rule.example}.`);
  if (n < 0) return fail("O valor não pode ser negativo.");
  if (rule.integer && !Number.isInteger(n)) return fail("Use um número inteiro.");
  if (rule.positive && n === 0) return fail("Informe um valor maior que zero.");
  if (rule.max !== undefined && n > rule.max) return fail(`O máximo é ${plain(rule.max)}${rule.unit ?? ""}.`);
  return { value: n, error: null };
}

/** Valor em reais ("1.500,00"). */
export function checkMoney(text: string, options: NumberOptions = {}): Checked<number> {
  return checkNumber(text, { example: "1.500,00", ...options });
}

/** Percentual digitado como número de 0 a 100 ("6,5" para 6,5%). */
export function checkPercent(text: string, options: NumberOptions = {}): Checked<number> {
  return checkNumber(text, { example: "6,5", unit: "%", ...options });
}

/** Número inteiro, como quantidade de cotas ou prazo em dias. */
export function checkInteger(text: string, options: NumberOptions = {}): Checked<number> {
  return checkNumber(text, { example: "100", integer: true, ...options });
}

/** Número com casas decimais sem unidade, como P/VP ou Dívida/EBITDA ("2,5"). */
export function checkDecimal(text: string, options: NumberOptions = {}): Checked<number> {
  return checkNumber(text, { example: "2,5", ...options });
}

/**
 * Código de negociação da B3: quatro caracteres terminados em letra e um ou dois dígitos
 * (PETR4, TAEE11, HGLG11, B3SA3, AAPL34).
 */
export function checkTicker(text: string): Checked<string> {
  const ticker = text.trim().toUpperCase();
  if (!ticker) return EMPTY;
  if (!TICKER_PATTERN.test(ticker)) return fail("Use o código da B3, como PETR4 ou HGLG11.");
  return { value: ticker, error: null };
}

function isRealDate(iso: string): boolean {
  if (!ISO_DATE.test(iso)) return false;
  const d = new Date(`${iso}T00:00:00Z`);
  return !Number.isNaN(d.getTime()) && d.toISOString().slice(0, 10) === iso;
}

/** Data no formato do `<input type="date">` (AAAA-MM-DD), opcionalmente entre `min` e `max`. */
export function checkDate(text: string, bounds: { min?: string; max?: string } = {}): Checked<string> {
  if (!text) return EMPTY;
  if (!isRealDate(text)) return fail("Data inválida.");
  if (bounds.max && text > bounds.max) return fail(`Use uma data até ${dateBr(bounds.max)}.`);
  if (bounds.min && text < bounds.min) return fail(`Use uma data a partir de ${dateBr(bounds.min)}.`);
  return { value: text, error: null };
}

/** O formulário pode ser enviado: os obrigatórios estão preenchidos e nenhum campo tem erro. */
export function canSubmit(required: Checked<unknown>[], optional: Checked<unknown>[] = []): boolean {
  return required.every((c) => c.value !== null) && [...required, ...optional].every((c) => c.error === null);
}

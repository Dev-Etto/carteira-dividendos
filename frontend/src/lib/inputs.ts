/**
 * Valor da API (Decimal como string ou número) no formato que o usuário digita: vírgula decimal e sem
 * separador de milhar, para que parseNumber leia de volta o mesmo número ("1500.5" → "1500,5").
 */
export function decimalInput(v: number | string | null | undefined): string {
  if (v === null || v === undefined || v === "") return "";
  return Number(v).toLocaleString("pt-BR", { maximumFractionDigits: 8, useGrouping: false });
}

/** Rola até o elemento e foca o campo indicado, sem rolar de novo ao focar. */
export function scrollAndFocus(target: HTMLElement | null, field: HTMLInputElement | null) {
  target?.scrollIntoView({ behavior: "smooth", block: "start" });
  field?.focus({ preventScroll: true });
}

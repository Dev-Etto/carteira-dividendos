import { checkPercent } from "./validation";

/** Faixa que cada classe pode ocupar na divisão-alvo, em %. */
export type AllocationBounds = { min: number; max: number };

/** Faixas que a API aplica por metodologia de divisão; as demais aceitam de 0% a 100%. */
const BOUNDS: Record<string, AllocationBounds> = { arca: { min: 10, max: 40 } };
const FULL_RANGE: AllocationBounds = { min: 0, max: 100 };
const TOTAL = 100;
const TOLERANCE = 0.01;

export function allocationBounds(method: string): AllocationBounds {
  return BOUNDS[method] ?? FULL_RANGE;
}

/** Se a faixa restringe alguma coisa além do óbvio (0% a 100%). */
export function isRestricted(bounds: AllocationBounds): boolean {
  return bounds.min > FULL_RANGE.min || bounds.max < FULL_RANGE.max;
}

export type AllocationRow = { asset_class: string; text: string; value: number | null; error: string | null };

export type AllocationCheck = {
  rows: AllocationRow[];
  /** Soma das classes preenchidas, arredondada a 2 casas. */
  total: number;
  /** Quanto falta (positivo) ou sobra (negativo) para 100%. */
  remaining: number;
  filled: boolean;
  ok: boolean;
  /** O que impede salvar, já na língua do usuário; null quando dá para salvar. */
  problem: string | null;
};

function plain(n: number): string {
  return n.toLocaleString("pt-BR", { maximumFractionDigits: 2 });
}

function rowError(value: number | null, error: string | null, bounds: AllocationBounds, methodLabel: string): string | null {
  if (error) return error;
  if (value === null) return "Informe um percentual.";
  if (value < bounds.min || value > bounds.max)
    return `Fica entre ${plain(bounds.min)}% e ${plain(bounds.max)}% no ${methodLabel}.`;
  return null;
}

function problemOf(filled: boolean, rows: AllocationRow[], remaining: number): string | null {
  if (!filled) return "Preencha todas as classes.";
  const broken = rows.find((r) => r.error);
  if (broken) return broken.error;
  if (Math.abs(remaining) <= TOLERANCE) return null;
  const sign = remaining > 0 ? "Faltam" : "Sobram";
  return `${sign} ${plain(Math.abs(remaining))} p.p. para fechar 100%.`;
}

/**
 * Confere a divisão digitada antes de enviar, com as mesmas regras da API: cada classe preenchida e dentro
 * da faixa da metodologia, e a soma em 100%.
 */
export function checkAllocation(
  items: { asset_class: string; text: string }[],
  bounds: AllocationBounds,
  methodLabel: string,
): AllocationCheck {
  const rows = items.map((i) => {
    const checked = checkPercent(i.text, { max: TOTAL });
    return { ...i, value: checked.value, error: rowError(checked.value, checked.error, bounds, methodLabel) };
  });
  const filled = rows.every((r) => r.value !== null);
  const total = Math.round(rows.reduce((s, r) => s + (r.value ?? 0), 0) * 100) / 100;
  const remaining = Math.round((TOTAL - total) * 100) / 100;
  const problem = problemOf(filled, rows, remaining);
  return { rows, total, remaining, filled, ok: problem === null, problem };
}

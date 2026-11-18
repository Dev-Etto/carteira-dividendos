/** Primeiros `limit` itens, ou todos quando a lista foi expandida. */
export function visibleItems<T>(items: T[], limit: number, expanded: boolean): T[] {
  return expanded ? items : items.slice(0, limit);
}

/** Quantos itens ficam escondidos (0 quando a lista cabe ou já foi expandida). */
export function hiddenCount(total: number, limit: number, expanded: boolean): number {
  return expanded ? 0 : Math.max(0, total - limit);
}

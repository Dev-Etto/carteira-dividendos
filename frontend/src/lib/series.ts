type Point = { date: string; close: number };

function navOn(nav: Point[], date: string): number | null {
  return nav.filter((n) => n.date <= date).at(-1)?.close ?? null;
}

/**
 * Junta a cada fechamento o valor patrimonial vigente naquela data, ou seja, o do último informe
 * mensal até ali. Antes do primeiro informe, `nav` fica nulo. As duas séries vêm em ordem de data.
 */
export function withNav(prices: Point[], nav: Point[]): (Point & { nav: number | null })[] {
  return prices.map((p) => ({ ...p, nav: navOn(nav, p.date) }));
}

import { describe, expect, it } from "vitest";

import { withNav } from "./series";

describe("withNav", () => {
  const prices = [
    { date: "2026-08-20", close: 90 },
    { date: "2026-09-01", close: 92 },
    { date: "2026-09-15", close: 93 },
    { date: "2026-10-10", close: 95 },
  ];
  const nav = [
    { date: "2026-09-01", close: 100 },
    { date: "2026-10-01", close: 101 },
  ];

  it("usa o último informe até a data de cada fechamento", () => {
    expect(withNav(prices, nav).map((p) => p.nav)).toEqual([null, 100, 100, 101]);
  });

  it("sem informes, o VP fica nulo", () => {
    expect(withNav(prices, []).every((p) => p.nav === null)).toBe(true);
  });
});

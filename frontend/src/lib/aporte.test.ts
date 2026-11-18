import { describe, expect, it } from "vitest";

import { effectiveCashUsed } from "./aporte";

describe("caixa usado ao registrar o plano", () => {
  const lines = [{ amount: 483.47 }, { amount: 167.18 }, { amount: 100 }];
  it("usa todo o caixa quando tudo foi executado", () => {
    expect(effectiveCashUsed(300, lines, [true, true, true])).toBe(300);
  });
  it("devolve ao caixa o que não foi executado", () => {
    expect(effectiveCashUsed(3050.76, lines, [false, true, true])).toBe(2567.29);
    expect(effectiveCashUsed(300, lines, [false, true, true])).toBe(0);
  });
});

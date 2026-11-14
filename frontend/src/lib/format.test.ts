import { describe, expect, it } from "vitest";

import { brl, dateBr, decimalStr, num, parseNumber, pct } from "./format";

const NBSP_INTL = "\u00a0";

describe("parseNumber", () => {
  it.each([
    ["1500", 1500],
    ["1.500", 1500],
    ["1.000.000", 1_000_000],
    ["1.500,50", 1500.5],
    ["1500,5", 1500.5],
    ["0,06", 0.06],
    ["0.06", 0.06],
    ["10.5", 10.5],
    ["12.3456", 12.3456],
    ["R$ 1.234,56", 1234.56],
    ["  250 ", 250],
    ["110%", 110],
    [",5", 0.5],
    ["-3,2", -3.2],
    [42, 42],
  ])("%j → %d", (input, expected) => {
    expect(parseNumber(input)).toBe(expected);
  });

  it.each(["", "   ", "abc", "1,500,50", "1..5", "1.5.", "--1", null, undefined, Number.NaN, Infinity])(
    "%j não é número",
    (input) => {
      expect(parseNumber(input)).toBeNull();
    },
  );
});

describe("decimalStr", () => {
  it("normaliza para o formato da API", () => {
    expect(decimalStr("3.000")).toBe("3000");
    expect(decimalStr("33,50")).toBe("33.5");
    expect(decimalStr("x")).toBeNull();
  });
});

describe("formatação", () => {
  it("moeda, percentual e número em pt-BR", () => {
    expect(brl(1234.5)).toBe(`R$${NBSP_INTL}1.234,50`);
    expect(brl(null)).toBe("—");
    expect(pct(0.0612)).toBe("6,1%");
    expect(pct(Number.NaN)).toBe("—");
    expect(num(1234.567, 1)).toBe("1.234,6");
  });

  it("data ISO para dd/mm/aaaa", () => {
    expect(dateBr("2026-11-17")).toBe("17/11/2026");
    expect(dateBr("2026-11-17T19:07:00")).toBe("17/11/2026");
    expect(dateBr(null)).toBe("—");
  });
});

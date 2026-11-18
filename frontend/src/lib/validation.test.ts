import { describe, expect, it } from "vitest";

import { canSubmit, checkDate, checkDecimal, checkInteger, checkMoney, checkPercent, checkTicker } from "./validation";

const EMPTY = { value: null, error: null };

describe("checkMoney", () => {
  it("lê o formato brasileiro", () => {
    expect(checkMoney("1.500,50")).toEqual({ value: 1500.5, error: null });
  });

  it("vazio não é erro", () => {
    expect(checkMoney("  ")).toEqual(EMPTY);
  });

  it("texto que não é número traz exemplo", () => {
    expect(checkMoney("1.5.").error).toBe("Número inválido. Use, por exemplo, 1.500,00.");
  });

  it("zero só vale quando o campo aceita", () => {
    expect(checkMoney("0")).toEqual({ value: 0, error: null });
    expect(checkMoney("0", { positive: true }).error).toBe("Informe um valor maior que zero.");
  });

  it("negativo é recusado", () => {
    expect(checkMoney("-10").error).toBe("O valor não pode ser negativo.");
  });
});

describe("checkPercent", () => {
  it("aceita dentro do máximo", () => {
    expect(checkPercent("100", { max: 100 })).toEqual({ value: 100, error: null });
  });

  it("acima do máximo mostra o limite em %", () => {
    expect(checkPercent("10,5", { max: 10 }).error).toBe("O máximo é 10%.");
  });

  it("número inválido traz exemplo de percentual", () => {
    expect(checkPercent(",").error).toBe("Número inválido. Use, por exemplo, 6,5.");
  });
});

describe("checkInteger", () => {
  it("aceita inteiros", () => {
    expect(checkInteger("100", { positive: true })).toEqual({ value: 100, error: null });
  });

  it("recusa fração", () => {
    expect(checkInteger("1,5").error).toBe("Use um número inteiro.");
  });

  it("recusa zero quando precisa ser positivo", () => {
    expect(checkInteger("0", { positive: true }).error).toBe("Informe um valor maior que zero.");
  });
});

describe("checkDecimal", () => {
  it("lê vírgula decimal", () => {
    expect(checkDecimal("2,5")).toEqual({ value: 2.5, error: null });
  });
});

describe("checkTicker", () => {
  it.each(["PETR4", "TAEE11", "HGLG11", "B3SA3", "AAPL34", "petr4"])("%j é válido", (text) => {
    expect(checkTicker(text)).toEqual({ value: text.toUpperCase(), error: null });
  });

  it.each(["PET", "PETR", "PETR123", "1234", "PETRA"])("%j é inválido", (text) => {
    expect(checkTicker(text).error).toBe("Use o código da B3, como PETR4 ou HGLG11.");
  });

  it("vazio não é erro", () => {
    expect(checkTicker("")).toEqual(EMPTY);
  });
});

describe("checkDate", () => {
  it("aceita data real", () => {
    expect(checkDate("2024-02-29")).toEqual({ value: "2024-02-29", error: null });
  });

  it.each(["2023-02-29", "2024-13-01", "29/02/2024"])("%j é inválida", (text) => {
    expect(checkDate(text).error).toBe("Data inválida.");
  });

  it("respeita o máximo", () => {
    expect(checkDate("2025-01-02", { max: "2025-01-01" }).error).toBe("Use uma data até 01/01/2025.");
  });

  it("respeita o mínimo", () => {
    expect(checkDate("2024-12-31", { min: "2025-01-01" }).error).toBe("Use uma data a partir de 01/01/2025.");
  });

  it("vazio não é erro", () => {
    expect(checkDate("")).toEqual(EMPTY);
  });
});

describe("canSubmit", () => {
  const ok = { value: 1, error: null };
  const bad = { value: null, error: "erro" };

  it("exige os obrigatórios preenchidos", () => {
    expect(canSubmit([ok, EMPTY])).toBe(false);
    expect(canSubmit([ok], [EMPTY])).toBe(true);
  });

  it("bloqueia com erro em qualquer campo", () => {
    expect(canSubmit([ok], [bad])).toBe(false);
  });
});

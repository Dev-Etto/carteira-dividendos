import { describe, expect, it } from "vitest";

import { allocationBounds, checkAllocation, isRestricted, weightText } from "./allocation";

const ARCA = allocationBounds("arca");
const PERFIL = allocationBounds("perfil");

function items(...texts: string[]) {
  return texts.map((text, i) => ({ asset_class: `c${i}`, text }));
}

describe("allocationBounds", () => {
  it("ARCA vai de 10% a 40%; os demais de 0% a 100%", () => {
    expect(ARCA).toEqual({ min: 10, max: 40 });
    expect(PERFIL).toEqual({ min: 0, max: 100 });
    expect(isRestricted(ARCA)).toBe(true);
    expect(isRestricted(PERFIL)).toBe(false);
  });
});

describe("checkAllocation", () => {
  it("soma 100 dentro da faixa pode salvar", () => {
    const out = checkAllocation(items("25", "25", "25", "25"), ARCA, "ARCA");
    expect(out).toMatchObject({ total: 100, remaining: 0, sumOk: true, ok: true, problem: null });
  });

  it("diz quanto falta para 100%", () => {
    const out = checkAllocation(items("20", "30", "45"), PERFIL, "Perfil");
    expect(out.ok).toBe(false);
    expect(out.problem).toBe("Faltam 5 p.p. para fechar 100%.");
  });

  it("diz quanto sobra", () => {
    expect(checkAllocation(items("60", "50,5"), PERFIL, "Perfil").problem).toBe("Sobram 10,5 p.p. para fechar 100%.");
  });

  it("classe fora da faixa do ARCA tem erro mesmo somando 100", () => {
    const out = checkAllocation(items("50", "20", "20", "10"), ARCA, "ARCA");
    expect(out.rows[0]?.error).toBe("Fica entre 10% e 40% no ARCA.");
    expect(out.sumOk).toBe(true);
    expect(out.problem).toBe("Fica entre 10% e 40% no ARCA.");
    expect(out.ok).toBe(false);
  });

  it("classe vazia pede preenchimento", () => {
    const out = checkAllocation(items("50", ""), PERFIL, "Perfil");
    expect(out.filled).toBe(false);
    expect(out.problem).toBe("Preencha todas as classes.");
    expect(out.rows[1]?.error).toBe("Informe um percentual.");
  });

  it("aceita decimais brasileiros", () => {
    expect(checkAllocation(items("33,33", "33,33", "33,34"), PERFIL, "Perfil").ok).toBe(true);
  });
});

describe("weightText", () => {
  it("inteiro sem casas e decimal com vírgula", () => {
    expect(weightText(25)).toBe("25");
    expect(weightText(33.336)).toBe("33,34");
  });
});

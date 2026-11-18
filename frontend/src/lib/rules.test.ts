import { describe, expect, it } from "vitest";

import {
  checkRule,
  ruleDisplay,
  findGroup,
  groupFromParam,
  orderedGroups,
  pendingKeys,
  ruleGroupOf,
  ruleKind,
  rulesBody,
  ruleText,
  ruleValue,
  sameRuleValue,
  selectionGroup,
  splitSubsections,
} from "./rules";

describe("ruleKind", () => {
  it.each([
    ["yield_alvo", "percent"],
    ["liquidez_min", "money"],
    ["nota_comprar", "score"],
    ["proventos_anos_ok", "integer"],
    ["divida_max", "decimal"],
  ])("%s → %s", (key, kind) => {
    expect(ruleKind(key)).toBe(kind);
  });
});

describe("checkRule", () => {
  it("vazio é erro", () => {
    expect(checkRule("divida_max", "")).toEqual({ value: null, error: "Informe um valor." });
  });

  it("nota acima de 100 é erro", () => {
    expect(checkRule("nota_comprar", "101").error).toMatch(/máximo/);
  });

  it("aceita decimal brasileiro", () => {
    expect(checkRule("divida_max", "2,5")).toEqual({ value: 2.5, error: null });
  });
});

describe("ruleText e ruleValue", () => {
  it("percentual vira fração e volta", () => {
    expect(ruleText("yield_alvo", 0.06)).toBe("6");
    expect(ruleValue("yield_alvo", "6,5")).toBeCloseTo(0.065);
  });

  it("reais com separador de milhar, que a leitura entende", () => {
    expect(ruleText("liquidez_min", 1500000)).toBe("1.500.000");
    expect(ruleValue("liquidez_min", "1.500.000")).toBe(1500000);
  });

  it("decimais sem separador de milhar", () => {
    expect(ruleText("divida_max", 1500.5)).toBe("1500,5");
  });

  it("mostra com a unidade", () => {
    expect(ruleDisplay("yield_alvo", 0.06)).toBe("6%");
    expect(ruleDisplay("liquidez_min", 5000000)).toBe("R$ 5.000.000");
    expect(ruleDisplay("divida_max", 2.5)).toBe("2,5");
    expect(ruleDisplay("fii_spread_tijolo_ok", 0.02)).toBe("2 p.p.");
  });

  it("texto inválido não vira valor", () => {
    expect(ruleValue("divida_max", "")).toBeNull();
  });
});

describe("grupos", () => {
  it("chave sem prefixo é do Barsi", () => {
    expect(ruleGroupOf("yield_alvo")).toBe("barsi");
    expect(ruleGroupOf("bazin_yield_alvo")).toBe("bazin");
    expect(ruleGroupOf("fm_fracao_comprar")).toBe("fm");
    expect(ruleGroupOf("fii_pl_min")).toBe("fii");
  });

  it("metodologia de seleção aponta para o grupo; desconhecida cai no Barsi", () => {
    expect(selectionGroup("formula-magica")).toBe("fm");
    expect(selectionGroup("graham")).toBe("graham");
    expect(selectionGroup("outra")).toBe("barsi");
  });

  it("põe o grupo da metodologia escolhida primeiro", () => {
    expect(orderedGroups("graham").map((g) => g.key)).toEqual(["graham", "barsi", "bazin", "fm", "fii", "etf"]);
    expect(orderedGroups("barsi").map((g) => g.key)).toEqual(["barsi", "bazin", "graham", "fm", "fii", "etf"]);
  });

  it("acha o grupo pela chave", () => {
    expect(findGroup("etf").title).toBe("ETFs");
    expect(findGroup("xyz").key).toBe("barsi");
  });

  it("grupo da URL vale se existir; senão o da metodologia", () => {
    expect(groupFromParam("fii", "bazin")).toBe("fii");
    expect(groupFromParam("xyz", "bazin")).toBe("bazin");
    expect(groupFromParam(null, "graham")).toBe("graham");
  });
});

describe("splitSubsections", () => {
  it("separa Papel e Tijolo e tira o prefixo", () => {
    const out = splitSubsections([
      { key: "a", label: "Papel: P/VP máximo" },
      { key: "b", label: "Patrimônio mínimo" },
      { key: "c", label: "Tijolo: vacância" },
    ]);
    expect(out).toEqual([
      { title: null, rules: [{ key: "b", label: "Patrimônio mínimo" }] },
      { title: "Papel", rules: [{ key: "a", label: "P/VP máximo" }] },
      { title: "Tijolo", rules: [{ key: "c", label: "Vacância" }] },
    ]);
  });

  it("sem prefixos, uma subseção só", () => {
    expect(splitSubsections([{ key: "a", label: "ROE" }])).toEqual([{ title: null, rules: [{ key: "a", label: "ROE" }] }]);
  });
});

describe("alterações pendentes", () => {
  const saved = { yield_alvo: 0.06, divida_max: 3 };

  it("texto igual ao salvo não é alteração", () => {
    expect(sameRuleValue("yield_alvo", "6", 0.06)).toBe(true);
    expect(sameRuleValue("yield_alvo", "6,55", 0.0655)).toBe(true);
    expect(pendingKeys({ yield_alvo: "6", divida_max: "3,5" }, saved)).toEqual(["divida_max"]);
  });

  it("texto inválido conta como alteração", () => {
    expect(pendingKeys({ divida_max: "" }, saved)).toEqual(["divida_max"]);
  });

  it("monta o corpo só com as chaves pedidas", () => {
    expect(rulesBody({ yield_alvo: "7", divida_max: "4" }, ["yield_alvo"])).toEqual({ yield_alvo: 0.07 });
  });

  it("corpo nulo se alguma chave for inválida", () => {
    expect(rulesBody({ divida_max: "" }, ["divida_max"])).toBeNull();
  });
});

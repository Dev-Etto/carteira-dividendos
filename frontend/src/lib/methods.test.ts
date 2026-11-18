import { describe, expect, it } from "vitest";

import type { Method } from "./api/client";
import { choiceChanged, focusLabel, methodLabel, resolveChoice, shouldKeepAllocation } from "./methods";

const SAVED = { selection_method: "barsi", allocation_method: "perfil" };

describe("focusLabel", () => {
  it.each([
    ["renda", "Foco em renda"],
    ["valor", "Foco em valor"],
    ["valorizacao", "Foco em valorização"],
    ["divisao", "Divisão da carteira"],
    ["outro", null],
  ])("%s → %s", (focus, label) => {
    expect(focusLabel(focus)).toBe(label);
  });
});

describe("resolveChoice", () => {
  it("sem rascunho, segue o salvo", () => {
    expect(resolveChoice({}, SAVED)).toEqual(SAVED);
  });

  it("o rascunho vence campo a campo", () => {
    expect(resolveChoice({ allocation_method: "arca" }, SAVED)).toEqual({ selection_method: "barsi", allocation_method: "arca" });
    expect(resolveChoice({ selection_method: "bazin" }, SAVED)).toEqual({
      selection_method: "bazin",
      allocation_method: "perfil",
    });
  });
});

describe("choiceChanged", () => {
  it("igual ao salvo não mudou", () => {
    expect(choiceChanged({ ...SAVED }, SAVED)).toBe(false);
  });

  it.each([
    [{ selection_method: "graham", allocation_method: "perfil" }],
    [{ selection_method: "barsi", allocation_method: "arca" }],
  ])("%o mudou", (choice) => {
    expect(choiceChanged(choice, SAVED)).toBe(true);
  });
});

describe("shouldKeepAllocation", () => {
  it("mantém quando já tem perfil, pediu e a divisão não mudou", () => {
    expect(shouldKeepAllocation(true, true, SAVED, SAVED)).toBe(true);
  });

  it("trocar só a seleção ainda mantém", () => {
    expect(shouldKeepAllocation(true, true, { ...SAVED, selection_method: "bazin" }, SAVED)).toBe(true);
  });

  it.each([
    [false, true, SAVED],
    [true, false, SAVED],
    [true, true, { ...SAVED, allocation_method: "arca" }],
  ])("onboarded=%s keep=%s %o → não mantém", (onboarded, keep, choice) => {
    expect(shouldKeepAllocation(onboarded, keep, choice, SAVED)).toBe(false);
  });
});

describe("methodLabel", () => {
  const methods: Method[] = [{ key: "barsi", label: "Barsi", author: "Luiz Barsi", summary: "", focus: "renda" }];

  it("acha o nome pela chave", () => {
    expect(methodLabel(methods, "barsi")).toBe("Barsi");
  });

  it("sem a metodologia na lista, devolve a chave", () => {
    expect(methodLabel(methods, "nova")).toBe("nova");
  });
});

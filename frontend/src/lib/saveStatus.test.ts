import { describe, expect, it } from "vitest";

import { saveStatus } from "./saveStatus";

describe("saveStatus", () => {
  it("problema pendente tem prioridade", () => {
    expect(saveStatus("Salvo.", "Faltam 5 p.p.", 2)).toEqual({ tone: "bad", text: "Faltam 5 p.p." });
  });

  it("conta as alterações no singular e no plural", () => {
    expect(saveStatus(null, null, 1)).toEqual({ tone: "warn", text: "1 alteração não salva" });
    expect(saveStatus(null, null, 3)).toEqual({ tone: "warn", text: "3 alterações não salvas" });
  });

  it("sem pendências, confirma o salvamento", () => {
    expect(saveStatus("Divisão salva.", null, 0)).toEqual({ tone: "good", text: "Divisão salva." });
  });

  it("problema sem pendência não aparece", () => {
    expect(saveStatus(null, "Faltam 5 p.p.", 0)).toEqual({ tone: "muted", text: "Nenhuma alteração pendente." });
  });
});

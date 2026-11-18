import { describe, expect, it } from "vitest";

import { configHref, sectionFromParam } from "./configSections";

describe("sectionFromParam", () => {
  it("seção conhecida", () => {
    expect(sectionFromParam("regras")).toBe("regras");
  });

  it("ausente ou desconhecida abre a primeira", () => {
    expect(sectionFromParam(null)).toBe("perfil");
    expect(sectionFromParam("xyz")).toBe("perfil");
  });
});

describe("configHref", () => {
  it("monta a URL da seção e do grupo", () => {
    expect(configHref("dados")).toBe("/config?secao=dados");
    expect(configHref("regras", "fii")).toBe("/config?secao=regras&grupo=fii");
  });
});

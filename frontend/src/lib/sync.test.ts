import { describe, expect, it } from "vitest";

import { dateTimeBr, stepLabel, syncSummary } from "./sync";

const run = (status: "ok" | "error" | "running", finished_at: string | null) => ({
  source: "macro",
  status,
  started_at: "2026-11-18T19:00:00",
  finished_at,
});

describe("syncSummary", () => {
  it("sem execuções, nunca atualizou", () => {
    expect(syncSummary(false, [])).toEqual({ health: "never", lastFinished: null, errors: 0 });
  });

  it("rodando tem prioridade", () => {
    expect(syncSummary(true, [run("running", null)]).health).toBe("running");
  });

  it("pega o fim mais recente e conta os erros", () => {
    const out = syncSummary(false, [run("running", null), run("error", "2026-11-18T19:05:00"), run("ok", "2026-11-17T19:05:00")]);
    expect(out).toEqual({ health: "error", lastFinished: "2026-11-18T19:05:00", errors: 1 });
  });

  it("tudo ok", () => {
    expect(syncSummary(false, [run("ok", "2026-11-18T19:05:00")]).health).toBe("ok");
  });
});

describe("dateTimeBr", () => {
  it("formata data e hora sem mexer no fuso", () => {
    expect(dateTimeBr("2026-11-18T19:02:31.123")).toBe("18/11/2026 às 19:02");
  });

  it("só data", () => {
    expect(dateTimeBr("2026-11-18")).toBe("18/11/2026");
  });

  it("vazio vira travessão", () => {
    expect(dateTimeBr(null)).toBe("—");
  });
});

describe("stepLabel", () => {
  it("etapa conhecida, desconhecida e vazia", () => {
    expect(stepLabel("cvm")).toBe("Balanços (CVM)");
    expect(stepLabel("nova")).toBe("nova");
    expect(stepLabel(null)).toBe("…");
  });
});

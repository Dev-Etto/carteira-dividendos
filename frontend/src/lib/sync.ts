/** Etapa da atualização de dados como o usuário entende. */
export const STEP_LABEL: Record<string, string> = {
  universo: "Lista de ativos",
  macro: "Selic, CDI e IPCA (Banco Central)",
  tesouro: "Tesouro Direto",
  cvm: "Balanços (CVM)",
  fiis: "Informes de FIIs (CVM)",
  etfs: "Patrimônio dos ETFs (CVM)",
  mercado: "Preços e proventos",
  proventos: "Proventos que faltam no Yahoo (B3)",
  avaliacoes: "Avaliações",
};

export function stepLabel(step: string | null | undefined): string {
  return STEP_LABEL[step ?? ""] ?? step ?? "…";
}

type Run = { source: string; status: "running" | "ok" | "error"; started_at: string; finished_at: string | null };

export type SyncHealth = "never" | "running" | "ok" | "error";

export type SyncSummary = {
  health: SyncHealth;
  /** Fim da etapa concluída mais recente (data-hora da API). */
  lastFinished: string | null;
  /** Etapas com erro entre as execuções listadas. */
  errors: number;
};

function healthOf(running: boolean, runs: Run[], errors: number): SyncHealth {
  if (running) return "running";
  if (runs.length === 0) return "never";
  return errors > 0 ? "error" : "ok";
}

/** Resumo das execuções recentes (a API manda da mais nova para a mais antiga). */
export function syncSummary(running: boolean, runs: Run[]): SyncSummary {
  const errors = runs.filter((r) => r.status === "error").length;
  const lastFinished = runs.find((r) => r.finished_at)?.finished_at ?? null;
  return { health: healthOf(running, runs, errors), lastFinished, errors };
}

/** Data-hora da API ("2026-11-18T19:02:31") como "18/11/2026 às 19:02", sem conversão de fuso. */
export function dateTimeBr(iso: string | null | undefined): string {
  if (!iso) return "—";
  const [y, m, d] = iso.slice(0, 10).split("-");
  const time = iso.slice(11, 16);
  if (!time) return `${d}/${m}/${y}`;
  return `${d}/${m}/${y} às ${time}`;
}

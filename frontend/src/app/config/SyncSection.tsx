"use client";

import { useEffect, useState } from "react";

import { Button, Card, ErrorBox, Loading } from "@/components/ui";
import { api, type SyncStatus } from "@/lib/api/client";
import { num } from "@/lib/format";
import { dateTimeBr, stepLabel, syncSummary, type SyncHealth } from "@/lib/sync";
import { useApi } from "@/lib/useApi";

import { errorText } from "./parts";

const POLL_MS = 2500;
const ERROR_PREVIEW = 120;

type SyncRun = SyncStatus["runs"][number];

const HEALTH: Record<SyncHealth, { title: string; dot: string; box: string }> = {
  never: { title: "Os dados ainda não foram baixados", dot: "bg-warn", box: "border-warn/30 bg-warn-soft" },
  running: { title: "Atualizando os dados", dot: "bg-accent animate-pulse", box: "border-accent/30 bg-accent-soft" },
  ok: { title: "Dados atualizados", dot: "bg-good", box: "border-good/30 bg-good-soft" },
  error: { title: "Última atualização teve erros", dot: "bg-bad", box: "border-bad/30 bg-bad-soft" },
};

const RUN_STATUS: Record<SyncRun["status"], { label: string; cls: string }> = {
  ok: { label: "ok", cls: "bg-good-soft text-good" },
  error: { label: "erro", cls: "bg-bad-soft text-bad" },
  running: { label: "rodando", cls: "bg-neutral-soft text-muted" },
};

function detail(health: SyncHealth, step: string | null, lastFinished: string | null, errors: number): string {
  if (health === "running") return `Etapa atual: ${stepLabel(step)}.`;
  if (health === "never") return "A primeira atualização baixa vários anos de balanços e preços e pode levar alguns minutos.";
  const errorsNote = errors > 0 ? ` ${errors} etapa(s) com erro no histórico abaixo.` : "";
  return `Última etapa concluída em ${dateTimeBr(lastFinished)}.${errorsNote}`;
}

/** Status em destaque com o botão de atualizar ao lado. */
function StatusPanel({ status, onStart, err }: { status: SyncStatus; onStart: () => void; err: string | null }) {
  const summary = syncSummary(status.running, status.runs);
  const h = HEALTH[summary.health];
  return (
    <div className={`rounded-2xl border p-5 ${h.box}`}>
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex min-w-0 items-start gap-3">
          <span aria-hidden="true" className={`mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full ${h.dot}`} />
          <div className="min-w-0">
            <div className="text-lg font-bold text-ink">{h.title}</div>
            <p className="mt-0.5 text-sm text-label">
              {detail(summary.health, status.step, summary.lastFinished, summary.errors)}
            </p>
          </div>
        </div>
        <Button onClick={onStart} disabled={status.running}>
          {status.running ? "Atualizando…" : "Atualizar dados agora"}
        </Button>
      </div>
      {err && (
        <div className="mt-4">
          <ErrorBox error={err} />
        </div>
      )}
    </div>
  );
}

/** Histórico compacto: uma linha por etapa, com situação, linhas gravadas e horário. */
function RunHistory({ runs }: { runs: SyncRun[] }) {
  if (runs.length === 0) return null;
  return (
    <Card title="Histórico recente">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-line text-left text-[13px] font-semibold text-subtle">
            <th className="pb-2 pr-3 font-semibold">Etapa</th>
            <th className="pb-2 pr-3 font-semibold">Situação</th>
            <th className="pb-2 pr-3 text-right font-semibold">Linhas</th>
            <th className="pb-2 text-right font-semibold">Início</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {runs.map((r, i) => (
            <tr key={i} className="align-top">
              <td className="py-2 pr-3 text-ink">
                {stepLabel(r.source)}
                {r.error && (
                  <span className="mt-0.5 block text-[13px] text-bad" title={r.error}>
                    {r.error.slice(0, ERROR_PREVIEW)}
                  </span>
                )}
              </td>
              <td className="py-2 pr-3">
                <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-semibold ${RUN_STATUS[r.status].cls}`}>
                  {RUN_STATUS[r.status].label}
                </span>
              </td>
              <td className="py-2 pr-3 text-right tabular-nums text-muted">{r.status === "ok" ? num(r.rows, 0) : "—"}</td>
              <td className="whitespace-nowrap py-2 text-right tabular-nums text-muted">{dateTimeBr(r.started_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}

/** Atualização dos dados do mercado: status, botão e histórico. Consulta o status enquanto há uma rodando. */
export function SyncSection() {
  const { data, error, reload } = useApi<SyncStatus>("/api/sync/status");
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    if (!data?.running) return;
    const id = setInterval(() => void reload(), POLL_MS);
    return () => clearInterval(id);
  }, [data?.running, reload]);

  async function start() {
    setErr(null);
    try {
      await api.post("/api/sync");
      await reload();
    } catch (e) {
      setErr(errorText(e));
    }
  }

  if (error && !data) return <ErrorBox error={error} onRetry={() => void reload()} />;
  if (!data) return <Loading />;
  return (
    <div className="space-y-5">
      <StatusPanel status={data} onStart={() => void start()} err={err} />
      <p className="text-sm text-muted">
        Depois da primeira vez, o app atualiza sozinho todo dia às 19h enquanto a API estiver rodando. Para cotações em tempo
        real, coloque seu token gratuito da brapi no arquivo{" "}
        <code className="rounded bg-neutral-soft px-1.5 text-[13px]">backend/.env</code>.
      </p>
      <RunHistory runs={data.runs} />
    </div>
  );
}

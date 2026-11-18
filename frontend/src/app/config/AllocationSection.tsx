"use client";

import { useState } from "react";

import { PercentInput } from "@/components/inputs";
import { Card, ErrorBox, FieldRow, Loading } from "@/components/ui";
import { api, type AllocationItem } from "@/lib/api/client";
import { allocationBounds, checkAllocation, isRestricted, weightText, type AllocationBounds } from "@/lib/allocation";
import { CLASS_LABEL, num } from "@/lib/format";
import { saveStatus } from "@/lib/saveStatus";
import { useApi } from "@/lib/useApi";

import { errorText, SaveBar } from "./parts";

const FULL = 100;

function shown(value: number): string {
  return num(value, value % 1 ? 2 : 0);
}

/** Barra do peso da classe, com a faixa permitida pela metodologia sombreada quando ela restringe. */
function WeightBar({ value, bounds, invalid }: { value: number; bounds: AllocationBounds; invalid: boolean }) {
  return (
    <span className="relative mt-2 block h-2 w-full max-w-sm overflow-hidden rounded-full bg-neutral-soft" aria-hidden="true">
      {isRestricted(bounds) && (
        <span
          className="absolute inset-y-0 bg-accent-soft"
          style={{ left: `${bounds.min}%`, width: `${bounds.max - bounds.min}%` }}
        />
      )}
      <span
        className={`absolute inset-y-0 left-0 rounded-full ${invalid ? "bg-bad" : "bg-accent"}`}
        style={{ width: `${Math.min(FULL, value)}%` }}
      />
    </span>
  );
}

function totalNote(filled: boolean, sumOk: boolean, remaining: number): string {
  if (!filled) return "Preencha todas as classes";
  if (sumOk) return "Fecha 100%";
  const verb = remaining > 0 ? "Faltam" : "Sobram";
  return `${verb} ${shown(Math.abs(remaining))} p.p.`;
}

/** Soma das classes em destaque, com quanto falta ou sobra para 100%. */
function TotalRow({ total, remaining, filled, sumOk }: { total: number; remaining: number; filled: boolean; sumOk: boolean }) {
  const tone = sumOk ? "text-good" : "text-bad";
  return (
    <div className="grid items-center gap-x-6 gap-y-1 rounded-xl bg-neutral-soft px-4 py-3 sm:grid-cols-[minmax(0,1fr)_minmax(0,220px)]">
      <span className="text-sm font-semibold text-ink">Total</span>
      <span className="flex items-baseline justify-between gap-3">
        <strong className={`text-xl tabular-nums ${tone}`}>{shown(total)}%</strong>
        <span className={`text-[13px] font-medium ${tone}`}>{totalNote(filled, sumOk, remaining)}</span>
      </span>
    </div>
  );
}

/**
 * Divisão-alvo por classe, nas classes da metodologia de divisão. A soma e a faixa de cada classe são
 * conferidas enquanto o usuário digita, com as mesmas regras da API; o que a API recusar aparece embaixo.
 */
export function AllocationSection({ method, methodName }: { method: string; methodName: string }) {
  const { data, error, reload } = useApi<AllocationItem[]>("/api/alocacao");
  const [edits, setEdits] = useState<Record<string, string>>({});
  const [saved, setSaved] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  if (error && !data) return <ErrorBox error={error} onRetry={() => void reload()} />;
  if (!data) return <Loading />;

  const items = data;
  const bounds = allocationBounds(method);
  const check = checkAllocation(
    data.map((i) => ({ asset_class: i.asset_class, text: edits[i.asset_class] ?? weightText(i.weight_pct) })),
    bounds,
    methodName,
  );
  const pending = check.rows.filter((r, idx) => r.value !== data[idx]?.weight_pct).length;

  async function save() {
    setErr(null);
    setSaved(null);
    setSaving(true);
    const body: AllocationItem[] = items.map((i, idx) => ({
      asset_class: i.asset_class,
      weight_pct: check.rows[idx]?.value ?? 0,
    }));
    try {
      await api.put("/api/alocacao", body);
      await reload();
      setEdits({});
      setSaved("Divisão salva. O próximo aporte já segue os novos alvos.");
    } catch (e) {
      setErr(errorText(e));
    }
    setSaving(false);
  }

  function edit(assetClass: string, text: string) {
    setSaved(null);
    setEdits((s) => ({ ...s, [assetClass]: text }));
  }

  return (
    <Card title={`Divisão-alvo pelo ${methodName}`} help="diversificacao">
      <p className="-mt-2 mb-5 max-w-2xl text-sm text-muted">
        Quanto da carteira cada classe deve ter. A soma precisa dar 100%.
        {isRestricted(bounds) && ` No ${methodName}, cada classe fica entre ${bounds.min}% e ${bounds.max}% (faixa sombreada).`}
      </p>
      <div className="max-w-3xl divide-y divide-line">
        {check.rows.map((r) => (
          <div key={r.asset_class} className="py-3 first:pt-0">
            <FieldRow
              label={CLASS_LABEL[r.asset_class] ?? r.asset_class}
              description={<WeightBar value={r.value ?? 0} bounds={bounds} invalid={r.error !== null} />}
              error={r.error}
            >
              <span className="relative block">
                <PercentInput
                  className="pr-9 text-right tabular-nums"
                  value={r.text}
                  onValueChange={(text) => edit(r.asset_class, text)}
                />
                <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-sm text-subtle">%</span>
              </span>
            </FieldRow>
          </div>
        ))}
      </div>
      <div className="mt-3 max-w-3xl">
        <TotalRow total={check.total} remaining={check.remaining} filled={check.filled} sumOk={check.sumOk} />
      </div>
      {err && (
        <div className="mt-4">
          <ErrorBox error={err} />
        </div>
      )}
      <SaveBar
        status={saveStatus(saved, check.problem, pending)}
        dirty={pending > 0}
        canSave={pending > 0 && check.ok}
        saving={saving}
        onSave={() => void save()}
        onDiscard={() => {
          setEdits({});
          setErr(null);
        }}
        saveLabel="Salvar divisão"
      />
    </Card>
  );
}

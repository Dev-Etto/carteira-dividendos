"use client";

import Link from "next/link";
import { useState } from "react";

import { Button, Card, ErrorBox, Field, inputCls } from "@/components/ui";
import { api, type FixedIncomeIn, type Plan, type S } from "@/lib/api/client";
import { brl, CLASS_LABEL, decimalStr, num, todayIso } from "@/lib/format";

type PlanLine = Plan["lines"][number];
type PlanPurchaseIn = S["PlanPurchaseIn"];
export type RegisterPlanOut = S["RegisterPlanOut"];

type Entry = { selected: boolean; quantity: string; price: string; amount: string };
type Payload = { purchases: PlanPurchaseIn[]; holdings: FixedIncomeIn[] };
type Built = { ok: true; payload: Payload } | { ok: false; error: string };
type Checked<T> = { value: T; error?: undefined } | { value?: undefined; error: string };

function isRegistrable(line: PlanLine): boolean {
  return Boolean(line.ticker || line.holding);
}

function initialEntries(plan: Plan): Entry[] {
  return plan.lines.map((l) => ({
    selected: isRegistrable(l),
    quantity: l.quantity === null ? "" : String(l.quantity),
    price: num(l.unit_price, 2),
    amount: num(l.holding ? Number(l.holding.amount) : l.amount, 2),
  }));
}

function isPositive(value: string | null): value is string {
  return value !== null && Number(value) > 0;
}

function purchaseOf(ticker: string, entry: Entry): Checked<PlanPurchaseIn> {
  const quantity = decimalStr(entry.quantity);
  const price = decimalStr(entry.price);
  if (!isPositive(quantity) || !isPositive(price)) return { error: `Quantidade ou preço pago de ${ticker} inválido.` };
  return { value: { ticker, quantity, price, fees: "0" } };
}

function holdingOf(product: string, holding: FixedIncomeIn, entry: Entry, day: string): Checked<FixedIncomeIn> {
  const amount = decimalStr(entry.amount);
  if (!isPositive(amount)) return { error: `Valor aplicado em ${product} inválido.` };
  return { value: { ...holding, amount, start_date: day } };
}

function valuesOf<T>(items: Checked<T>[]): T[] {
  return items.flatMap((item) => (item.value === undefined ? [] : [item.value]));
}

/** Monta o corpo do registro a partir das linhas marcadas; devolve o primeiro valor inválido como erro. */
function buildPayload(plan: Plan, entries: Entry[], day: string): Built {
  const chosen = plan.lines.flatMap((line, i) => {
    const entry = entries[i];
    return entry?.selected ? [{ line, entry }] : [];
  });
  const purchases = chosen.flatMap(({ line, entry }) => (line.ticker ? [purchaseOf(line.ticker, entry)] : []));
  const holdings = chosen.flatMap(({ line, entry }) => (line.holding ? [holdingOf(line.product, line.holding, entry, day)] : []));
  const failed = [...purchases, ...holdings].find((item) => item.error !== undefined);
  if (failed?.error) return { ok: false, error: failed.error };
  if (!purchases.length && !holdings.length) return { ok: false, error: "Marque ao menos uma compra ou aplicação." };
  return { ok: true, payload: { purchases: valuesOf(purchases), holdings: valuesOf(holdings) } };
}

function errorMessage(e: unknown): string {
  return e instanceof Error ? e.message : String(e);
}

/**
 * Checklist do que foi feito a partir do plano: compras de ações (quantidade e preço pagos) e aplicações
 * de renda fixa (valor aplicado). Tudo é registrado numa única chamada, ou nada é.
 */
export function RegisterPlanCard({ plan, onRegistered }: { plan: Plan; onRegistered: (result: RegisterPlanOut) => void }) {
  const [entries, setEntries] = useState<Entry[]>(() => initialEntries(plan));
  const [day, setDay] = useState(todayIso());
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const update = (index: number, patch: Partial<Entry>) =>
    setEntries((all) => all.map((entry, i) => (i === index ? { ...entry, ...patch } : entry)));

  async function register() {
    const built = buildPayload(plan, entries, day);
    if (!built.ok) return setErr(built.error);
    setErr(null);
    setBusy(true);
    try {
      onRegistered(await api.post<RegisterPlanOut>("/api/aporte/registrar", { date: day, ...built.payload }));
    } catch (e) {
      setErr(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card title="Depois de comprar na corretora e aplicar no banco">
      <p className="mb-4 text-sm text-muted">
        Marque o que você fez, ajuste os valores reais e registre tudo de uma vez: as ações entram na Carteira e as aplicações em
        Renda fixa.
      </p>
      <ul className="divide-y divide-line">
        {plan.lines.map((line, i) => (
          <PlanLineEntry key={i} line={line} entry={entries[i]} onChange={(patch) => update(i, patch)} />
        ))}
      </ul>
      <div className="mt-4 flex flex-wrap items-end gap-3">
        <div className="w-44">
          <Field label="Data da operação">
            <input type="date" className={inputCls} value={day} max={todayIso()} onChange={(e) => setDay(e.target.value)} />
          </Field>
        </div>
        <Button onClick={register} disabled={busy}>
          {busy ? "Registrando…" : "Registrar selecionados"}
        </Button>
      </div>
      {err && (
        <div className="mt-3">
          <ErrorBox error={err} />
        </div>
      )}
    </Card>
  );
}

function PlanLineEntry({ line, entry, onChange }: { line: PlanLine; entry?: Entry; onChange: (patch: Partial<Entry>) => void }) {
  if (!entry) return null;
  const title = line.ticker ? `${line.ticker} · ${line.product}` : line.product;
  return (
    <li className="flex flex-wrap items-start gap-3 py-3">
      <input
        type="checkbox"
        className="mt-1"
        aria-label={`Registrar ${title}`}
        checked={entry.selected}
        disabled={!isRegistrable(line)}
        onChange={(e) => onChange({ selected: e.target.checked })}
      />
      <div className="min-w-0 flex-1">
        <div className="text-xs font-semibold uppercase tracking-wide text-muted">
          {CLASS_LABEL[line.asset_class] ?? line.asset_class}
        </div>
        <div className="text-sm font-semibold text-ink">{title}</div>
        <LineFields line={line} entry={entry} onChange={onChange} />
      </div>
    </li>
  );
}

function LineFields({ line, entry, onChange }: { line: PlanLine; entry: Entry; onChange: (patch: Partial<Entry>) => void }) {
  if (line.ticker) {
    return (
      <div className="mt-2 grid max-w-md gap-3 sm:grid-cols-2">
        <Field label="Quantidade">
          <input
            className={inputCls}
            inputMode="numeric"
            value={entry.quantity}
            disabled={!entry.selected}
            onChange={(e) => onChange({ quantity: e.target.value })}
          />
        </Field>
        <Field label="Preço pago (R$)">
          <input
            className={inputCls}
            inputMode="decimal"
            value={entry.price}
            disabled={!entry.selected}
            onChange={(e) => onChange({ price: e.target.value })}
          />
        </Field>
      </div>
    );
  }
  if (line.holding) {
    return (
      <div className="mt-2 max-w-[14rem]">
        <Field label="Valor aplicado (R$)">
          <input
            className={inputCls}
            inputMode="decimal"
            value={entry.amount}
            disabled={!entry.selected}
            onChange={(e) => onChange({ amount: e.target.value })}
          />
        </Field>
      </div>
    );
  }
  const params = new URLSearchParams({ nome: line.product, valor: num(line.amount, 2), reserva: "0" });
  return (
    <p className="mt-1 text-sm text-muted">
      Aqui você escolhe o título ou CDB ({brl(line.amount)}).{" "}
      <Link className="font-semibold text-accent underline" href={`/renda-fixa?${params.toString()}`}>
        Cadastrar em Renda fixa →
      </Link>
    </p>
  );
}

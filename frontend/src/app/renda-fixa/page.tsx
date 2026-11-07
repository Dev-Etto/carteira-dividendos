"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";

import {
  Button,
  Card,
  ConfirmAction,
  ErrorBox,
  Field,
  Help,
  inputCls,
  Loading,
  PageHeader,
  ProgressBar,
  Stat,
} from "@/components/ui";
import { api, type Compare, type FixedIncome, type Portfolio, type Treasury } from "@/lib/api/client";
import { brl, dateBr, decimalStr, parseNumber, pct, todayIso } from "@/lib/format";
import { decimalInput, scrollAndFocus } from "@/lib/inputs";
import { useApi } from "@/lib/useApi";

const KIND_LABEL: Record<string, string> = { tesouro: "Tesouro Direto", cdb: "CDB", lci: "LCI", lca: "LCA", outro: "Outro" };

export default function RendaFixaPage() {
  return (
    <Suspense fallback={<Loading />}>
      <RendaFixa />
    </Suspense>
  );
}

/**
 * Renda fixa. `?nome=&valor=&reserva=1|0` (vindo do Aporte) pré-preenche o cadastro e rola até ele.
 */
function RendaFixa() {
  const holdings = useApi<FixedIncome[]>("/api/renda-fixa");
  const pf = useApi<Portfolio>("/api/carteira");
  const tesouro = useApi<Treasury[]>("/api/renda-fixa/tesouro");
  const params = useSearchParams();
  const [removeErr, setRemoveErr] = useState<string | null>(null);
  const [editing, setEditing] = useState<FixedIncome | null>(null);
  const prefill = params.has("nome") || params.has("valor") ? params : null;

  function reloadAll() {
    void holdings.reload();
    void pf.reload();
  }

  async function remove(h: FixedIncome) {
    setRemoveErr(null);
    try {
      await api.del(`/api/renda-fixa/${h.id}`);
      setEditing((current) => (current?.id === h.id ? null : current));
      void holdings.reload();
      void pf.reload();
    } catch (e) {
      setRemoveErr(e instanceof Error ? e.message : String(e));
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Renda fixa e reserva"
        subtitle="Aqui fica sua reserva de emergência e a parte de renda fixa da carteira. A reserva vem antes de qualquer ação ou FII."
      />

      {pf.data && (
        <Card title="Reserva de emergência" help="reserva-de-emergencia">
          <div className="grid gap-4 sm:grid-cols-3">
            <Stat label="Guardado" value={brl(pf.data.reserve_value)} />
            <Stat label="Meta" value={brl(pf.data.reserve_target)} />
            <Stat label="Falta" value={brl(Math.max(0, pf.data.reserve_target - pf.data.reserve_value))} />
          </div>
          <ProgressBar className="mt-4" value={pf.data.reserve_value} max={pf.data.reserve_target} />
          <p className="mt-3 text-sm text-muted">
            Onde guardar: <strong className="text-ink">Tesouro Selic</strong> <Help slug="tesouro-selic" /> ou CDB de liquidez
            diária que pague pelo menos 100% do CDI, de banco coberto pelo FGC <Help slug="fgc" />. Nada de ações, FIIs ou títulos
            com vencimento longo aqui.
          </p>
        </Card>
      )}

      <Card title="Suas aplicações">
        <HoldingsList
          loading={holdings.loading}
          data={holdings.data}
          error={holdings.error}
          editingId={editing?.id ?? null}
          onEdit={setEditing}
          onRemove={remove}
        />
        {removeErr && (
          <div className="mt-3">
            <ErrorBox error={removeErr} />
          </div>
        )}
        <div className="mt-5 border-t border-line pt-5">
          <HoldingForm
            key={editing ? `editar-${editing.id}` : `novo-${params.toString()}`}
            editing={editing}
            prefill={prefill}
            onSaved={() => {
              setEditing(null);
              reloadAll();
            }}
            onCancel={() => setEditing(null)}
          />
        </div>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Comparator />
        <Card title="Tesouro Direto hoje">
          <TreasuryList loading={tesouro.loading} data={tesouro.data} />
        </Card>
      </div>
    </div>
  );
}

function HoldingsList({
  loading,
  data,
  error,
  editingId,
  onEdit,
  onRemove,
}: {
  loading: boolean;
  data: FixedIncome[] | null;
  error: string | null;
  editingId: number | null;
  onEdit: (h: FixedIncome) => void;
  onRemove: (h: FixedIncome) => Promise<void>;
}) {
  if (loading && !data) return <Loading />;
  if (error) return <ErrorBox error={error} />;
  if (!data?.length) return <p className="text-sm text-muted">Nenhuma aplicação cadastrada.</p>;
  return (
    <ul className="divide-y divide-line">
      {data.map((h) => (
        <li
          key={h.id}
          className={`flex flex-wrap items-start justify-between gap-3 py-3 text-sm ${h.id === editingId ? "bg-accent-soft" : ""}`}
        >
          <div>
            <div className="font-semibold text-ink">
              {h.name}{" "}
              {h.is_emergency_reserve && (
                <span className="ml-1 rounded bg-accent-soft px-1.5 py-0.5 text-[10px] font-semibold text-accent">reserva</span>
              )}
            </div>
            <div className="text-xs text-muted">
              {KIND_LABEL[h.kind]} · {h.issuer} · {rateLabel(h.indexer, h.rate)} · desde {dateBr(h.start_date)}
              {h.maturity ? ` · vence ${dateBr(h.maturity)}` : ""}
              {h.daily_liquidity ? " · liquidez diária" : ""}
            </div>
            {h.is_emergency_reserve && !h.reserve_ok && (
              <div className="mt-1 text-xs text-warn">Atenção para a reserva: {h.reserve_reason}</div>
            )}
          </div>
          <div className="flex items-center gap-3">
            <span className="font-semibold tabular-nums">{brl(h.amount)}</span>
            <button type="button" className="text-xs text-accent hover:underline" onClick={() => onEdit(h)}>
              atualizar saldo / editar
            </button>
            <ConfirmAction label="remover" onConfirm={() => void onRemove(h)} />
          </div>
        </li>
      ))}
    </ul>
  );
}

function bondRate(b: Treasury): string {
  if (b.name.includes("Selic")) return `Selic + ${pct(b.buy_rate, 4)}`;
  if (b.name.includes("IPCA")) return `IPCA + ${pct(b.buy_rate, 2)}`;
  return pct(b.buy_rate, 2);
}

function TreasuryList({ loading, data }: { loading: boolean; data: Treasury[] | null }) {
  if (loading && !data) return <Loading />;
  if (!data?.length) return <p className="text-sm text-muted">Sem dados. Rode a atualização em Configurações.</p>;
  return (
    <>
      <p className="mb-3 text-xs text-muted">Taxas de compra em {dateBr(data[0]?.date)} (Tesouro Transparente).</p>
      <ul className="max-h-80 divide-y divide-line overflow-y-auto text-sm">
        {data.map((b) => (
          <li key={`${b.name}-${b.maturity}`} className="flex justify-between py-2">
            <span>
              {b.name} <span className="text-muted">{b.maturity.slice(0, 4)}</span>
            </span>
            <span className="tabular-nums">{bondRate(b)}</span>
          </li>
        ))}
      </ul>
    </>
  );
}

function rateLabel(indexer: string, rate: number) {
  if (indexer === "cdi") return `${rate}% do CDI`;
  if (indexer === "ipca") return `IPCA + ${rate}%`;
  if (indexer === "selic") return "Selic";
  return `${rate}% a.a.`;
}

type HoldingFields = {
  name: string;
  issuer: string;
  kind: string;
  indexer: string;
  rate: string;
  start_date: string;
  maturity: string;
  daily_liquidity: boolean;
  amount: string;
  is_emergency_reserve: boolean;
  fgc_covered: boolean;
};

function tesouroSelic(): HoldingFields {
  return {
    name: "Tesouro Selic",
    issuer: "Tesouro Nacional",
    kind: "tesouro",
    indexer: "selic",
    rate: "0",
    start_date: todayIso(),
    maturity: "",
    daily_liquidity: true,
    amount: "",
    is_emergency_reserve: true,
    fgc_covered: true,
  };
}

const BANK_KINDS = ["cdb", "lci", "lca"];

/** Tipo e indexador deduzidos do nome quando ele não deixa dúvida (ex.: "Tesouro IPCA+ 2035"). */
function guessFromName(name: string): Partial<HoldingFields> {
  const lower = name.toLowerCase();
  if (lower.includes(" ou ")) return {};
  if (lower.includes("tesouro selic")) return { kind: "tesouro", indexer: "selic", issuer: "Tesouro Nacional" };
  if (lower.includes("tesouro ipca"))
    return { kind: "tesouro", indexer: "ipca", issuer: "Tesouro Nacional", daily_liquidity: false };
  return {};
}

function reserveParam(value: string | null, fallback: boolean): boolean {
  if (value === "1") return true;
  if (value === "0") return false;
  return fallback;
}

function fromParams(params: URLSearchParams): HoldingFields {
  const base = tesouroSelic();
  const name = params.get("nome") ?? base.name;
  const guessed = { ...base, name, ...guessFromName(name) };
  return {
    ...guessed,
    amount: decimalInput(parseNumber(params.get("valor"))),
    is_emergency_reserve: reserveParam(params.get("reserva"), guessed.is_emergency_reserve),
  };
}

function fromHolding(h: FixedIncome): HoldingFields {
  return {
    name: h.name,
    issuer: h.issuer,
    kind: h.kind,
    indexer: h.indexer,
    rate: decimalInput(h.rate),
    start_date: h.start_date,
    maturity: h.maturity ?? "",
    daily_liquidity: h.daily_liquidity,
    amount: decimalInput(h.amount),
    is_emergency_reserve: h.is_emergency_reserve,
    fgc_covered: h.fgc_covered,
  };
}

function initialHolding(editing: FixedIncome | null, prefill: URLSearchParams | null): HoldingFields {
  if (editing) return fromHolding(editing);
  if (prefill) return fromParams(prefill);
  return tesouroSelic();
}

/**
 * Padrões ao trocar tipo ou indexador: Tesouro Selic é o lugar da reserva (liquidez diária); CDB, LCI e LCA
 * começam fora da reserva, e o usuário marca se quiser.
 */
function withDefaults(f: HoldingFields, changed: keyof HoldingFields): HoldingFields {
  if (changed !== "kind" && changed !== "indexer") return f;
  if (f.kind === "tesouro" && f.indexer === "selic") return { ...f, is_emergency_reserve: true, daily_liquidity: true };
  if (changed === "kind" && BANK_KINDS.includes(f.kind)) return { ...f, is_emergency_reserve: false };
  return f;
}

function HoldingForm({
  editing,
  prefill,
  onSaved,
  onCancel,
}: {
  editing: FixedIncome | null;
  prefill: URLSearchParams | null;
  onSaved: () => void;
  onCancel: () => void;
}) {
  const [f, setF] = useState<HoldingFields>(() => initialHolding(editing, prefill));
  const [err, setErr] = useState<string | null>(null);
  const formRef = useRef<HTMLDivElement>(null);
  const amountRef = useRef<HTMLInputElement>(null);
  const focusOnMount = Boolean(editing || prefill);
  useEffect(() => {
    if (focusOnMount) scrollAndFocus(formRef.current, amountRef.current);
  }, [focusOnMount]);
  const set = (k: keyof HoldingFields) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const t = e.target as HTMLInputElement;
    setF((s) => withDefaults({ ...s, [k]: t.type === "checkbox" ? t.checked : t.value }, k));
  };
  async function save() {
    setErr(null);
    const rate = parseNumber(f.rate || "0");
    const amount = decimalStr(f.amount);
    if (rate === null || amount === null) return setErr("Taxa e valor precisam ser números (ex.: 110 ou 1.000,00).");
    const body = { ...f, rate, amount, maturity: f.maturity || null };
    try {
      await (editing ? api.put(`/api/renda-fixa/${editing.id}`, body) : api.post("/api/renda-fixa", body));
      setF((s) => ({ ...s, amount: "" }));
      onSaved();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    }
  }
  return (
    <div ref={formRef} className="scroll-mt-6">
      <div className="mb-1 text-sm font-semibold text-ink">{editing ? `Editar ${editing.name}` : "Cadastrar aplicação"}</div>
      {editing && (
        <p className="mb-3 text-xs text-muted">Para atualizar o saldo, troque o valor pelo que aparece hoje na corretora.</p>
      )}
      <div className="mt-3 grid gap-3 sm:grid-cols-4">
        <Field label="Nome">
          <input className={inputCls} value={f.name} onChange={set("name")} />
        </Field>
        <Field label="Emissor">
          <input className={inputCls} value={f.issuer} onChange={set("issuer")} />
        </Field>
        <Field label="Tipo">
          <select className={inputCls} value={f.kind} onChange={set("kind")}>
            {Object.entries(KIND_LABEL).map(([k, v]) => (
              <option key={k} value={k}>
                {v}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Indexador">
          <select className={inputCls} value={f.indexer} onChange={set("indexer")}>
            <option value="selic">Selic</option>
            <option value="cdi">% do CDI</option>
            <option value="ipca">IPCA +</option>
            <option value="pre">Prefixado</option>
          </select>
        </Field>
        <Field label={f.indexer === "cdi" ? "Taxa (% do CDI)" : "Taxa (% a.a.)"}>
          <input className={inputCls} inputMode="decimal" value={f.rate} onChange={set("rate")} />
        </Field>
        <Field label={editing ? "Saldo atual (R$)" : "Valor (R$)"}>
          <input ref={amountRef} className={inputCls} inputMode="decimal" value={f.amount} onChange={set("amount")} />
        </Field>
        <Field label="Data da aplicação">
          <input type="date" className={inputCls} value={f.start_date} onChange={set("start_date")} />
        </Field>
        <Field label="Vencimento">
          <input type="date" className={inputCls} value={f.maturity} onChange={set("maturity")} />
        </Field>
      </div>
      <div className="mt-3 flex flex-wrap gap-5 text-sm">
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={f.daily_liquidity} onChange={set("daily_liquidity")} /> Liquidez diária
        </label>
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={f.fgc_covered} onChange={set("fgc_covered")} /> Coberto pelo FGC (ou Tesouro)
        </label>
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={f.is_emergency_reserve} onChange={set("is_emergency_reserve")} /> Faz parte da reserva
          de emergência
        </label>
      </div>
      <div className="mt-4 flex items-center gap-3">
        <Button onClick={save} disabled={!f.amount}>
          {editing ? "Salvar alterações" : "Salvar aplicação"}
        </Button>
        {editing && (
          <Button variant="ghost" onClick={onCancel}>
            Cancelar
          </Button>
        )}
      </div>
      {err && (
        <div className="mt-3">
          <ErrorBox error={err} />
        </div>
      )}
    </div>
  );
}

function Comparator() {
  const [f, setF] = useState({ kind: "cdb", indexer: "cdi", rate: "110", days: "730" });
  const [res, setRes] = useState<Compare | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setF((s) => ({ ...s, [k]: e.target.value }));
  async function run() {
    setErr(null);
    const rate = parseNumber(f.rate);
    const days = parseNumber(f.days);
    if (rate === null || days === null || days <= 0 || !Number.isInteger(days))
      return setErr("Informe a taxa e o prazo em dias inteiros.");
    try {
      setRes(await api.post<Compare>("/api/renda-fixa/comparar", { ...f, rate, days }));
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    }
  }
  return (
    <Card title="Comparador: quanto rende de verdade?" help="ir-regressivo">
      <div className="grid gap-3 sm:grid-cols-4">
        <Field label="Tipo">
          <select className={inputCls} value={f.kind} onChange={set("kind")}>
            {Object.entries(KIND_LABEL).map(([k, v]) => (
              <option key={k} value={k}>
                {v}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Indexador">
          <select className={inputCls} value={f.indexer} onChange={set("indexer")}>
            <option value="cdi">% do CDI</option>
            <option value="ipca">IPCA +</option>
            <option value="pre">Prefixado</option>
            <option value="selic">Selic</option>
          </select>
        </Field>
        <Field label={f.indexer === "cdi" ? "% do CDI" : "Taxa % a.a."}>
          <input className={inputCls} value={f.rate} onChange={set("rate")} />
        </Field>
        <Field label="Prazo (dias)">
          <input className={inputCls} value={f.days} onChange={set("days")} />
        </Field>
      </div>
      <Button className="mt-3" onClick={run}>
        Calcular
      </Button>
      {err && (
        <div className="mt-3">
          <ErrorBox error={err} />
        </div>
      )}
      {res && (
        <div className="mt-4 grid grid-cols-2 gap-4 border-t border-line pt-4">
          <Stat label="Rendimento bruto ao ano" value={pct(res.gross_annual, 2)} />
          <Stat
            label="Líquido de IR ao ano"
            value={pct(res.net_annual, 2)}
            hint={res.tax_exempt ? "isento de IR" : `IR de ${pct(res.ir_rate, 1)}`}
          />
          <Stat label={res.equivalent_label} value={pct(res.equivalent_rate, 2)} />
          <Stat
            label="Contra o CDI líquido"
            value={
              <span className={res.vs_cdi_net >= 0 ? "text-good" : "text-bad"}>
                {res.vs_cdi_net >= 0 ? "+" : ""}
                {pct(res.vs_cdi_net, 2)}
              </span>
            }
            hint="mesmo prazo"
          />
        </div>
      )}
    </Card>
  );
}

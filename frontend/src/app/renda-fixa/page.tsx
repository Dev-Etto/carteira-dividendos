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
import { brl, dateBr, decimalStr, num, parseNumber, pct, todayIso } from "@/lib/format";
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
    <div className="space-y-5">
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

      <Comparator />
      <Card title="Tesouro Direto hoje">
        <TreasuryList loading={tesouro.loading} data={tesouro.data} />
      </Card>
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
    <ul className="divide-y divide-line border-t border-line">
      {data.map((h) => (
        <li
          key={h.id}
          className={`flex flex-wrap items-center justify-between gap-3 py-3.5 text-sm ${h.id === editingId ? "bg-accent-soft" : ""}`}
        >
          <div>
            <div className="font-semibold text-ink">
              {h.name}{" "}
              {h.is_emergency_reserve && (
                <span className="ml-1 rounded-md bg-accent-soft px-1.5 py-0.5 text-xs font-semibold text-accent">reserva</span>
              )}
            </div>
            <div className="text-[13px] text-subtle">
              {KIND_LABEL[h.kind]} · {h.issuer} · {rateLabel(h.indexer, h.rate)} · desde {dateBr(h.start_date)}
              {h.maturity ? ` · vence ${dateBr(h.maturity)}` : ""}
              {h.daily_liquidity ? " · liquidez diária" : ""}
            </div>
            {h.is_emergency_reserve && !h.reserve_ok && (
              <div className="mt-1 text-xs text-warn">Atenção para a reserva: {h.reserve_reason}</div>
            )}
          </div>
          <div className="flex items-center gap-3">
            <span className="font-bold tabular-nums">{brl(h.amount)}</span>
            <button type="button" className="text-xs font-semibold text-accent hover:underline" onClick={() => onEdit(h)}>
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
      <p className="mb-3 text-[13px] text-subtle">Taxas de compra em {dateBr(data[0]?.date)} (Tesouro Transparente).</p>
      <ul className="grid gap-x-10 text-sm [grid-template-columns:repeat(auto-fit,minmax(320px,1fr))]">
        {data.map((b) => (
          <li key={`${b.name}-${b.maturity}`} className="flex justify-between gap-4 border-t border-line py-2.5">
            <span>
              {b.name} <span className="text-subtle">{b.maturity.slice(0, 4)}</span>
            </span>
            <span className="whitespace-nowrap font-semibold tabular-nums">{bondRate(b)}</span>
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
    <div ref={formRef} className="scroll-mt-6 rounded-xl border border-line bg-bg p-5">
      <div className="mb-1 text-[15px] font-bold text-ink">{editing ? `Editar ${editing.name}` : "Cadastrar aplicação"}</div>
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
      <div className="mt-4 flex flex-wrap gap-5 text-sm text-label [&_input]:h-[18px] [&_input]:w-[18px] [&_input]:accent-accent">
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

const KIND_HINT = "LCI e LCA são isentas de IR para pessoa física.";
const DAYS_PER_YEAR = 365;

/** "≈ 2 anos" para o prazo digitado; vazio enquanto não é um número de dias válido. */
function yearsHint(daysText: string): string {
  const days = parseNumber(daysText);
  if (days === null || days <= 0) return "dias corridos";
  return `≈ ${num(days / DAYS_PER_YEAR, 1)} ${days >= 2 * DAYS_PER_YEAR ? "anos" : "ano"}`;
}

/** Conclusão em linguagem simples, montada só a partir do resultado do cálculo. */
function conclusion(res: Compare): { title: string; text: string; tone: string } {
  const exempt = res.tax_exempt ? ", sem IR" : " depois do IR";
  const gap = `${pct(Math.abs(res.vs_cdi_net), 2)} ${res.vs_cdi_net >= 0 ? "acima" : "abaixo"} do CDI depois do IR, no mesmo prazo`;
  const text = `Rende ${pct(res.net_annual, 2)} ao ano${exempt}: ${gap}.`;
  if (res.vs_cdi_net >= 0) return { title: "Vale a pena.", text, tone: "bg-good-soft text-good" };
  return { title: "Não compensa.", text, tone: "bg-warn-soft text-warn" };
}

function ComparatorResult({ res }: { res: Compare | null }) {
  if (!res)
    return (
      <div className="flex min-w-0 flex-[1_1_380px] items-center justify-center rounded-[14px] border border-dashed border-line-strong p-6 text-center text-sm text-subtle">
        Preencha os passos 1 e 2 e clique em Calcular para ver o resultado aqui.
      </div>
    );
  const c = conclusion(res);
  return (
    <div aria-live="polite" className={`flex min-w-0 flex-[1_1_380px] flex-col gap-4 rounded-[14px] p-6 ${c.tone}`}>
      <span className="text-[13px] font-bold">Resultado</span>
      <p className="text-base text-ink">
        <strong className="font-bold">{c.title}</strong> {c.text}
      </p>
      <dl className="grid gap-x-5 gap-y-4 border-t border-current/20 pt-4 text-ink [grid-template-columns:repeat(auto-fit,minmax(160px,1fr))]">
        <ResultStat label="Rende por ano, antes do IR" value={pct(res.gross_annual, 2)} />
        <ResultStat
          label="Fica com você, depois do IR"
          value={pct(res.net_annual, 2)}
          hint={res.tax_exempt ? "isento de IR" : `IR de ${pct(res.ir_rate, 1)}`}
        />
        <ResultStat label={res.equivalent_label} value={pct(res.equivalent_rate, 2)} hint="ao ano" />
        <ResultStat
          label="Contra o CDI depois do IR"
          value={`${res.vs_cdi_net >= 0 ? "+" : ""}${pct(res.vs_cdi_net, 2)}`}
          valueClass={res.vs_cdi_net >= 0 ? "text-good" : "text-bad"}
          hint="mesmo prazo"
        />
      </dl>
    </div>
  );
}

function ResultStat({
  label,
  value,
  hint,
  valueClass = "",
}: {
  label: string;
  value: string;
  hint?: string;
  valueClass?: string;
}) {
  return (
    <div className="flex flex-col gap-0.5">
      <dt className="text-[13px] font-medium text-muted">{label}</dt>
      <dd className={`text-[22px] font-bold tabular-nums tracking-tight ${valueClass}`}>{value}</dd>
      {hint && <dd className="text-[13px] text-subtle">{hint}</dd>}
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
    <section className="rounded-2xl border border-line bg-surface p-7 shadow-card">
      <h2 className="flex items-center gap-1.5 text-lg font-bold text-ink">
        Quanto rende de verdade? <Help slug="ir-regressivo" />
      </h2>
      <p className="mt-1 text-sm text-muted">
        Te ofereceram um CDB, LCI ou título do Tesouro? Coloque a taxa aqui e veja quanto sobra depois do IR e se ele ganha do
        CDI.
      </p>
      <div className="mt-6 flex flex-wrap items-stretch gap-7">
        <div className="flex min-w-0 flex-[1_1_380px] flex-col gap-5">
          <fieldset className="flex flex-col gap-3">
            <legend className="mb-3 text-[13px] font-bold text-accent">1. O que te ofereceram</legend>
            <div className="grid gap-3 [grid-template-columns:repeat(auto-fit,minmax(150px,1fr))]">
              <Field label="Tipo">
                <select className={inputCls} value={f.kind} onChange={set("kind")}>
                  {Object.entries(KIND_LABEL).map(([k, v]) => (
                    <option key={k} value={k}>
                      {v}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Como rende">
                <select className={inputCls} value={f.indexer} onChange={set("indexer")}>
                  <option value="cdi">% do CDI</option>
                  <option value="ipca">IPCA +</option>
                  <option value="pre">Prefixado</option>
                  <option value="selic">Selic</option>
                </select>
              </Field>
              <Field label={f.indexer === "cdi" ? "Taxa (% do CDI)" : "Taxa (% a.a.)"}>
                <input className={inputCls} inputMode="decimal" value={f.rate} onChange={set("rate")} />
              </Field>
            </div>
            <span className="text-[13px] text-subtle">{KIND_HINT}</span>
          </fieldset>
          <fieldset>
            <legend className="mb-3 text-[13px] font-bold text-accent">2. Por quanto tempo</legend>
            <div className="max-w-[220px]">
              <Field label="Prazo (dias)" hint={yearsHint(f.days)}>
                <input className={inputCls} inputMode="numeric" value={f.days} onChange={set("days")} />
              </Field>
            </div>
          </fieldset>
          <Button className="self-start" onClick={run}>
            3. Calcular
          </Button>
          {err && <ErrorBox error={err} />}
        </div>
        <ComparatorResult res={res} />
      </div>
    </section>
  );
}

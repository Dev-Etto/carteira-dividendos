"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";

import { AllocationBars } from "@/components/AllocationBars";
import { DateInput, IntegerInput, MoneyInput, TickerInput } from "@/components/inputs";
import {
  Button,
  Card,
  ConfirmAction,
  Empty,
  ErrorBox,
  Field,
  Help,
  inputCls,
  Loading,
  PageHeader,
  Stat,
  VerdictBadge,
} from "@/components/ui";
import { Investidor10Link } from "@/components/Investidor10Link";
import { api, type AssetRow, type Portfolio, type Transaction } from "@/lib/api/client";
import { brl, dateBr, groupLabel, num, pct, todayIso } from "@/lib/format";
import { decimalInput, scrollAndFocus } from "@/lib/inputs";
import { useApi } from "@/lib/useApi";
import { TickerOptions, useTickers } from "@/lib/useTickers";
import { canSubmit, checkDate, checkInteger, checkMoney, checkTicker } from "@/lib/validation";

const TH = "whitespace-nowrap px-3.5 py-3 font-semibold";
const TD = "whitespace-nowrap px-3.5 py-3";

/** Alertas da carteira em caixa de atenção, com ícone para não depender só da cor. */
function AlertsBox({ alerts }: { alerts: string[] }) {
  return (
    <section className="rounded-2xl border border-warn/30 bg-warn-soft px-6 py-4">
      <h2 className="mb-2 text-base font-bold text-warn">Alertas</h2>
      <ul className="space-y-1.5 text-sm text-ink">
        {alerts.map((a) => (
          <li key={a} className="flex items-start gap-2.5">
            <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true" className="mt-0.5 shrink-0 text-warn">
              <path d="M8 2 L14.5 13.5 H1.5 Z" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
              <path d="M8 6.5 V9.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
              <circle cx="8" cy="11.5" r="0.9" fill="currentColor" />
            </svg>
            {a}
          </li>
        ))}
      </ul>
    </section>
  );
}

export default function CarteiraPage() {
  return (
    <Suspense fallback={<Loading />}>
      <Carteira />
    </Suspense>
  );
}

/**
 * Carteira. `?novo=TICKER` (vindo da ficha do ativo) pré-preenche o formulário de operação, rola até ele
 * e foca a quantidade.
 */
function Carteira() {
  const pf = useApi<Portfolio>("/api/carteira");
  const txs = useApi<Transaction[]>("/api/transacoes");
  const tickers = useTickers();
  const prefill = useSearchParams().get("novo");
  const [editing, setEditing] = useState<Transaction | null>(null);

  const reloadAll = () => {
    void pf.reload();
    void txs.reload();
  };

  if (pf.loading && !pf.data) return <Loading />;
  if (pf.error) return <ErrorBox error={pf.error} onRetry={pf.reload} />;
  const d = pf.data!;

  return (
    <div className="space-y-5">
      <PageHeader
        title="Minha carteira"
        subtitle="Suas posições, quanto rendem e como está a divisão em relação ao seu perfil."
      />

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <Stat label="Investido (sem reserva)" value={brl(d.total_invested)} />
        </Card>
        <Card>
          <Stat
            label="Reserva de emergência"
            help="reserva-de-emergencia"
            value={brl(d.reserve_value)}
            hint={`meta ${brl(d.reserve_target)}`}
          />
        </Card>
        <Card>
          <Stat
            label="Proventos (12 meses)"
            help="dividendos"
            value={brl(d.income_12m)}
            hint={`${brl(d.income_12m / 12)} por mês`}
          />
        </Card>
        <Card>
          <Stat label="Setores em ações" value={Object.keys(d.sectors).length} hint="ideal: 5 ou mais" help="diversificacao" />
        </Card>
      </div>

      {d.alerts.length > 0 && <AlertsBox alerts={d.alerts} />}

      <Card title="Posições" help="preco-medio">
        {d.positions.length === 0 ? (
          <Empty title="Nenhuma posição ainda">
            Registre sua primeira compra abaixo, ou use o{" "}
            <Link className="text-accent underline" href="/aporte">
              assistente de aporte
            </Link>
            .
          </Empty>
        ) : (
          <div className="-mx-6 -mb-6 overflow-x-auto">
            <table className="w-full min-w-[900px] text-sm tabular-nums">
              <thead className="border-y border-line bg-bg text-left text-xs text-muted">
                <tr>
                  <th className={`${TH} pl-6`}>Ativo</th>
                  <th className={`${TH} text-right`}>Qtd.</th>
                  <th className={`${TH} text-right`}>Preço médio</th>
                  <th className={`${TH} text-right`}>Preço</th>
                  <th className={`${TH} text-right`}>Valor</th>
                  <th className={`${TH} text-right`}>Resultado</th>
                  <th className={`${TH} text-right`}>Peso</th>
                  <th className={`${TH} text-right`}>
                    <span className="inline-flex items-center gap-1">
                      Yield on cost <Help slug="yield-on-cost" />
                    </span>
                  </th>
                  <th className={`${TH} pr-6`}>Veredito hoje</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {d.positions.map((p) => (
                  <tr key={p.ticker}>
                    <td className={`${TD} pl-6`}>
                      <Link href={`/ativo/${p.ticker}`} className="font-bold text-ink hover:text-accent">
                        {p.ticker}
                      </Link>
                      <div className="text-xs text-subtle">{groupLabel(p.asset_class, p.sector)}</div>
                      <Investidor10Link ticker={p.ticker} assetClass={p.asset_class} compact />
                    </td>
                    <td className={`${TD} text-right`}>{num(p.quantity, 0)}</td>
                    <td className={`${TD} text-right`}>{brl(p.avg_price)}</td>
                    <td className={`${TD} text-right`}>{brl(p.price)}</td>
                    <td className={`${TD} text-right font-semibold`}>{brl(p.value)}</td>
                    <td className={`${TD} text-right ${p.profit >= 0 ? "text-good" : "text-bad"}`}>
                      {p.profit > 0 ? "+" : ""}
                      {brl(p.profit)} <span className="text-xs">({pct(p.profit_pct)})</span>
                    </td>
                    <td className={`${TD} text-right`}>{num(p.weight_pct, 1)}%</td>
                    <td className={`${TD} text-right`}>{pct(p.yield_on_cost)}</td>
                    <td className={`${TD} pr-6`}>
                      <VerdictBadge verdict={p.verdict} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <div className="grid items-start gap-5 lg:grid-cols-2">
        <Card title="Divisão atual × alvo" help="diversificacao">
          <AllocationBars classes={d.classes} />
        </Card>
        <Card
          title="Renda fixa e reserva"
          actions={
            <Link href="/renda-fixa" className="text-sm font-semibold text-accent">
              gerenciar →
            </Link>
          }
        >
          {d.fixed_income.length === 0 ? (
            <p className="text-sm text-muted">Nenhuma aplicação cadastrada.</p>
          ) : (
            <ul className="divide-y divide-line border-t border-line text-sm">
              {d.fixed_income.map((h) => (
                <li key={h.id} className="flex justify-between gap-4 py-3">
                  <span>
                    {h.name}{" "}
                    {h.is_emergency_reserve && (
                      <span className="ml-1 rounded-md bg-accent-soft px-1.5 py-0.5 text-xs font-semibold text-accent">
                        reserva
                      </span>
                    )}
                  </span>
                  <span className="font-semibold tabular-nums">{brl(h.amount)}</span>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <TxForm
        key={editing ? `editar-${editing.id}` : `novo-${prefill ?? ""}`}
        editing={editing}
        defaultTicker={prefill ?? ""}
        focusOnMount={Boolean(editing || prefill)}
        tickers={tickers}
        onSaved={() => {
          setEditing(null);
          reloadAll();
        }}
        onCancel={() => setEditing(null)}
      />

      <Card title="Histórico de operações">
        <TxHistory
          loading={txs.loading}
          data={txs.data}
          editingId={editing?.id ?? null}
          onEdit={setEditing}
          onChanged={reloadAll}
        />
      </Card>
    </div>
  );
}

function TxHistory({
  loading,
  data,
  editingId,
  onEdit,
  onChanged,
}: {
  loading: boolean;
  data: Transaction[] | null;
  editingId: number | null;
  onEdit: (t: Transaction | null) => void;
  onChanged: () => void;
}) {
  const [err, setErr] = useState<string | null>(null);
  if (loading && !data) return <Loading />;
  if (!data?.length) return <p className="text-sm text-muted">Nenhuma operação registrada.</p>;
  async function remove(t: Transaction) {
    setErr(null);
    try {
      await api.del(`/api/transacoes/${t.id}`);
      if (t.id === editingId) onEdit(null);
      onChanged();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    }
  }
  return (
    <>
      {err && (
        <div className="mb-3">
          <ErrorBox error={err} />
        </div>
      )}
      <div className="-mx-6 -mb-6 overflow-x-auto">
        <table className="w-full min-w-[640px] text-sm tabular-nums">
          <thead className="border-y border-line bg-bg text-left text-xs text-muted">
            <tr>
              <th className={`${TH} pl-6`}>Data</th>
              <th className={TH}>Ativo</th>
              <th className={TH}>Tipo</th>
              <th className={`${TH} text-right`}>Qtd.</th>
              <th className={`${TH} text-right`}>Preço</th>
              <th className={`${TH} text-right`}>Taxas</th>
              <th className={`${TH} pr-6`}>
                <span className="sr-only">Ações</span>
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {data.map((t) => (
              <tr key={t.id} className={t.id === editingId ? "bg-accent-soft" : ""}>
                <td className={`${TD} pl-6`}>{dateBr(t.date)}</td>
                <td className={`${TD} font-semibold`}>{t.ticker}</td>
                <td className={`${TD} ${t.kind === "compra" ? "text-good" : "text-bad"}`}>{t.kind}</td>
                <td className={`${TD} text-right`}>{num(Number(t.quantity), 0)}</td>
                <td className={`${TD} text-right`}>{brl(t.price)}</td>
                <td className={`${TD} text-right`}>{brl(t.fees)}</td>
                <td className={`${TD} pr-6 text-right`}>
                  <span className="inline-flex items-center gap-3">
                    <button type="button" className="text-xs font-semibold text-accent hover:underline" onClick={() => onEdit(t)}>
                      editar
                    </button>
                    <ConfirmAction label="excluir" onConfirm={() => void remove(t)} />
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

type TxFields = { ticker: string; date: string; kind: string; quantity: string; price: string; fees: string };

function initialTx(editing: Transaction | null, defaultTicker: string): TxFields {
  if (!editing) return { ticker: defaultTicker, date: todayIso(), kind: "compra", quantity: "", price: "", fees: "0" };
  return {
    ticker: editing.ticker,
    date: editing.date,
    kind: editing.kind,
    quantity: decimalInput(editing.quantity),
    price: decimalInput(editing.price),
    fees: decimalInput(editing.fees),
  };
}

function TxForm({
  editing,
  defaultTicker,
  focusOnMount,
  tickers,
  onSaved,
  onCancel,
}: {
  editing: Transaction | null;
  defaultTicker: string;
  focusOnMount: boolean;
  tickers: AssetRow[];
  onSaved: () => void;
  onCancel: () => void;
}) {
  const [f, setF] = useState<TxFields>(() => initialTx(editing, defaultTicker));
  const [err, setErr] = useState<string | null>(null);
  const [ok, setOk] = useState(false);
  const cardRef = useRef<HTMLDivElement>(null);
  const quantityRef = useRef<HTMLInputElement>(null);
  useEffect(() => {
    if (focusOnMount) scrollAndFocus(cardRef.current, quantityRef.current);
  }, [focusOnMount]);
  const set = (k: keyof TxFields) => (text: string) => setF((s) => ({ ...s, [k]: text }));
  const checks = {
    ticker: checkTicker(f.ticker),
    date: checkDate(f.date, { max: todayIso() }),
    quantity: checkInteger(f.quantity, { positive: true }),
    price: checkMoney(f.price, { positive: true }),
    fees: checkMoney(f.fees),
  };
  const ready = canSubmit([checks.ticker, checks.date, checks.quantity, checks.price], [checks.fees]);
  async function save() {
    setErr(null);
    setOk(false);
    const body = {
      ...f,
      ticker: checks.ticker.value,
      quantity: String(checks.quantity.value),
      price: String(checks.price.value),
      fees: String(checks.fees.value ?? 0),
    };
    try {
      await (editing ? api.put(`/api/transacoes/${editing.id}`, body) : api.post("/api/transacoes", body));
      setF((s) => ({ ...s, quantity: "", price: "", fees: "0" }));
      setOk(!editing);
      onSaved();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    }
  }
  return (
    <div ref={cardRef} className="scroll-mt-6">
      <Card title={editing ? `Editar operação de ${editing.ticker} em ${dateBr(editing.date)}` : "Registrar operação"}>
        <div className="grid gap-3 sm:grid-cols-6">
          <Field label="Ticker" error={checks.ticker.error}>
            <TickerInput list="tickers-carteira" value={f.ticker} onValueChange={set("ticker")} placeholder="TAEE11" />
            <TickerOptions id="tickers-carteira" assets={tickers} />
          </Field>
          <Field label="Data" error={checks.date.error}>
            <DateInput value={f.date} max={todayIso()} onValueChange={set("date")} />
          </Field>
          <Field label="Tipo">
            <select className={inputCls} value={f.kind} onChange={(e) => set("kind")(e.target.value)}>
              <option value="compra">Compra</option>
              <option value="venda">Venda</option>
            </select>
          </Field>
          <Field label="Quantidade" error={checks.quantity.error}>
            <IntegerInput ref={quantityRef} value={f.quantity} onValueChange={set("quantity")} />
          </Field>
          <Field label="Preço (R$)" error={checks.price.error}>
            <MoneyInput value={f.price} onValueChange={set("price")} />
          </Field>
          <Field label="Taxas (R$)" error={checks.fees.error}>
            <MoneyInput value={f.fees} onValueChange={set("fees")} />
          </Field>
        </div>
        <div className="mt-4 flex items-center gap-3">
          <Button onClick={save} disabled={!ready}>
            {editing ? "Salvar alterações" : "Salvar"}
          </Button>
          {editing && (
            <Button variant="ghost" onClick={onCancel}>
              Cancelar
            </Button>
          )}
          {ok && <span className="text-sm text-good">Operação salva.</span>}
        </div>
        {err && (
          <div className="mt-3">
            <ErrorBox error={err} />
          </div>
        )}
      </Card>
    </div>
  );
}

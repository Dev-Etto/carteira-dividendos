"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";

import { AllocationBars } from "@/components/AllocationBars";
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
import { api, type AssetRow, type Portfolio, type Transaction } from "@/lib/api/client";
import { brl, dateBr, decimalStr, num, pct, SECTOR_LABEL, todayIso } from "@/lib/format";
import { decimalInput, scrollAndFocus } from "@/lib/inputs";
import { useApi } from "@/lib/useApi";
import { TickerOptions, useTickers } from "@/lib/useTickers";

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
    <div className="space-y-6">
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

      {d.alerts.length > 0 && (
        <Card title="Alertas">
          <ul className="space-y-2 text-sm">
            {d.alerts.map((a) => (
              <li key={a} className="flex gap-2">
                <span className="text-warn">●</span>
                {a}
              </li>
            ))}
          </ul>
        </Card>
      )}

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
          <div className="overflow-x-auto">
            <table className="w-full min-w-[820px] text-sm">
              <thead className="border-b border-line text-left text-xs text-muted">
                <tr>
                  <th className="py-2 pr-3 font-medium">Ativo</th>
                  <th className="py-2 pr-3 text-right font-medium">Qtd.</th>
                  <th className="py-2 pr-3 text-right font-medium">Preço médio</th>
                  <th className="py-2 pr-3 text-right font-medium">Preço</th>
                  <th className="py-2 pr-3 text-right font-medium">Valor</th>
                  <th className="py-2 pr-3 text-right font-medium">Resultado</th>
                  <th className="py-2 pr-3 text-right font-medium">Peso</th>
                  <th className="py-2 pr-3 text-right font-medium">
                    <span className="inline-flex items-center gap-1">
                      Yield on cost <Help slug="yield-on-cost" />
                    </span>
                  </th>
                  <th className="py-2 font-medium">Veredito hoje</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {d.positions.map((p) => (
                  <tr key={p.ticker}>
                    <td className="py-2.5 pr-3">
                      <Link href={`/ativo/${p.ticker}`} className="font-semibold text-ink hover:text-accent">
                        {p.ticker}
                      </Link>
                      <div className="text-xs text-muted">{SECTOR_LABEL[p.sector] ?? p.sector}</div>
                    </td>
                    <td className="py-2.5 pr-3 text-right tabular-nums">{num(p.quantity, 0)}</td>
                    <td className="py-2.5 pr-3 text-right tabular-nums">{brl(p.avg_price)}</td>
                    <td className="py-2.5 pr-3 text-right tabular-nums">{brl(p.price)}</td>
                    <td className="py-2.5 pr-3 text-right tabular-nums">{brl(p.value)}</td>
                    <td className={`py-2.5 pr-3 text-right tabular-nums ${p.profit >= 0 ? "text-good" : "text-bad"}`}>
                      {brl(p.profit)} <span className="text-xs">({pct(p.profit_pct)})</span>
                    </td>
                    <td className="py-2.5 pr-3 text-right tabular-nums">{num(p.weight_pct, 1)}%</td>
                    <td className="py-2.5 pr-3 text-right tabular-nums">{pct(p.yield_on_cost)}</td>
                    <td className="py-2.5">
                      <VerdictBadge verdict={p.verdict} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Divisão atual × alvo" help="diversificacao">
          <AllocationBars classes={d.classes} />
        </Card>
        <Card
          title="Renda fixa e reserva"
          actions={
            <Link href="/renda-fixa" className="text-xs font-semibold text-accent">
              gerenciar →
            </Link>
          }
        >
          {d.fixed_income.length === 0 ? (
            <p className="text-sm text-muted">Nenhuma aplicação cadastrada.</p>
          ) : (
            <ul className="divide-y divide-line text-sm">
              {d.fixed_income.map((h) => (
                <li key={h.id} className="flex justify-between py-2">
                  <span>
                    {h.name}{" "}
                    {h.is_emergency_reserve && (
                      <span className="ml-1 rounded bg-accent-soft px-1.5 py-0.5 text-[10px] font-semibold text-accent">
                        reserva
                      </span>
                    )}
                  </span>
                  <span className="tabular-nums">{brl(h.amount)}</span>
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
    <div className="overflow-x-auto">
      {err && (
        <div className="mb-3">
          <ErrorBox error={err} />
        </div>
      )}
      <table className="w-full min-w-[640px] text-sm">
        <thead className="border-b border-line text-left text-xs text-muted">
          <tr>
            <th className="py-2 font-medium">Data</th>
            <th className="py-2 font-medium">Ativo</th>
            <th className="py-2 font-medium">Tipo</th>
            <th className="py-2 text-right font-medium">Qtd.</th>
            <th className="py-2 text-right font-medium">Preço</th>
            <th className="py-2 text-right font-medium">Taxas</th>
            <th />
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {data.map((t) => (
            <tr key={t.id} className={t.id === editingId ? "bg-accent-soft" : ""}>
              <td className="py-2">{dateBr(t.date)}</td>
              <td className="py-2 font-medium">{t.ticker}</td>
              <td className={`py-2 ${t.kind === "compra" ? "text-good" : "text-bad"}`}>{t.kind}</td>
              <td className="py-2 text-right tabular-nums">{num(Number(t.quantity), 0)}</td>
              <td className="py-2 text-right tabular-nums">{brl(t.price)}</td>
              <td className="py-2 text-right tabular-nums">{brl(t.fees)}</td>
              <td className="py-2 text-right">
                <span className="inline-flex items-center gap-3">
                  <button type="button" className="text-xs text-accent hover:underline" onClick={() => onEdit(t)}>
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
  const set = (k: keyof TxFields) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setF((s) => ({ ...s, [k]: e.target.value }));
  async function save() {
    setErr(null);
    setOk(false);
    const nums = { quantity: decimalStr(f.quantity), price: decimalStr(f.price), fees: decimalStr(f.fees || "0") };
    if (Object.values(nums).some((v) => v === null))
      return setErr("Quantidade, preço e taxas precisam ser números (ex.: 34,50).");
    const body = { ...f, ...nums, ticker: f.ticker.trim().toUpperCase() };
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
          <Field label="Ticker">
            <input
              className={inputCls}
              list="tickers-carteira"
              value={f.ticker}
              onChange={(e) => setF((s) => ({ ...s, ticker: e.target.value.toUpperCase() }))}
              placeholder="TAEE11"
            />
            <TickerOptions id="tickers-carteira" assets={tickers} />
          </Field>
          <Field label="Data">
            <input type="date" className={inputCls} value={f.date} max={todayIso()} onChange={set("date")} />
          </Field>
          <Field label="Tipo">
            <select className={inputCls} value={f.kind} onChange={set("kind")}>
              <option value="compra">Compra</option>
              <option value="venda">Venda</option>
            </select>
          </Field>
          <Field label="Quantidade">
            <input ref={quantityRef} className={inputCls} inputMode="numeric" value={f.quantity} onChange={set("quantity")} />
          </Field>
          <Field label="Preço (R$)">
            <input className={inputCls} inputMode="decimal" value={f.price} onChange={set("price")} />
          </Field>
          <Field label="Taxas (R$)">
            <input className={inputCls} inputMode="decimal" value={f.fees} onChange={set("fees")} />
          </Field>
        </div>
        <div className="mt-4 flex items-center gap-3">
          <Button onClick={save} disabled={!f.ticker || !f.quantity || !f.price}>
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

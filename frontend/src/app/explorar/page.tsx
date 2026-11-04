"use client";

import Link from "next/link";
import { useCallback, useMemo, useState } from "react";

import {
  Button,
  Card,
  Empty,
  ErrorBox,
  Field,
  Help,
  inputCls,
  Loading,
  PageHeader,
  ScorePill,
  signClass,
  VerdictBadge,
} from "@/components/ui";
import { api, type AssetRow } from "@/lib/api/client";
import { brl, pct, SECTOR_LABEL } from "@/lib/format";
import { useApi } from "@/lib/useApi";
import { useSyncWatch } from "@/lib/useSyncWatch";

const VERDICTS = ["", "comprar", "aguardar", "neutro", "evitar"];

export default function Explorar() {
  const { data, error, loading, reload } = useApi<AssetRow[]>("/api/ativos?classe=acao");
  const [sector, setSector] = useState("");
  const [verdict, setVerdict] = useState("");
  const [search, setSearch] = useState("");
  const [adding, setAdding] = useState(false);
  const collecting = useSyncWatch(useCallback(() => void reload(), [reload]));

  const rows = useMemo(
    () =>
      (data ?? []).filter(
        (r) =>
          (!sector || r.sector === sector) &&
          (!verdict || r.verdict === verdict) &&
          (!search || `${r.ticker} ${r.name}`.toLowerCase().includes(search.toLowerCase())),
      ),
    [data, sector, verdict, search],
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title="Explorar ações"
        subtitle="Cada ação é avaliada pelas regras do método Barsi. Clique para ver o checklist completo e o porquê de cada nota."
      >
        <Button variant="ghost" onClick={() => setAdding((a) => !a)}>
          {adding ? "Fechar" : "+ Adicionar ação"}
        </Button>
      </PageHeader>

      <div className="flex gap-2 rounded-lg border border-line bg-surface p-1 text-sm">
        <span className="rounded-md bg-accent-soft px-3 py-1.5 font-medium text-accent">Ações</span>
        <span className="px-3 py-1.5 text-muted" title="Chega na Fase 2">
          FIIs (em breve)
        </span>
        <span className="px-3 py-1.5 text-muted" title="Chega na Fase 2">
          ETFs (em breve)
        </span>
        <Link href="/renda-fixa" className="px-3 py-1.5 text-muted hover:text-ink">
          Renda fixa
        </Link>
      </div>

      {adding && (
        <AddAsset
          onDone={(ticker) => {
            setAdding(false);
            collecting.watch(ticker);
          }}
        />
      )}

      {collecting.watching && (
        <div className="rounded-lg border border-line bg-accent-soft px-4 py-3 text-sm text-accent">
          Coletando dados de {collecting.watching}… A lista atualiza sozinha quando terminar.
        </div>
      )}

      <div className="grid gap-3 sm:grid-cols-3">
        <input
          className={inputCls}
          placeholder="Buscar por ticker ou nome"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select className={inputCls} value={sector} onChange={(e) => setSector(e.target.value)}>
          <option value="">Todos os setores</option>
          {Object.entries(SECTOR_LABEL).map(([k, v]) => (
            <option key={k} value={k}>
              {v}
            </option>
          ))}
        </select>
        <select className={inputCls} value={verdict} onChange={(e) => setVerdict(e.target.value)}>
          {VERDICTS.map((v) => (
            <option key={v} value={v}>
              {v ? v.charAt(0).toUpperCase() + v.slice(1) : "Todos os vereditos"}
            </option>
          ))}
        </select>
      </div>

      <AssetsResult loading={loading} data={data} rows={rows} error={error} onRetry={reload} />
    </div>
  );
}

function AssetsResult({
  loading,
  data,
  rows,
  error,
  onRetry,
}: {
  loading: boolean;
  data: AssetRow[] | null;
  rows: AssetRow[];
  error: string | null;
  onRetry: () => void;
}) {
  if (loading && !data) return <Loading />;
  if (error) return <ErrorBox error={error} onRetry={onRetry} />;
  if (rows.length === 0)
    return <Empty title="Nenhuma ação encontrada">Mude os filtros, ou rode a atualização de dados em Configurações.</Empty>;
  return <AssetsTable rows={rows} />;
}

function AssetsTable({ rows }: { rows: AssetRow[] }) {
  return (
    <div className="overflow-x-auto rounded-xl border border-line bg-surface">
      <table className="w-full min-w-[760px] text-sm">
        <thead className="border-b border-line text-left text-xs text-muted">
          <tr>
            <th className="px-4 py-3 font-medium">Ação</th>
            <th className="px-4 py-3 font-medium">Setor</th>
            <th className="px-4 py-3 font-medium">
              <span className="inline-flex items-center gap-1">
                Nota <Help slug="veredito" />
              </span>
            </th>
            <th className="px-4 py-3 font-medium">Veredito</th>
            <th className="px-4 py-3 text-right font-medium">Preço</th>
            <th className="px-4 py-3 text-right font-medium">
              <span className="inline-flex items-center gap-1">
                Preço-teto <Help slug="preco-teto" />
              </span>
            </th>
            <th className="px-4 py-3 text-right font-medium">Margem</th>
            <th className="px-4 py-3 text-right font-medium">
              <span className="inline-flex items-center gap-1">
                DY 12m <Help slug="dividend-yield" />
              </span>
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {rows.map((r) => (
            <tr key={r.ticker} className="hover:bg-neutral-soft">
              <td className="px-4 py-3">
                <Link href={`/ativo/${r.ticker}`} className="font-semibold text-ink hover:text-accent">
                  {r.ticker}
                </Link>
                <div className="text-xs text-muted">{r.name}</div>
              </td>
              <td className="px-4 py-3 text-muted">{SECTOR_LABEL[r.sector] ?? r.sector}</td>
              <td className="px-4 py-3">
                <ScorePill score={r.score} verdict={r.verdict} />
              </td>
              <td className="px-4 py-3">
                <VerdictBadge verdict={r.verdict} />
              </td>
              <td className="px-4 py-3 text-right tabular-nums">{brl(r.price)}</td>
              <td className="px-4 py-3 text-right tabular-nums">{brl(r.ceiling_price)}</td>
              <td className={`px-4 py-3 text-right tabular-nums ${signClass(r.margin_pct)}`}>{pct(r.margin_pct)}</td>
              <td className="px-4 py-3 text-right tabular-nums">{pct(r.dividend_yield)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function AddAsset({ onDone }: { onDone: (ticker: string) => void }) {
  const [ticker, setTicker] = useState("");
  const [name, setName] = useState("");
  const [sector, setSector] = useState("perene");
  const [err, setErr] = useState<string | null>(null);
  async function save() {
    setErr(null);
    try {
      await api.post("/api/ativos", { ticker, name: name || ticker, sector });
      onDone(ticker);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    }
  }
  return (
    <Card title="Adicionar ação ao universo">
      <div className="grid gap-3 sm:grid-cols-4">
        <Field label="Ticker">
          <input
            className={inputCls}
            value={ticker}
            onChange={(e) => setTicker(e.target.value.toUpperCase())}
            placeholder="CSMG3"
          />
        </Field>
        <Field label="Nome">
          <input className={inputCls} value={name} onChange={(e) => setName(e.target.value)} placeholder="Copasa" />
        </Field>
        <Field label="Setor">
          <select className={inputCls} value={sector} onChange={(e) => setSector(e.target.value)}>
            {Object.entries(SECTOR_LABEL).map(([k, v]) => (
              <option key={k} value={k}>
                {v}
              </option>
            ))}
          </select>
        </Field>
        <div className="flex items-end">
          <Button onClick={save} disabled={ticker.length < 4}>
            Adicionar
          </Button>
        </div>
      </div>
      <p className="mt-3 text-xs text-muted">
        Ao adicionar, os dados dela são coletados e avaliados na hora; leva alguns segundos.
      </p>
      {err && (
        <div className="mt-3">
          <ErrorBox error={err} />
        </div>
      )}
    </Card>
  );
}

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
import { Investidor10Link } from "@/components/Investidor10Link";
import { api, type AssetRow } from "@/lib/api/client";
import { brl, FII_KIND_LABEL, groupLabel, pct, SECTOR_LABEL } from "@/lib/format";
import { useApi } from "@/lib/useApi";
import { useSyncWatch } from "@/lib/useSyncWatch";

const VERDICTS = ["", "comprar", "aguardar", "neutro", "evitar"];

type AssetClass = "acao" | "fii";

type ClassView = {
  tab: string;
  title: string;
  subtitle: string;
  noun: string;
  groupHeader: string;
  groups: Record<string, string>;
  allGroups: string;
  ceilingHeader: string;
  ceilingHelp: string;
  empty: string;
  add: string;
};

const VIEWS: Record<AssetClass, ClassView> = {
  acao: {
    tab: "Ações",
    title: "Explorar ações",
    subtitle: "Cada ação é avaliada pelas regras do método Barsi. Clique para ver o checklist completo e o porquê de cada nota.",
    noun: "Ação",
    groupHeader: "Setor",
    groups: SECTOR_LABEL,
    allGroups: "Todos os setores",
    ceilingHeader: "Preço-teto",
    ceilingHelp: "preco-teto",
    empty: "Nenhuma ação encontrada",
    add: "+ Adicionar ação",
  },
  fii: {
    tab: "FIIs",
    title: "Explorar FIIs",
    subtitle:
      "Cada fundo passa por um filtro de porte, estabilidade dos rendimentos, rendimento contra a renda fixa e P/VP, com faixas diferentes para papel e tijolo.",
    noun: "FII",
    groupHeader: "Tipo",
    groups: FII_KIND_LABEL,
    allGroups: "Todos os tipos",
    ceilingHeader: "Preço máx. (P/VP)",
    ceilingHelp: "p-vp",
    empty: "Nenhum FII encontrado",
    add: "+ Adicionar FII",
  },
};

const TAB_CLS = "rounded-md px-3 py-1.5";
const ACTIVE_TAB_CLS = `${TAB_CLS} bg-accent-soft font-medium text-accent`;
const IDLE_TAB_CLS = `${TAB_CLS} text-muted hover:text-ink`;

export default function Explorar() {
  const [assetClass, setAssetClass] = useState<AssetClass>("acao");
  const view = VIEWS[assetClass];
  const { data, error, loading, reload } = useApi<AssetRow[]>(`/api/ativos?classe=${assetClass}`);
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
      <PageHeader title={view.title} subtitle={view.subtitle}>
        <Button variant="ghost" onClick={() => setAdding((a) => !a)}>
          {adding ? "Fechar" : view.add}
        </Button>
      </PageHeader>

      <div className="flex gap-2 rounded-lg border border-line bg-surface p-1 text-sm">
        {(Object.keys(VIEWS) as AssetClass[]).map((cls) => (
          <button
            key={cls}
            type="button"
            className={cls === assetClass ? ACTIVE_TAB_CLS : IDLE_TAB_CLS}
            onClick={() => {
              setAssetClass(cls);
              setSector("");
              setAdding(false);
            }}
          >
            {VIEWS[cls].tab}
          </button>
        ))}
        <span className="px-3 py-1.5 text-muted" title="Chega no próximo passo do roteiro">
          ETFs (em breve)
        </span>
        <Link href="/renda-fixa" className="px-3 py-1.5 text-muted hover:text-ink">
          Renda fixa
        </Link>
      </div>

      {adding && (
        <AddAsset
          assetClass={assetClass}
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
          <option value="">{view.allGroups}</option>
          {Object.entries(view.groups).map(([k, v]) => (
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

      <AssetsResult view={view} loading={loading} data={data} rows={rows} error={error} onRetry={reload} />
    </div>
  );
}

function AssetsResult({
  view,
  loading,
  data,
  rows,
  error,
  onRetry,
}: {
  view: ClassView;
  loading: boolean;
  data: AssetRow[] | null;
  rows: AssetRow[];
  error: string | null;
  onRetry: () => void;
}) {
  if (loading && !data) return <Loading />;
  if (error) return <ErrorBox error={error} onRetry={onRetry} />;
  if (rows.length === 0)
    return <Empty title={view.empty}>Mude os filtros, ou rode a atualização de dados em Configurações.</Empty>;
  return <AssetsTable view={view} rows={rows} />;
}

function AssetsTable({ view, rows }: { view: ClassView; rows: AssetRow[] }) {
  return (
    <div className="overflow-x-auto rounded-xl border border-line bg-surface">
      <table className="w-full min-w-[760px] text-sm">
        <thead className="border-b border-line text-left text-xs text-muted">
          <tr>
            <th className="px-4 py-3 font-medium">{view.noun}</th>
            <th className="px-4 py-3 font-medium">{view.groupHeader}</th>
            <th className="px-4 py-3 font-medium">
              <span className="inline-flex items-center gap-1">
                Nota <Help slug="veredito" />
              </span>
            </th>
            <th className="px-4 py-3 font-medium">Veredito</th>
            <th className="px-4 py-3 text-right font-medium">Preço</th>
            <th className="px-4 py-3 text-right font-medium">
              <span className="inline-flex items-center gap-1">
                {view.ceilingHeader} <Help slug={view.ceilingHelp} />
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
                <Investidor10Link ticker={r.ticker} assetClass={r.asset_class} compact />
              </td>
              <td className="px-4 py-3 text-muted">{groupLabel(r.asset_class, r.sector)}</td>
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

const ADD_FORM: Record<AssetClass, { title: string; tickerHint: string; nameHint: string; hint: string }> = {
  acao: {
    title: "Adicionar ação ao universo",
    tickerHint: "CSMG3",
    nameHint: "Copasa",
    hint: "Ao adicionar, os balanços e as cotações dela são coletados e avaliados na hora; leva alguns segundos.",
  },
  fii: {
    title: "Adicionar FII ao universo",
    tickerHint: "RBRP11",
    nameHint: "RBR Properties",
    hint: "Ao adicionar, os informes da CVM e as cotações dele são coletados e avaliados na hora. O tipo (papel ou tijolo) vem da carteira do fundo.",
  },
};

function AddAsset({ assetClass, onDone }: { assetClass: AssetClass; onDone: (ticker: string) => void }) {
  const form = ADD_FORM[assetClass];
  const [ticker, setTicker] = useState("");
  const [name, setName] = useState("");
  const [sector, setSector] = useState("perene");
  const [err, setErr] = useState<string | null>(null);
  async function save() {
    setErr(null);
    const body = { ticker, name: name || ticker, asset_class: assetClass, sector: assetClass === "acao" ? sector : null };
    try {
      await api.post("/api/ativos", body);
      onDone(ticker);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    }
  }
  return (
    <Card title={form.title}>
      <div className="grid gap-3 sm:grid-cols-4">
        <Field label="Ticker">
          <input
            className={inputCls}
            value={ticker}
            onChange={(e) => setTicker(e.target.value.toUpperCase())}
            placeholder={form.tickerHint}
          />
        </Field>
        <Field label="Nome">
          <input className={inputCls} value={name} onChange={(e) => setName(e.target.value)} placeholder={form.nameHint} />
        </Field>
        {assetClass === "acao" && (
          <Field label="Setor">
            <select className={inputCls} value={sector} onChange={(e) => setSector(e.target.value)}>
              {Object.entries(SECTOR_LABEL).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </select>
          </Field>
        )}
        <div className="flex items-end">
          <Button onClick={save} disabled={ticker.length < 4}>
            Adicionar
          </Button>
        </div>
      </div>
      <p className="mt-3 text-xs text-muted">{form.hint}</p>
      {err && (
        <div className="mt-3">
          <ErrorBox error={err} />
        </div>
      )}
    </Card>
  );
}

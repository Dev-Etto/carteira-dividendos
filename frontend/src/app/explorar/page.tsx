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
import { FavoriteButton } from "@/components/FavoriteButton";
import { TickerInput } from "@/components/inputs";
import { Investidor10Link } from "@/components/Investidor10Link";
import { api, type AssetRow } from "@/lib/api/client";
import { brl, FII_KIND_LABEL, groupLabel, pct, SECTOR_LABEL } from "@/lib/format";
import { useApi } from "@/lib/useApi";
import { useSyncWatch } from "@/lib/useSyncWatch";
import { checkTicker } from "@/lib/validation";

const VERDICTS = ["", "comprar", "aguardar", "neutro", "evitar"];

type AssetClass = "acao" | "fii" | "etf";

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
  etf: {
    tab: "ETFs",
    title: "Explorar ETFs",
    subtitle:
      "ETFs não recebem nota: o checklist mostra liquidez, tamanho, taxa e se pagam proventos. Marque com ★ os que você quer no aporte; a fatia de ETFs é dividida em partes iguais entre eles.",
    noun: "ETF",
    groupHeader: "Tipo",
    groups: {},
    allGroups: "Todos",
    ceilingHeader: "",
    ceilingHelp: "etf",
    empty: "Nenhum ETF encontrado",
    add: "+ Adicionar ETF",
  },
};

const TAB_CLS = "flex h-10 items-center whitespace-nowrap rounded-[10px] px-4 text-sm transition";
const ACTIVE_TAB_CLS = `${TAB_CLS} bg-surface font-semibold text-ink shadow-card`;
const IDLE_TAB_CLS = `${TAB_CLS} font-medium text-muted hover:text-ink`;
const TABLE_WRAP_CLS = "overflow-x-auto rounded-2xl border border-line bg-surface shadow-card";
const THEAD_CLS = "border-b border-line bg-bg text-left text-xs text-muted";
const TH_CLS = "px-4 py-3 font-semibold";
const TD_CLS = "px-4 py-3.5";

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

      <nav aria-label="Classe de ativo" className="inline-flex flex-wrap gap-1 rounded-xl bg-line p-1">
        {(Object.keys(VIEWS) as AssetClass[]).map((cls) => (
          <button
            key={cls}
            type="button"
            aria-pressed={cls === assetClass}
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
        <Link href="/renda-fixa" className={IDLE_TAB_CLS}>
          Renda fixa
        </Link>
      </nav>

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
        <div className="rounded-xl border border-accent/20 bg-accent-soft px-4 py-3 text-sm text-accent">
          Coletando dados de {collecting.watching}… A lista atualiza sozinha quando terminar.
        </div>
      )}

      <div className="grid gap-3 sm:grid-cols-3">
        <input
          className={inputCls}
          aria-label="Buscar por ticker ou nome"
          placeholder="Buscar por ticker ou nome"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        {assetClass !== "etf" && (
          <>
            <select aria-label={view.groupHeader} className={inputCls} value={sector} onChange={(e) => setSector(e.target.value)}>
              <option value="">{view.allGroups}</option>
              {Object.entries(view.groups).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </select>
            <select aria-label="Veredito" className={inputCls} value={verdict} onChange={(e) => setVerdict(e.target.value)}>
              {VERDICTS.map((v) => (
                <option key={v} value={v}>
                  {v ? v.charAt(0).toUpperCase() + v.slice(1) : "Todos os vereditos"}
                </option>
              ))}
            </select>
          </>
        )}
      </div>

      <AssetsResult
        view={view}
        isEtf={assetClass === "etf"}
        loading={loading}
        data={data}
        rows={rows}
        error={error}
        onRetry={reload}
      />
    </div>
  );
}

function AssetsResult({
  view,
  isEtf,
  loading,
  data,
  rows,
  error,
  onRetry,
}: {
  view: ClassView;
  isEtf: boolean;
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
  if (isEtf) return <EtfTable rows={rows} onChange={onRetry} />;
  return <AssetsTable view={view} rows={rows} />;
}

const STATUS_PILL_CLS = "inline-flex h-[26px] items-center rounded-full px-2.5 text-[13px] font-semibold";

/** Situação do ETF no checklist: só a liquidez reprova; o resto apenas informa. */
function EtfStatus({ verdict }: { verdict: string | null }) {
  if (!verdict) return <span className="text-xs text-subtle">sem avaliação</span>;
  if (verdict === "evitar") return <span className={`${STATUS_PILL_CLS} bg-bad-soft text-bad`}>Evitar</span>;
  return <span className={`${STATUS_PILL_CLS} bg-good-soft text-good`}>Apto</span>;
}

function EtfTable({ rows, onChange }: { rows: AssetRow[]; onChange: () => void }) {
  return (
    <div className={TABLE_WRAP_CLS}>
      <table className="w-full min-w-[560px] text-sm">
        <thead className={THEAD_CLS}>
          <tr>
            <th className={TH_CLS}>ETF</th>
            <th className={TH_CLS}>Favorito</th>
            <th className={TH_CLS}>Situação</th>
            <th className={`${TH_CLS} text-right`}>Preço</th>
            <th className={`${TH_CLS} text-right`}>
              <span className="inline-flex items-center gap-1">
                DY 12m <Help slug="etf-distribui" />
              </span>
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {rows.map((r) => (
            <tr key={r.ticker} className="hover:bg-bg">
              <td className={TD_CLS}>
                <Link href={`/ativo/${r.ticker}`} className="font-bold text-ink hover:text-accent">
                  {r.ticker}
                </Link>
                <div className="text-[13px] text-subtle">{r.name}</div>
                <Investidor10Link ticker={r.ticker} assetClass={r.asset_class} compact />
              </td>
              <td className={TD_CLS}>
                <FavoriteButton ticker={r.ticker} favorite={r.favorite} onChange={onChange} />
              </td>
              <td className={TD_CLS}>
                <EtfStatus verdict={r.verdict} />
              </td>
              <td className={`${TD_CLS} text-right tabular-nums`}>{brl(r.price)}</td>
              <td className={`${TD_CLS} text-right tabular-nums`}>{r.dividend_yield ? pct(r.dividend_yield) : "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function AssetsTable({ view, rows }: { view: ClassView; rows: AssetRow[] }) {
  return (
    <div className={TABLE_WRAP_CLS}>
      <table className="w-full min-w-[760px] text-sm">
        <thead className={THEAD_CLS}>
          <tr>
            <th className={TH_CLS}>{view.noun}</th>
            <th className={TH_CLS}>{view.groupHeader}</th>
            <th className={TH_CLS}>
              <span className="inline-flex items-center gap-1">
                Nota <Help slug="veredito" />
              </span>
            </th>
            <th className={TH_CLS}>Veredito</th>
            <th className={`${TH_CLS} text-right`}>Preço</th>
            <th className={`${TH_CLS} text-right`}>
              <span className="inline-flex items-center gap-1">
                {view.ceilingHeader} <Help slug={view.ceilingHelp} />
              </span>
            </th>
            <th className={`${TH_CLS} text-right`}>Margem</th>
            <th className={`${TH_CLS} text-right`}>
              <span className="inline-flex items-center gap-1">
                DY 12m <Help slug="dividend-yield" />
              </span>
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {rows.map((r) => (
            <tr key={r.ticker} className="hover:bg-bg">
              <td className={TD_CLS}>
                <Link href={`/ativo/${r.ticker}`} className="font-bold text-ink hover:text-accent">
                  {r.ticker}
                </Link>
                <div className="text-[13px] text-subtle">{r.name}</div>
                <Investidor10Link ticker={r.ticker} assetClass={r.asset_class} compact />
              </td>
              <td className={`${TD_CLS} text-muted`}>{groupLabel(r.asset_class, r.sector)}</td>
              <td className={TD_CLS}>
                <ScorePill score={r.score} verdict={r.verdict} />
              </td>
              <td className={TD_CLS}>
                <VerdictBadge verdict={r.verdict} />
              </td>
              <td className={`${TD_CLS} text-right tabular-nums`}>{brl(r.price)}</td>
              <td className={`${TD_CLS} text-right tabular-nums`}>{brl(r.ceiling_price)}</td>
              <td className={`${TD_CLS} text-right tabular-nums ${signClass(r.margin_pct)}`}>{pct(r.margin_pct)}</td>
              <td className={`${TD_CLS} text-right tabular-nums`}>{pct(r.dividend_yield)}</td>
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
  etf: {
    title: "Adicionar ETF ao universo",
    tickerHint: "HASH11",
    nameHint: "Hashdex Nasdaq Crypto",
    hint: "Ao adicionar, o patrimônio (cadastro da CVM) e as cotações dele são coletados na hora. A taxa de administração você informa na ficha.",
  },
};

function AddAsset({ assetClass, onDone }: { assetClass: AssetClass; onDone: (ticker: string) => void }) {
  const form = ADD_FORM[assetClass];
  const [ticker, setTicker] = useState("");
  const [name, setName] = useState("");
  const [sector, setSector] = useState("perene");
  const [err, setErr] = useState<string | null>(null);
  const tickerCheck = checkTicker(ticker);
  async function save() {
    setErr(null);
    const code = tickerCheck.value;
    if (code === null) return;
    const body = { ticker: code, name: name || code, asset_class: assetClass, sector: assetClass === "acao" ? sector : null };
    try {
      await api.post("/api/ativos", body);
      onDone(code);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    }
  }
  return (
    <Card title={form.title}>
      <div className="grid gap-3 sm:grid-cols-4">
        <Field label="Ticker" error={tickerCheck.error}>
          <TickerInput value={ticker} onValueChange={setTicker} placeholder={form.tickerHint} />
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
          <Button onClick={save} disabled={tickerCheck.value === null}>
            Adicionar
          </Button>
        </div>
      </div>
      <p className="mt-3 text-[13px] text-subtle">{form.hint}</p>
      {err && (
        <div className="mt-3">
          <ErrorBox error={err} />
        </div>
      )}
    </Card>
  );
}

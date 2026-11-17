"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import {
  Card,
  ErrorBox,
  Help,
  Loading,
  PageHeader,
  Stat,
  StatusIcon,
  VerdictBadge,
  verdictTone,
  type ScoreTone,
} from "@/components/ui";
import { Investidor10Link } from "@/components/Investidor10Link";
import type { AssetDetail, AssetHistory, RuleResult } from "@/lib/api/client";
import { brl, brlCompact, dateBr, groupLabel, num, pct, SEGMENT_LABEL } from "@/lib/format";
import { withNav } from "@/lib/series";
import { useApi } from "@/lib/useApi";

import { EtfFeeCard, EtfHeader, EtfStats } from "./EtfParts";

type Group = { key: string; title: string; help?: string };
type Extras = Record<string, number | null | undefined>;

const STOCK_GROUPS: Group[] = [
  { key: "qualidade", title: "Qualidade da empresa" },
  { key: "setorial", title: "Regras do setor" },
  { key: "sustentabilidade", title: "O dividendo se sustenta?", help: "fluxo-de-caixa-livre" },
  { key: "preco", title: "O preço está bom?", help: "preco-teto" },
];

const FII_GROUPS: Group[] = [
  { key: "qualidade", title: "Qualidade do fundo" },
  { key: "sustentabilidade", title: "Os rendimentos se mantêm?", help: "estabilidade-rendimentos" },
  { key: "preco", title: "O preço e o rendimento estão bons?", help: "p-vp" },
];

const ETF_GROUPS: Group[] = [{ key: "qualidade", title: "Checklist do ETF", help: "etf" }];

const GROUPS_BY_CLASS: Record<string, Group[]> = { acao: STOCK_GROUPS, fii: FII_GROUPS, etf: ETF_GROUPS };

const SCORE_RING: Record<ScoreTone, string> = {
  good: "border-good text-good",
  warn: "border-warn text-warn",
  neutral: "border-line text-ink",
  bad: "border-bad text-bad",
};

/** Texto do preço-teto com o yield-alvo exigente; avaliações antigas não trazem esse yield. */
function demandingCeilingHint(ex: Extras): string {
  const base = `yield-alvo ${pct(ex.yield_alvo, 0)}`;
  if (ex.yield_alvo_exigente === undefined || ex.yield_alvo_exigente === null) return base;
  return `${base} · com ${pct(ex.yield_alvo_exigente, 0)}: ${brl(ex.teto_exigente)}`;
}

/** Volta para a tela anterior; aberta direto (sem histórico), vai para o Explorar. */
function BackLink() {
  const router = useRouter();
  function goBack() {
    if (window.history.length > 1) return router.back();
    router.push("/explorar");
  }
  return (
    <button type="button" onClick={goBack} className="text-sm text-muted hover:text-ink">
      ← Voltar
    </button>
  );
}

function marginValue(margin: number | null | undefined) {
  return <span className={(margin ?? 0) >= 0 ? "text-good" : "text-bad"}>{pct(margin)}</span>;
}

function StockStats({ data, ex }: { data: AssetDetail; ex: Extras }) {
  return (
    <>
      <Stat label="Preço atual" value={brl(data.price)} hint={data.price_at ? `em ${dateBr(data.price_at)}` : undefined} />
      <Stat label="Preço-teto Barsi" help="preco-teto" value={brl(data.ceiling_price)} hint={demandingCeilingHint(ex)} />
      <Stat label="Margem de segurança" value={marginValue(data.margin_pct)} />
      <Stat
        label="Dividend yield 12m"
        help="dividend-yield"
        value={pct(data.dividend_yield)}
        hint={`média 5 anos: ${pct(ex.dy_medio_5a)}`}
      />
      <Stat label="Teto de Bazin" help="bazin" value={brl(ex.bazin)} hint="segunda opinião" />
      <Stat label="Valor de Graham" help="graham" value={brl(ex.graham)} hint="segunda opinião" />
      <Stat label="ROE médio 5 anos" help="roe" value={pct(ex.roe_medio_5a)} />
      <Stat label="Liquidez diária" help="liquidez" value={brlCompact(data.avg_daily_volume_brl)} />
    </>
  );
}

/** Com o que o rendimento do FII é comparado: CDI líquido (papel) ou juro real do Tesouro IPCA+ (demais). */
function benchmarkHint(sector: string, ex: Extras): string {
  if (sector === "papel") return `CDI líquido de IR: ${pct(ex.cdi_liquido)}`;
  return `Tesouro IPCA+: IPCA + ${pct(ex.ntnb_real)}`;
}

function FiiStats({ data, ex }: { data: AssetDetail; ex: Extras }) {
  const isPaper = data.sector === "papel";
  return (
    <>
      <Stat label="Preço atual" value={brl(data.price)} hint={data.price_at ? `em ${dateBr(data.price_at)}` : undefined} />
      <Stat label="P/VP" help="p-vp" value={num(ex.pvp)} hint={`valor patrimonial da cota: ${brl(ex.valor_patrimonial_cota)}`} />
      <Stat
        label="Preço máximo pelo P/VP"
        help="p-vp"
        value={brl(data.ceiling_price)}
        hint={`${num(ex.pvp_max)} × o valor patrimonial`}
      />
      <Stat label="Margem até o máximo" value={marginValue(data.margin_pct)} />
      <Stat
        label="Dividend yield 12m"
        help="dividend-yield"
        value={pct(data.dividend_yield)}
        hint={benchmarkHint(data.sector, ex)}
      />
      <Stat label="Patrimônio" help="patrimonio-fii" value={brlCompact(ex.patrimonio)} hint={`${num(ex.cotistas, 0)} cotistas`} />
      {isPaper ? (
        <Stat label="Liquidez diária" help="liquidez" value={brlCompact(data.avg_daily_volume_brl)} />
      ) : (
        <Stat label="Vacância" help="vacancia" value={pct(ex.vacancia)} hint={`${num(ex.imoveis, 0)} imóveis`} />
      )}
      <Stat label="Taxa de administração" help="taxa-administracao" value={pct(ex.taxa_adm_ano, 2)} hint="ao ano" />
    </>
  );
}

function subtitle(data: AssetDetail): string {
  const segment = data.segment ? ` · ${SEGMENT_LABEL[data.segment] ?? data.segment}` : "";
  const group = data.economic_group ? ` · grupo ${data.economic_group}` : "";
  return `${groupLabel(data.asset_class, data.sector)}${segment}${group}`;
}

function ScoreHeader({ data }: { data: AssetDetail }) {
  return (
    <div className="flex items-center gap-3">
      <div
        className={`flex h-16 w-16 items-center justify-center rounded-full border-4 text-xl font-bold ${SCORE_RING[verdictTone(data.verdict)]}`}
      >
        {data.score}
      </div>
      <div>
        <div className="flex items-center gap-2">
          <VerdictBadge verdict={data.verdict} />
          <Help slug="veredito" />
        </div>
        <p className="mt-1 max-w-xl text-sm text-ink">{data.summary}</p>
      </div>
    </div>
  );
}

function ClassStats({ data, ex }: { data: AssetDetail; ex: Extras }) {
  if (data.asset_class === "fii") return <FiiStats data={data} ex={ex} />;
  if (data.asset_class === "etf") return <EtfStats data={data} ex={ex} />;
  return <StockStats data={data} ex={ex} />;
}

export function AtivoView() {
  const { ticker } = useParams<{ ticker: string }>();
  const { data, error, loading, reload } = useApi<AssetDetail>(`/api/ativos/${ticker}`);
  const hist = useApi<AssetHistory>(`/api/ativos/${ticker}/historico`);

  if (loading && !data) return <Loading />;
  if (error) return <ErrorBox error={error} onRetry={reload} />;
  if (!data) return null;
  const ex = data.extras as Extras;
  const isFii = data.asset_class === "fii";
  const isEtf = data.asset_class === "etf";
  const groups = GROUPS_BY_CLASS[data.asset_class] ?? STOCK_GROUPS;
  const unit = data.asset_class === "acao" ? "por ação" : "por cota";

  return (
    <div className="space-y-6">
      <BackLink />
      <PageHeader title={`${data.ticker} · ${data.name}`} subtitle={subtitle(data)}>
        <div className="flex flex-wrap gap-2">
          <Investidor10Link ticker={data.ticker} assetClass={data.asset_class} />
          <Link
            href={`/carteira?novo=${data.ticker}`}
            className="rounded-lg border border-line px-4 py-2 text-sm font-medium text-ink hover:bg-neutral-soft"
          >
            Registrar compra
          </Link>
        </div>
      </PageHeader>

      <Card>
        <div className="flex flex-wrap items-center gap-6">
          {isEtf ? <EtfHeader data={data} onChange={() => void reload()} /> : <ScoreHeader data={data} />}
        </div>
        <div className="mt-6 grid grid-cols-2 gap-5 border-t border-line pt-5 md:grid-cols-4">
          <ClassStats data={data} ex={ex} />
        </div>
      </Card>

      <div className="grid gap-6 lg:grid-cols-5">
        <div className="space-y-6 lg:col-span-3">
          {groups.map((g) => {
            const rules = data.rules.filter((r) => r.group === g.key);
            if (!rules.length) return null;
            return (
              <Card key={g.key} title={g.title} help={g.help}>
                <ul className="space-y-4">
                  {rules.map((r) => (
                    <RuleItem key={r.id} r={r} />
                  ))}
                </ul>
              </Card>
            );
          })}
        </div>
        <div className="space-y-6 lg:col-span-2">
          <Card title="Proventos por ano" help="dividendos">
            {hist.data && hist.data.dividends_by_year.length ? (
              <div className="h-52">
                <ResponsiveContainer>
                  <BarChart data={hist.data.dividends_by_year}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--line)" />
                    <XAxis dataKey="year" tick={{ fontSize: 11, fill: "var(--muted)" }} />
                    <YAxis tick={{ fontSize: 11, fill: "var(--muted)" }} width={40} />
                    <Tooltip
                      formatter={(v) => [brl(Number(v)), unit]}
                      contentStyle={{ background: "var(--surface)", border: "1px solid var(--line)", fontSize: 12 }}
                    />
                    <Bar dataKey="amount" fill="var(--accent)" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <p className="text-sm text-muted">Sem histórico ainda.</p>
            )}
          </Card>
          <Card title={isFii ? "Preço × valor patrimonial (5 anos)" : "Preço (5 anos)"} help={isFii ? "p-vp" : undefined}>
            {hist.data && hist.data.prices.length ? (
              <div className="h-52">
                <ResponsiveContainer>
                  <LineChart data={withNav(hist.data.prices, hist.data.nav)}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--line)" />
                    <XAxis
                      dataKey="date"
                      tickFormatter={(d: string) => d.slice(0, 4)}
                      minTickGap={40}
                      tick={{ fontSize: 11, fill: "var(--muted)" }}
                    />
                    <YAxis tick={{ fontSize: 11, fill: "var(--muted)" }} width={40} domain={["auto", "auto"]} />
                    <Tooltip
                      labelFormatter={(d) => dateBr(String(d))}
                      formatter={(v, name) => [brl(Number(v)), name === "nav" ? "valor patrimonial" : "fechamento"]}
                      contentStyle={{ background: "var(--surface)", border: "1px solid var(--line)", fontSize: 12 }}
                    />
                    <Line dataKey="close" stroke="var(--accent)" dot={false} strokeWidth={1.5} />
                    {isFii && <Line dataKey="nav" stroke="var(--muted)" dot={false} strokeWidth={1.5} strokeDasharray="4 3" />}
                  </LineChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <p className="text-sm text-muted">Sem histórico ainda.</p>
            )}
            {data.ceiling_price && (
              <p className="mt-2 text-xs text-muted">
                {isFii ? "Preço máximo pelo P/VP" : "Preço-teto atual"}: {brl(data.ceiling_price)}
                {isFii && " · linha tracejada: valor patrimonial da cota"}
              </p>
            )}
          </Card>
          {isEtf && <EtfFeeCard key={String(ex.taxa_adm_ano)} data={data} ex={ex} onChange={() => void reload()} />}
          <Card title="O que pode dar errado">
            <ul className="space-y-2 text-sm text-ink">
              {data.risks.map((r) => (
                <li key={r} className="flex gap-2">
                  <span className="text-warn">●</span>
                  <span>{r}</span>
                </li>
              ))}
            </ul>
          </Card>
          <Card title="De onde vêm os dados">
            <dl className="space-y-1.5 text-xs">
              {Object.entries(data.data_sources).map(([k, v]) => (
                <div key={k} className="flex justify-between gap-3">
                  <dt className="text-muted">{k}</dt>
                  <dd className="text-right text-ink">{v ?? "sem dado"}</dd>
                </div>
              ))}
            </dl>
            {data.asset_class === "acao" && (
              <p className="mt-3 text-xs text-muted">Anos pagando proventos sem interrupção: {num(ex.anos_pagando ?? 0, 0)}</p>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}

function RuleItem({ r }: { r: RuleResult }) {
  return (
    <li className="flex gap-3">
      <StatusIcon status={r.status} />
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-baseline justify-between gap-x-3">
          <span className="flex items-center gap-1.5 text-sm font-semibold text-ink">
            {r.label}
            <Help slug={r.learn_more} />
            {r.eliminatory && (
              <span className="rounded bg-neutral-soft px-1.5 py-0.5 text-[10px] font-medium text-muted">eliminatória</span>
            )}
          </span>
          <span className="text-sm tabular-nums text-ink">{r.value_display}</span>
        </div>
        <p className="mt-0.5 text-sm text-muted">{r.explanation}</p>
        <p className="mt-0.5 text-xs text-muted">
          Critério: {r.threshold} · peso {r.weight}
        </p>
      </div>
    </li>
  );
}

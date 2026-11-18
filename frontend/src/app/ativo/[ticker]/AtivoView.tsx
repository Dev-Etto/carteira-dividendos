"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import {
  Card,
  ErrorBox,
  Help,
  Loading,
  PageHeader,
  ScorePill,
  Stat,
  StatusIcon,
  VerdictBadge,
  verdictTone,
  type ScoreTone,
} from "@/components/ui";
import { Investidor10Link } from "@/components/Investidor10Link";
import type { AssetDetail, AssetHistory, MethodVerdict, RuleResult } from "@/lib/api/client";
import { brl, brlCompact, dateBr, groupLabel, num, pct, SEGMENT_LABEL } from "@/lib/format";
import { withNav } from "@/lib/series";
import { useApi } from "@/lib/useApi";

import { EtfHeader, EtfInfoCard, EtfStats } from "./EtfParts";

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

const SCORE_BOX: Record<ScoreTone, string> = {
  good: "bg-good-soft text-good",
  warn: "bg-warn-soft text-warn",
  neutral: "bg-neutral-soft text-muted",
  bad: "bg-bad-soft text-bad",
};

const AXIS_TICK = { fontSize: 11, fill: "var(--subtle)" };
const TOOLTIP_STYLE = { background: "var(--surface)", border: "1px solid var(--line)", borderRadius: 10, fontSize: 12 };

/** Rótulo curto em reais para o eixo dos gráficos (sem centavos). */
function axisBrl(value: number): string {
  return `R$ ${num(value, 0)}`;
}

/** Uma marca por ano no eixo X: a primeira data de cada ano da série. */
function yearTicks(points: { date: string }[]): string[] {
  return points.filter((p, i) => i === 0 || p.date.slice(0, 4) !== points[i - 1]?.date.slice(0, 4)).map((p) => p.date);
}

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
    <button type="button" onClick={goBack} className="text-sm font-semibold text-muted hover:text-ink">
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
    <div className="flex items-center gap-5">
      <div
        className={`flex h-[76px] w-[76px] shrink-0 flex-col items-center justify-center rounded-[18px] ${SCORE_BOX[verdictTone(data.verdict)]}`}
      >
        <span className="text-[30px] font-extrabold leading-none tabular-nums">{data.score}</span>
        <span className="text-[11px] font-semibold">de 100</span>
      </div>
      <div>
        <div className="flex items-center gap-2">
          <VerdictBadge verdict={data.verdict} />
          <Help slug="veredito" />
          {data.method_label && <span className="text-[13px] text-subtle">pelo método {data.method_label}</span>}
        </div>
        <p className="mt-1.5 max-w-2xl text-base text-ink">{data.summary}</p>
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
            className="inline-flex h-[42px] items-center whitespace-nowrap rounded-[10px] bg-accent px-[18px] text-sm font-semibold text-white hover:bg-accent-strong"
          >
            Registrar compra
          </Link>
        </div>
      </PageHeader>

      <Card className="p-7">
        <div className="flex flex-wrap items-center gap-6">
          {isEtf ? <EtfHeader data={data} onChange={() => void reload()} /> : <ScoreHeader data={data} />}
        </div>
        <div
          className={`mt-6 grid grid-cols-2 gap-x-6 gap-y-5 border-t border-line pt-5 ${isEtf ? "md:grid-cols-5" : "md:grid-cols-4"}`}
        >
          <ClassStats data={data} ex={ex} />
        </div>
      </Card>

      <div className="grid items-start gap-5 lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)]">
        <div className="space-y-5">
          {groups.map((g) => {
            const rules = data.rules.filter((r) => r.group === g.key);
            if (!rules.length) return null;
            return (
              <Card key={g.key} title={g.title} help={g.help} className="pb-2">
                <ul className="divide-y divide-line border-t border-line">
                  {rules.map((r) => (
                    <RuleItem key={r.id} r={r} />
                  ))}
                </ul>
              </Card>
            );
          })}
        </div>
        <div className="space-y-5">
          <Card title="Proventos por ano" help="dividendos">
            {hist.data && hist.data.dividends_by_year.length ? (
              <div className="h-52">
                <ResponsiveContainer>
                  <BarChart data={hist.data.dividends_by_year}>
                    <CartesianGrid vertical={false} stroke="var(--line)" />
                    <XAxis dataKey="year" tick={AXIS_TICK} tickLine={false} axisLine={{ stroke: "var(--line-strong)" }} />
                    <YAxis tick={AXIS_TICK} width={52} tickFormatter={axisBrl} tickLine={false} axisLine={false} />
                    <Tooltip formatter={(v) => [brl(Number(v)), unit]} contentStyle={TOOLTIP_STYLE} />
                    <Bar dataKey="amount" fill="var(--accent)" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <p className="text-sm text-muted">Sem histórico ainda.</p>
            )}
          </Card>
          {hist.data && hist.data.quarters.length > 0 && <QuartersCard quarters={hist.data.quarters} />}
          <Card title={isFii ? "Preço × valor patrimonial (5 anos)" : "Preço (5 anos)"} help={isFii ? "p-vp" : undefined}>
            {hist.data && hist.data.prices.length ? (
              <div className="h-56">
                <ResponsiveContainer>
                  <LineChart data={withNav(hist.data.prices, hist.data.nav)}>
                    <CartesianGrid vertical={false} stroke="var(--line)" />
                    <XAxis
                      dataKey="date"
                      ticks={yearTicks(hist.data.prices)}
                      tickFormatter={(d: string) => d.slice(0, 4)}
                      tick={AXIS_TICK}
                      tickLine={false}
                      axisLine={{ stroke: "var(--line-strong)" }}
                    />
                    <YAxis
                      tick={AXIS_TICK}
                      width={56}
                      domain={["auto", "auto"]}
                      tickFormatter={axisBrl}
                      tickLine={false}
                      axisLine={false}
                    />
                    <Tooltip
                      labelFormatter={(d) => dateBr(String(d))}
                      formatter={(v, name) => [brl(Number(v)), name === "nav" ? "valor patrimonial" : "fechamento"]}
                      contentStyle={TOOLTIP_STYLE}
                    />
                    <Line dataKey="close" stroke="var(--accent)" dot={false} strokeWidth={2.2} />
                    {isFii && <Line dataKey="nav" stroke="var(--subtle)" dot={false} strokeWidth={2} strokeDasharray="5 4" />}
                  </LineChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <p className="text-sm text-muted">Sem histórico ainda.</p>
            )}
            {data.ceiling_price && (
              <p className="mt-2 text-[13px] text-subtle">
                {isFii ? "Preço máximo pelo P/VP" : "Preço-teto atual"}: {brl(data.ceiling_price)}
                {isFii && " · linha tracejada: valor patrimonial da cota"}
              </p>
            )}
          </Card>
          {isEtf && (
            <EtfInfoCard
              key={`${String(ex.taxa_adm_ano)}-${String(data.extras.distribui)}-${data.region}`}
              data={data}
              ex={ex}
              onChange={() => void reload()}
            />
          )}
          {data.other_methods.length > 0 && <OtherMethodsCard methods={data.other_methods} />}
          <Card title="O que pode dar errado">
            <ul className="space-y-2.5 text-sm text-label">
              {data.risks.map((r) => (
                <li key={r} className="flex gap-2.5">
                  <span aria-hidden="true" className="mt-[7px] h-1.5 w-1.5 shrink-0 rounded-full bg-warn" />
                  <span>{r}</span>
                </li>
              ))}
            </ul>
          </Card>
          <Card title="De onde vêm os dados">
            <dl className="space-y-2 text-[13px]">
              {Object.entries(data.data_sources).map(([k, v]) => (
                <div key={k} className="flex justify-between gap-3">
                  <dt className="text-subtle">{k}</dt>
                  <dd className="text-right text-ink">{v ?? "sem dado"}</dd>
                </div>
              ))}
            </dl>
            {data.asset_class === "acao" && (
              <p className="mt-3 text-[13px] text-subtle">
                Anos pagando proventos sem interrupção: {num(ex.anos_pagando ?? 0, 0)}
              </p>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}

/** Lucro de cada trimestre (ITR; o 4º é a DFP menos os três primeiros). Prejuízo em vermelho. */
function QuartersCard({ quarters }: { quarters: AssetHistory["quarters"] }) {
  return (
    <Card title="Lucro por trimestre" help="lucro">
      <div className="h-52">
        <ResponsiveContainer>
          <BarChart data={quarters}>
            <CartesianGrid vertical={false} stroke="var(--line)" />
            <XAxis dataKey="label" tick={AXIS_TICK} tickLine={false} axisLine={{ stroke: "var(--line-strong)" }} />
            <YAxis tick={AXIS_TICK} width={60} tickFormatter={(v: number) => brlCompact(v)} tickLine={false} axisLine={false} />
            <Tooltip formatter={(v) => [brlCompact(Number(v)), "lucro"]} contentStyle={TOOLTIP_STYLE} />
            <Bar dataKey="net_income" radius={[6, 6, 0, 0]}>
              {quarters.map((q) => (
                <Cell key={q.label} fill={(q.net_income ?? 0) < 0 ? "var(--bad)" : "var(--accent)"} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <p className="mt-2 text-[13px] text-subtle">Só os 3 meses de cada trimestre, pelos balanços entregues à CVM.</p>
    </Card>
  );
}

/** O veredito da ação nas metodologias que o usuário não escolheu, para comparar. */
function OtherMethodsCard({ methods }: { methods: MethodVerdict[] }) {
  return (
    <Card
      title="Nos outros métodos"
      actions={
        <Link href="/config" className="text-sm font-semibold text-accent">
          trocar método →
        </Link>
      }
    >
      <ul className="divide-y divide-line border-t border-line">
        {methods.map((m) => (
          <li key={m.key} className="flex gap-3 py-3">
            <ScorePill score={m.score} verdict={m.verdict} />
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm font-semibold text-ink">{m.label}</span>
                <VerdictBadge verdict={m.verdict} />
              </div>
              <p className="mt-1 text-[13px] text-muted">{m.summary}</p>
            </div>
          </li>
        ))}
      </ul>
    </Card>
  );
}

function RuleItem({ r }: { r: RuleResult }) {
  return (
    <li className="flex gap-3 py-4">
      <StatusIcon status={r.status} />
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-baseline justify-between gap-x-3">
          <span className="flex items-center gap-1.5 text-[15px] font-semibold text-ink">
            {r.label}
            <Help slug={r.learn_more} />
            {r.eliminatory && (
              <span className="rounded-md bg-neutral-soft px-1.5 py-0.5 text-[11px] font-semibold text-muted">eliminatória</span>
            )}
          </span>
          <span className="whitespace-nowrap text-[15px] font-semibold tabular-nums text-ink">{r.value_display}</span>
        </div>
        <p className="mt-0.5 text-sm text-muted">{r.explanation}</p>
        <p className="mt-0.5 text-xs text-subtle">
          Critério: {r.threshold} · peso {r.weight}
        </p>
      </div>
    </li>
  );
}

"use client";

import Link from "next/link";
import { useState } from "react";

import { AllocationBars } from "@/components/AllocationBars";
import { FilingList } from "@/components/FilingList";
import { ShowMoreButton } from "@/components/ShowMoreButton";
import { Card, ErrorBox, Loading, PageHeader, ProgressBar, ScorePill, Stat, VerdictBadge } from "@/components/ui";
import type { Dashboard } from "@/lib/api/client";
import { brl, dateBr, groupLabel, pct, PROFILE_LABEL } from "@/lib/format";
import { hiddenCount, visibleItems } from "@/lib/lists";
import { useApi } from "@/lib/useApi";

const FILINGS_SHOWN = 5;

function AlertIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 16 16"
      aria-hidden="true"
      className="mt-1 shrink-0 text-warn"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M8 2 L14.5 13.5 H1.5 Z" />
      <path d="M8 6.5 V9.5" />
      <circle cx="8" cy="11.5" r="0.6" fill="currentColor" />
    </svg>
  );
}

export default function Inicio() {
  const [showAllFilings, setShowAllFilings] = useState(false);
  const { data, error, loading, reload } = useApi<Dashboard>("/api/painel");
  if (loading && !data) return <Loading />;
  if (error) return <ErrorBox error={error} onRetry={reload} />;
  if (!data) return null;
  const p = data.profile;
  const monthlyIncome = data.income_12m / 12;
  const goal = data.passive_income_goal;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Início"
        subtitle={
          p.onboarded
            ? `Perfil ${PROFILE_LABEL[p.risk_profile]?.toLowerCase()} · ${p.risk_description}`
            : "Bem-vindo! Comece definindo seu perfil."
        }
      />

      <Link
        href={data.next_step.href}
        className="flex flex-wrap items-center justify-between gap-6 rounded-2xl bg-accent px-8 py-7 text-white transition hover:bg-accent-strong"
      >
        <div>
          <div className="text-[13px] font-semibold text-white/75">Seu próximo passo</div>
          <div className="mt-1 text-2xl font-bold tracking-tight">{data.next_step.title}</div>
          <div className="mt-1 text-white/85">{data.next_step.description}</div>
        </div>
        <span className="inline-flex h-11 items-center gap-2 rounded-[10px] bg-surface px-[18px] font-semibold text-accent">
          Ir agora
          <svg
            width="16"
            height="16"
            viewBox="0 0 16 16"
            aria-hidden="true"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M3 8 H13 M9 4 L13 8 L9 12" />
          </svg>
        </span>
      </Link>

      <div className="grid gap-5 md:grid-cols-3">
        <Card>
          <Stat
            label="Reserva de emergência"
            help="reserva-de-emergencia"
            value={brl(data.reserve_value)}
            hint={`meta de ${brl(data.reserve_target)}`}
          />
          <ProgressBar className="mt-3" value={data.reserve_value} max={data.reserve_target} />
        </Card>
        <Card>
          <Stat
            label="Patrimônio investido"
            value={brl(data.total_invested + data.cash_to_invest)}
            hint={
              data.cash_to_invest > 0
                ? `sem a reserva; inclui ${brl(data.cash_to_invest)} de caixa a investir`
                : "sem contar a reserva"
            }
          />
        </Card>
        <Card>
          <Stat
            label="Renda passiva (média mensal)"
            help="dividendos"
            value={brl(monthlyIncome)}
            hint={goal > 0 ? `meta de ${brl(goal)}/mês · ${pct(monthlyIncome / goal, 0)} do caminho` : "últimos 12 meses"}
          />
          {goal > 0 && <ProgressBar className="mt-3" value={monthlyIncome} max={goal} />}
        </Card>
      </div>

      {data.alerts.length > 0 && (
        <section className="rounded-2xl border border-warn/30 bg-warn-soft px-6 py-5">
          <h2 className="text-base font-bold text-warn">Alertas</h2>
          <ul className="mt-2 space-y-1.5">
            {data.alerts.map((a) => (
              <li key={a} className="flex items-start gap-2.5 text-ink">
                <AlertIcon />
                {a}
              </li>
            ))}
          </ul>
        </section>
      )}

      {data.filings.length > 0 && (
        <Card title="Fatos relevantes da sua carteira (30 dias)" help="comunicados">
          <FilingList filings={visibleItems(data.filings, FILINGS_SHOWN, showAllFilings)} showTicker />
          <ShowMoreButton
            hidden={hiddenCount(data.filings.length, FILINGS_SHOWN, showAllFilings)}
            onClick={() => setShowAllFilings(true)}
          />
        </Card>
      )}

      <div className="grid items-start gap-5 lg:grid-cols-[5fr_7fr]">
        <Card title="Divisão da carteira: atual × alvo" help="diversificacao">
          <AllocationBars classes={data.classes} />
        </Card>
        <Card
          title="Melhores oportunidades hoje"
          help="veredito"
          actions={
            <Link href="/explorar" className="text-sm font-semibold text-accent">
              Ver todas
            </Link>
          }
        >
          {data.top_opportunities.length === 0 ? (
            <p className="text-sm text-muted">
              Nenhuma ação com veredito &quot;comprar&quot; agora. Rode a atualização de dados em Configurações, ou espere preços
              melhores.
            </p>
          ) : (
            <ul className="divide-y divide-line border-t border-line">
              {data.top_opportunities.map((a) => (
                <li key={a.ticker}>
                  <Link href={`/ativo/${a.ticker}`} className="flex items-center justify-between gap-4 py-3.5 hover:opacity-80">
                    <div>
                      <div className="font-bold text-ink">
                        {a.ticker} <span className="font-normal text-muted">· {a.name}</span>
                      </div>
                      <div className="text-[13px] text-subtle">
                        {groupLabel(a.asset_class, a.sector)} · DY {pct(a.dividend_yield)} · {pct(a.margin_pct)} abaixo do{" "}
                        {a.asset_class === "fii" ? "preço máximo" : "teto"}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <ScorePill score={a.score} verdict={a.verdict} />
                      <VerdictBadge verdict={a.verdict} />
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <Card title="Cenário">
        <div className="grid grid-cols-2 gap-5 md:grid-cols-4">
          <Stat label="Selic" help="selic" value={pct(data.macro.selic_meta, 2)} />
          <Stat label="CDI" help="cdi" value={pct(data.macro.cdi, 2)} />
          <Stat label="IPCA 12 meses" help="ipca" value={pct(data.macro.ipca_12m, 2)} />
          <Stat
            label="Última atualização"
            value={data.last_sync ? dateBr(data.last_sync) : "nunca"}
            hint={data.macro.as_of ? `dados do BC de ${dateBr(data.macro.as_of)}` : undefined}
          />
        </div>
      </Card>
    </div>
  );
}

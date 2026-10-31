"use client";

import Link from "next/link";

import { AllocationBars } from "@/components/AllocationBars";
import { Card, ErrorBox, Loading, PageHeader, ProgressBar, ScorePill, Stat, VerdictBadge } from "@/components/ui";
import type { Dashboard } from "@/lib/api/client";
import { brl, dateBr, pct, PROFILE_LABEL, SECTOR_LABEL } from "@/lib/format";
import { useApi } from "@/lib/useApi";

export default function Inicio() {
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
        className="block rounded-xl border border-accent/30 bg-accent-soft p-5 transition hover:border-accent"
      >
        <div className="text-xs font-semibold uppercase tracking-wide text-accent">Seu próximo passo</div>
        <div className="mt-1 text-lg font-semibold text-ink">{data.next_step.title}</div>
        <div className="mt-1 text-sm text-muted">{data.next_step.description}</div>
        <div className="mt-3 text-sm font-semibold text-accent">Ir agora →</div>
      </Link>

      <div className="grid gap-4 md:grid-cols-3">
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
          <Stat label="Patrimônio investido" value={brl(data.total_invested)} hint="sem contar a reserva" />
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
        <Card title="Alertas">
          <ul className="space-y-2 text-sm">
            {data.alerts.map((a) => (
              <li key={a} className="flex gap-2 text-ink">
                <span className="text-warn">●</span>
                {a}
              </li>
            ))}
          </ul>
        </Card>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Divisão da carteira: atual × alvo" help="diversificacao">
          <AllocationBars classes={data.classes} />
        </Card>
        <Card
          title="Melhores oportunidades hoje"
          help="veredito"
          actions={
            <Link href="/explorar" className="text-xs font-semibold text-accent">
              ver todas →
            </Link>
          }
        >
          {data.top_opportunities.length === 0 ? (
            <p className="text-sm text-muted">
              Nenhuma ação com veredito &quot;comprar&quot; agora. Rode a atualização de dados em Configurações, ou espere preços
              melhores.
            </p>
          ) : (
            <ul className="divide-y divide-line">
              {data.top_opportunities.map((a) => (
                <li key={a.ticker}>
                  <Link href={`/ativo/${a.ticker}`} className="flex items-center justify-between gap-3 py-2.5 hover:opacity-80">
                    <div>
                      <div className="text-sm font-semibold text-ink">
                        {a.ticker} <span className="font-normal text-muted">· {a.name}</span>
                      </div>
                      <div className="text-xs text-muted">
                        {SECTOR_LABEL[a.sector]} · DY {pct(a.dividend_yield)} · {pct(a.margin_pct)} abaixo do teto
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
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
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <Stat label="Selic" help="selic" value={pct(data.macro.selic_meta, 2)} />
          <Stat label="CDI" help="cdi" value={pct(data.macro.cdi, 2)} />
          <Stat label="IPCA 12 meses" help="ipca" value={pct(data.macro.ipca_12m, 2)} />
          <Stat
            label="Última atualização"
            value={<span className="text-base">{data.last_sync ? dateBr(data.last_sync) : "nunca"}</span>}
            hint={data.macro.as_of ? `dados do BC de ${dateBr(data.macro.as_of)}` : undefined}
          />
        </div>
      </Card>
    </div>
  );
}

"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, type ReactNode } from "react";

import { ErrorBox, Loading, PageHeader } from "@/components/ui";
import { type Methods, type ProfileOut } from "@/lib/api/client";
import { CONFIG_SECTIONS, configHref, SECTION_PARAM, sectionFromParam, type ConfigSection } from "@/lib/configSections";
import { methodLabel } from "@/lib/methods";
import { useApi } from "@/lib/useApi";

import { AllocationSection } from "./AllocationSection";
import { SectionHeader } from "./parts";
import { ProfileSection } from "./ProfileSection";
import { RulesSection } from "./RulesSection";
import { SyncSection } from "./SyncSection";

export default function ConfigPage() {
  return (
    <Suspense fallback={<Loading />}>
      <Config />
    </Suspense>
  );
}

/** Menu lateral das seções; em telas estreitas vira uma faixa de abas rolável no topo. */
function SectionNav({ active }: { active: ConfigSection }) {
  return (
    <nav aria-label="Seções das configurações" className="lg:sticky lg:top-6">
      <ul className="flex gap-1 overflow-x-auto border-b border-line pb-2 lg:flex-col lg:border-b-0 lg:pb-0">
        {CONFIG_SECTIONS.map((s) => {
          const current = s.key === active;
          return (
            <li key={s.key} className="shrink-0">
              <Link
                href={configHref(s.key)}
                replace
                scroll={false}
                aria-current={current ? "page" : undefined}
                className={`block whitespace-nowrap rounded-[10px] px-3.5 py-2.5 text-sm font-semibold transition ${
                  current ? "bg-accent-soft text-accent" : "text-muted hover:bg-neutral-soft hover:text-ink"
                }`}
              >
                {s.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

/**
 * Configurações em quatro seções, com a ativa na URL (`/config?secao=regras`) para voltar e compartilhar.
 * Todas ficam montadas e só a ativa aparece: trocar de seção não perde o que foi digitado e não salvo.
 */
function Config() {
  const active = sectionFromParam(useSearchParams().get(SECTION_PARAM));
  const profile = useApi<ProfileOut>("/api/perfil");
  const methods = useApi<Methods>("/api/metodos");
  const failure = profile.error ?? methods.error;
  const ready = profile.data && methods.data;

  function needsProfile(render: (p: ProfileOut, m: Methods) => ReactNode): ReactNode {
    if (failure && !ready)
      return <ErrorBox error={failure} onRetry={() => void Promise.all([profile.reload(), methods.reload()])} />;
    if (!profile.data || !methods.data) return <Loading />;
    return render(profile.data, methods.data);
  }

  const content: Record<ConfigSection, ReactNode> = {
    perfil: needsProfile((p, m) => <ProfileSection methods={m} profile={p} onSaved={profile.reload} />),
    divisao: needsProfile((p, m) => (
      <AllocationSection
        key={p.allocation_method}
        method={p.allocation_method}
        methodName={methodLabel(m.allocation, p.allocation_method)}
      />
    )),
    regras: needsProfile((p, m) => (
      <RulesSection selectionMethod={p.selection_method} selectionName={methodLabel(m.selection, p.selection_method)} />
    )),
    dados: <SyncSection />,
  };

  return (
    <div>
      <PageHeader
        title="Configurações"
        subtitle="Seu perfil, a divisão da carteira, os limites das regras e os dados do mercado."
      />
      <div className="grid items-start gap-6 lg:grid-cols-[220px_minmax(0,1fr)] lg:gap-10">
        <SectionNav active={active} />
        <div className="min-w-0">
          {CONFIG_SECTIONS.map((s) => (
            <section key={s.key} hidden={s.key !== active} aria-labelledby={`secao-${s.key}`}>
              <SectionHeader id={`secao-${s.key}`} title={s.label} description={s.description} />
              {content[s.key]}
            </section>
          ))}
        </div>
      </div>
    </div>
  );
}

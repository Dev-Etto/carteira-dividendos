"use client";

import Link from "next/link";
import { useState } from "react";

import { MethodPicker } from "@/components/MethodPicker";
import { Card, ErrorBox } from "@/components/ui";
import { api, type Methods, type ProfileOut } from "@/lib/api/client";
import { PROFILE_LABEL } from "@/lib/format";
import { choiceChanged, methodLabel, resolveChoice, type MethodDraft } from "@/lib/methods";
import { saveStatus } from "@/lib/saveStatus";

import { errorText, SaveBar } from "./parts";

/** Perfil de risco, com o atalho para refazer o questionário. */
function RiskProfileCard({ profile }: { profile: ProfileOut }) {
  return (
    <Card>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 max-w-2xl">
          <div className="text-[13px] font-semibold uppercase tracking-wide text-subtle">Perfil de risco</div>
          <div className="mt-1 text-lg font-bold text-ink">
            {profile.onboarded ? (PROFILE_LABEL[profile.risk_profile] ?? profile.risk_profile) : "Ainda não definido"}
          </div>
          <p className="mt-1 text-sm text-muted">
            {profile.onboarded ? profile.risk_description : "Responda o questionário para o app sugerir a divisão da carteira."}
          </p>
        </div>
        <Link
          href="/onboarding"
          className="inline-flex h-[42px] items-center rounded-[10px] border border-line-strong bg-surface px-[18px] text-sm font-semibold text-ink transition hover:bg-neutral-soft"
        >
          {profile.onboarded ? "Refazer questionário" : "Responder questionário"}
        </Link>
      </div>
    </Card>
  );
}

/** As duas metodologias, com uma barra de salvar que mostra se há escolha pendente. */
function MethodsCard({ methods, profile, onSaved }: { methods: Methods; profile: ProfileOut; onSaved: () => Promise<void> }) {
  const [draft, setDraft] = useState<MethodDraft>({});
  const [saved, setSaved] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const choice = resolveChoice(draft, profile);
  const dirty = choiceChanged(choice, profile);
  const allocationChanged = choice.allocation_method !== profile.allocation_method;
  const pending = Number(choice.selection_method !== profile.selection_method) + Number(allocationChanged);

  async function save() {
    setErr(null);
    setSaved(null);
    setSaving(true);
    try {
      await api.put("/api/perfil/metodos", choice);
      setDraft({});
      await onSaved();
      setSaved("Metodologias salvas. Vereditos e recomendações já seguem a escolha.");
    } catch (e) {
      setErr(errorText(e));
    }
    setSaving(false);
  }

  return (
    <Card title="Metodologias" help="metodologias">
      <MethodPicker
        methods={methods}
        value={choice}
        onChange={(c) => {
          setSaved(null);
          setDraft((d) => ({ ...d, ...c }));
        }}
        columns
      />
      {allocationChanged && (
        <p className="mt-4 rounded-xl border border-warn/30 bg-warn-soft px-4 py-3 text-sm text-warn">
          Ao salvar, a divisão-alvo da carteira passa a ser a sugerida pelo{" "}
          <strong>{methodLabel(methods.allocation, choice.allocation_method)}</strong>. Você pode ajustá-la depois em Divisão da
          carteira.
        </p>
      )}
      {err && (
        <div className="mt-4">
          <ErrorBox error={err} />
        </div>
      )}
      <SaveBar
        status={saveStatus(saved, null, pending)}
        dirty={dirty}
        canSave={dirty}
        saving={saving}
        onSave={() => void save()}
        onDiscard={() => setDraft({})}
        saveLabel="Salvar metodologias"
      />
    </Card>
  );
}

export function ProfileSection({
  methods,
  profile,
  onSaved,
}: {
  methods: Methods;
  profile: ProfileOut;
  onSaved: () => Promise<void>;
}) {
  return (
    <div className="space-y-5">
      <RiskProfileCard profile={profile} />
      <MethodsCard methods={methods} profile={profile} onSaved={onSaved} />
    </div>
  );
}

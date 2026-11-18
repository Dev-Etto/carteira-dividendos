"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button, Card, ErrorBox, Field, Help, inputCls, Loading, PageHeader } from "@/components/ui";
import { api, type ProfileOut, type Question } from "@/lib/api/client";
import { brl, decimalStr, num, PROFILE_LABEL } from "@/lib/format";
import { useApi } from "@/lib/useApi";

const STABILITY = [
  { v: "estavel", label: "Estável (CLT, concursado, aposentado)", months: 6 },
  { v: "variavel", label: "Varia um pouco (comissões, PJ com contrato)", months: 9 },
  { v: "instavel", label: "Instável (autônomo, freelancer, sem emprego fixo)", months: 12 },
] as const;

/** Valor monetário do perfil no formato brasileiro, ou vazio quando ainda não há perfil ou o valor é zero. */
function moneyText(onboarded: boolean, value: number | string): string {
  const n = Number(value);
  return onboarded && n > 0 ? num(n, 2) : "";
}

/** Dica ao lado do botão desabilitado: a primeira pergunta ainda sem resposta. */
function pendingHint(qs: Question[], answers: Record<string, number>): string | null {
  const pending = qs.findIndex((q) => answers[q.id] === undefined);
  if (pending < 0) return null;
  return `Responda a pergunta ${pending + 1} para continuar.`;
}

function StepNumber({ n }: { n: number }) {
  return (
    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[10px] bg-accent-soft font-bold text-accent">
      {n}
    </span>
  );
}

export default function Onboarding() {
  const questions = useApi<Question[]>("/api/perfil/questionario");
  const profile = useApi<ProfileOut>("/api/perfil");
  const error = questions.error ?? profile.error;

  if (error) return <ErrorBox error={error} />;
  if (!questions.data || !profile.data) return <Loading />;
  return <OnboardingForm qs={questions.data} profile={profile.data} />;
}

/** Questionário e números do perfil. Quem já tem perfil vê as respostas atuais preenchidas. */
function OnboardingForm({ qs, profile }: { qs: Question[]; profile: ProfileOut }) {
  const router = useRouter();
  const known = profile.onboarded;
  const [answers, setAnswers] = useState<Record<string, number>>(known ? (profile.answers ?? {}) : {});
  const [stability, setStability] = useState<string>(known ? profile.income_stability : "estavel");
  const [expenses, setExpenses] = useState(moneyText(known, profile.monthly_expenses));
  const [contribution, setContribution] = useState(moneyText(known, profile.monthly_contribution));
  const [goal, setGoal] = useState(moneyText(known, profile.passive_income_goal));
  const [keepAllocation, setKeepAllocation] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [result, setResult] = useState<ProfileOut | null>(null);

  const money = { expenses: decimalStr(expenses), contribution: decimalStr(contribution || "0"), goal: decimalStr(goal || "0") };
  const invalid = Object.values(money).some((v) => v === null || Number(v) < 0);
  const complete = qs.every((q) => answers[q.id] !== undefined) && expenses !== "" && !invalid;
  const hint = pendingHint(qs, answers);

  async function submit() {
    setSaving(true);
    setSaveError(null);
    try {
      const p = await api.put<ProfileOut>("/api/perfil", {
        answers,
        income_stability: stability,
        monthly_expenses: money.expenses,
        monthly_contribution: money.contribution,
        passive_income_goal: money.goal,
        keep_allocation: known && keepAllocation,
      });
      setResult(p);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  }

  if (result) {
    return (
      <div className="mx-auto max-w-[820px] space-y-5">
        <span className="inline-flex h-[26px] items-center rounded-full bg-accent-soft px-2.5 text-[13px] font-semibold text-accent">
          Perfil definido
        </span>
        <PageHeader title={`Seu perfil: ${PROFILE_LABEL[result.risk_profile]}`} subtitle={result.risk_description} />
        <Card title="O que isso significa">
          <ul className="space-y-4 text-ink">
            <li className="flex gap-3.5">
              <StepNumber n={1} />
              <span>
                <strong>Reserva de emergência: {brl(result.emergency_target)}</strong> ({result.emergency_months} meses dos seus
                gastos). Ela vem primeiro. Enquanto não estiver completa, o assistente coloca todo aporte nela.
              </span>
            </li>
            <li className="flex gap-3.5">
              <StepNumber n={2} />
              <span>
                <strong>Depois da reserva:</strong> o app divide seus aportes entre renda fixa, ações, FIIs e ETFs na proporção do
                seu perfil. Você pode ajustar essa divisão em Configurações.
              </span>
            </li>
            <li className="flex gap-3.5">
              <StepNumber n={3} />
              <span>
                <strong>Reinvestimento:</strong> os proventos que você receber entram no aporte seguinte. É assim que a bola de
                neve começa.
              </span>
            </li>
          </ul>
        </Card>
        <div className="flex gap-3">
          <Button onClick={() => router.push("/")}>Ir para o início</Button>
          <Button variant="ghost" onClick={() => setResult(null)}>
            Refazer
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-[820px] space-y-5">
      <PageHeader
        title="Seu perfil de investidor"
        subtitle="Cinco perguntas rápidas e alguns números. Com isso, o app sugere quanto guardar de reserva e como dividir seus investimentos."
      />

      {qs.map((q, i) => (
        <Card key={q.id}>
          <div className="mb-4 flex items-center gap-3">
            <span className="flex h-[26px] w-[26px] shrink-0 items-center justify-center rounded-full bg-neutral-soft text-[13px] font-bold text-muted">
              {i + 1}
            </span>
            <h2 className="text-base font-semibold text-ink">{q.text}</h2>
          </div>
          <div className="grid gap-3 sm:grid-cols-3">
            {q.options.map((o) => (
              <label
                key={o.label}
                className={`flex min-h-[52px] cursor-pointer items-center gap-2.5 rounded-xl border px-4 text-[15px] text-ink transition ${
                  answers[q.id] === o.points
                    ? "border-accent bg-accent-soft ring-1 ring-accent"
                    : "border-line-strong hover:bg-neutral-soft"
                }`}
              >
                <input
                  type="radio"
                  name={q.id}
                  className="accent-[var(--accent)]"
                  checked={answers[q.id] === o.points}
                  onChange={() => setAnswers((a) => ({ ...a, [q.id]: o.points }))}
                />
                {o.label}
              </label>
            ))}
          </div>
        </Card>
      ))}

      <Card title="Sua renda e seus gastos" help="reserva-de-emergencia">
        <div className="space-y-4">
          <Field label="Como é a sua renda?">
            <select className={inputCls} value={stability} onChange={(e) => setStability(e.target.value)}>
              {STABILITY.map((s) => (
                <option key={s.v} value={s.v}>
                  {s.label} — reserva de {s.months} meses
                </option>
              ))}
            </select>
          </Field>
          <div className="grid gap-4 sm:grid-cols-3">
            <Field label="Gastos mensais (R$)" hint="o essencial para viver">
              <input
                className={inputCls}
                inputMode="decimal"
                value={expenses}
                onChange={(e) => setExpenses(e.target.value)}
                placeholder="3.000"
              />
            </Field>
            <Field label="Quanto pretende investir por mês (R$)">
              <input
                className={inputCls}
                inputMode="decimal"
                value={contribution}
                onChange={(e) => setContribution(e.target.value)}
                placeholder="500"
              />
            </Field>
            <Field label="Meta de renda passiva por mês (R$)">
              <input
                className={inputCls}
                inputMode="decimal"
                value={goal}
                onChange={(e) => setGoal(e.target.value)}
                placeholder="2000"
              />
            </Field>
          </div>
          <p className="flex items-center gap-1 text-[13px] text-muted">
            Por que perguntamos a estabilidade da renda? <Help slug="reserva-de-emergencia" />
          </p>
        </div>
      </Card>

      {invalid && expenses !== "" && (
        <ErrorBox error="Algum valor não é um número válido. Use, por exemplo, 3.000 ou 3.000,50." />
      )}
      {known && (
        <Card>
          <label className="flex cursor-pointer items-start gap-3 text-ink">
            <input
              type="checkbox"
              className="mt-0.5 accent-[var(--accent)]"
              checked={keepAllocation}
              onChange={(e) => setKeepAllocation(e.target.checked)}
            />
            <span>
              <strong>Manter minha divisão-alvo atual</strong>
              <span className="block text-sm text-muted">
                Desmarcado, a divisão entre renda fixa, ações, FIIs e ETFs volta à sugerida para o perfil que sair destas
                respostas.
              </span>
            </span>
          </label>
        </Card>
      )}
      {saveError && <ErrorBox error={saveError} />}
      <div className="flex flex-wrap items-center gap-4">
        <Button onClick={submit} disabled={!complete || saving}>
          {saving ? "Salvando…" : "Ver meu perfil"}
        </Button>
        {hint && <span className="text-sm text-muted">{hint}</span>}
      </div>
    </div>
  );
}

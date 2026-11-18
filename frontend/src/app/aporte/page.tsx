"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { Button, Card, ErrorBox, Field, Help, inputCls, Loading, PageHeader } from "@/components/ui";
import { RegisterPlanCard, type RegisterPlanOut } from "@/components/aporte/RegisterPlanCard";
import { api, type Plan, type ProfileOut } from "@/lib/api/client";
import { brl, CLASS_LABEL, num, parseNumber } from "@/lib/format";
import { useApi } from "@/lib/useApi";

const AMOUNT_PARAM = "valor";

/**
 * Campo de valor. Começa com o valor da URL (quem volta da ficha de um ativo reencontra o que digitou)
 * ou, sem ele, com o aporte mensal do perfil. Apagar tudo deixa o campo vazio.
 */
function useAmountField(fromUrl: number | null, defaultAmount: number) {
  const [typed, setTyped] = useState<string | null>(fromUrl === null ? null : num(fromUrl, 2));
  return [typed ?? (defaultAmount > 0 ? num(defaultAmount, 2) : ""), setTyped] as const;
}

function validAmount(text: string | null): number | null {
  const amount = parseNumber(text ?? "");
  if (amount === null || amount <= 0) return null;
  return amount;
}

export default function AportePage() {
  return (
    <Suspense fallback={<Loading />}>
      <Aporte />
    </Suspense>
  );
}

/**
 * O valor do aporte fica na URL (`/aporte?valor=1500`) e o plano é montado a partir dela. Assim, ao abrir
 * a ficha de um ativo do plano e voltar, a página remonta o mesmo plano em vez de recomeçar do zero.
 */
type PlanResult = { amount: number; round: number; plan: Plan | null; error: string | null };

function Aporte() {
  const router = useRouter();
  const urlAmount = validAmount(useSearchParams().get(AMOUNT_PARAM));
  const profile = useApi<ProfileOut>("/api/perfil");
  const [value, setAmount] = useAmountField(urlAmount, Number(profile.data?.monthly_contribution ?? 0));
  const [round, setRound] = useState(0);
  const [result, setResult] = useState<PlanResult | null>(null);
  const [inputError, setInputError] = useState<string | null>(null);
  const [registered, setRegistered] = useState<RegisterPlanOut | null>(null);

  const parsed = parseNumber(value);

  useEffect(() => {
    if (urlAmount === null) return;
    let active = true;
    const keep = (plan: Plan | null, error: string | null) => {
      if (!active) return;
      setResult({ amount: urlAmount, round, plan, error });
    };
    api.post<Plan>("/api/aporte/plano", { amount: urlAmount }).then(
      (plan) => keep(plan, null),
      (e: unknown) => keep(null, e instanceof Error ? e.message : String(e)),
    );
    return () => {
      active = false;
    };
  }, [urlAmount, round]);

  const current = result && result.amount === urlAmount && result.round === round ? result : null;
  const busy = urlAmount !== null && current === null;
  const plan = current?.plan ?? null;
  const err = inputError ?? current?.error ?? null;

  /** Monta o plano: põe o valor na URL, de onde o plano é carregado. Mesmo valor de novo recalcula. */
  function calc() {
    if (parsed === null || parsed <= 0) return setInputError("Informe um valor de aporte válido, por exemplo 1.500 ou 1.500,00.");
    setInputError(null);
    setRegistered(null);
    if (parsed === urlAmount) return setRound((r) => r + 1);
    router.replace(`/aporte?${AMOUNT_PARAM}=${parsed}`, { scroll: false });
  }

  /** Depois de registrar, o plano é limpo e o valor sai da URL: registrar de novo exige montar outro plano. */
  function onRegistered(done: RegisterPlanOut) {
    setRegistered(done);
    router.replace("/aporte", { scroll: false });
  }

  return (
    <div className="space-y-5">
      <PageHeader
        title="Aporte do mês"
        subtitle="Diga quanto vai investir. O app segue sempre a mesma ordem: reserva de emergência → classes abaixo do alvo → melhores ativos com preço bom."
      />

      {profile.data && !profile.data.onboarded && (
        <div className="rounded-2xl border border-warn/30 bg-warn-soft px-5 py-4 text-sm text-warn">
          Você ainda não definiu seu perfil.{" "}
          <Link href="/onboarding" className="font-semibold underline">
            Defina agora
          </Link>{" "}
          para o plano considerar sua reserva e a divisão ideal.
        </div>
      )}

      <Card>
        <div className="flex flex-wrap items-end gap-4">
          <div className="w-72">
            <Field label="Valor do aporte (R$)">
              <input
                className={`${inputCls} text-lg font-bold tabular-nums`}
                inputMode="decimal"
                value={value}
                onChange={(e) => setAmount(e.target.value)}
                placeholder="1.000,00"
              />
            </Field>
          </div>
          <Button onClick={calc} disabled={parsed === null || parsed <= 0 || busy}>
            {busy ? "Calculando…" : "Montar plano"}
          </Button>
          <span className="flex items-center gap-1 pb-2.5 text-sm text-muted">
            Como o plano é montado? <Help slug="aporte" />
          </span>
        </div>
      </Card>

      {err && <ErrorBox error={err} />}

      {registered && <RegisteredNotice result={registered} />}

      {plan && (
        <>
          <Card title={`Plano para ${brl(plan.amount)}`}>
            <ul className="divide-y divide-line border-t border-line">
              {plan.lines.map((l, i) => (
                <li key={i} className="grid grid-cols-[110px_minmax(0,1fr)_auto] items-center gap-4 py-3.5">
                  <span>
                    <span className="rounded-md bg-neutral-soft px-2 py-0.5 text-xs font-semibold text-muted">
                      {CLASS_LABEL[l.asset_class] ?? l.asset_class}
                    </span>
                  </span>
                  <div className="min-w-0">
                    <div className="font-semibold text-ink">
                      {l.ticker ? (
                        <Link className="hover:text-accent" href={`/ativo/${l.ticker}`}>
                          {l.ticker}
                        </Link>
                      ) : (
                        l.product
                      )}
                      {l.ticker && <span className="font-normal text-muted"> · {l.product}</span>}
                    </div>
                    <div className="text-[13px] text-subtle">{l.reason}</div>
                  </div>
                  <div className="text-right">
                    <div className="font-bold tabular-nums text-ink">{brl(l.amount)}</div>
                    {l.quantity && (
                      <div className="text-[13px] tabular-nums text-subtle">
                        {num(l.quantity, 0)} × {brl(l.unit_price)}
                      </div>
                    )}
                  </div>
                </li>
              ))}
            </ul>
            {plan.notes.length > 0 && (
              <div className="mt-4 space-y-1 rounded-xl bg-neutral-soft p-4 text-sm text-muted">
                {plan.notes.map((n) => (
                  <p key={n}>{n}</p>
                ))}
              </div>
            )}
          </Card>

          <RegisterPlanCard key={plan.lines.map((l) => l.product).join("|")} plan={plan} onRegistered={onRegistered} />
        </>
      )}

      <Card title="Regras do assistente">
        <ol className="list-decimal space-y-2 pl-5 text-sm text-label">
          <li>Enquanto a reserva de emergência não estiver completa, todo o aporte vai para ela.</li>
          <li>Depois, o valor é dividido entre as classes que estão mais abaixo do alvo do seu perfil.</li>
          <li>
            Em ações, só entram as com veredito &quot;comprar&quot;. A prioridade é nota × margem de segurança, preferindo setores
            que você ainda não tem.
          </li>
          <li>No começo, cada ação fica com no máximo 20% das suas ações; cada setor, com 30%.</li>
          <li>
            Em FIIs, vale o mesmo: só os com veredito &quot;comprar&quot;, cada fundo com no máximo 20% dos seus FIIs e cada tipo
            (papel ou tijolo) com 60%.
          </li>
          <li>
            Em ETFs, a fatia é dividida em partes iguais entre os seus favoritos (★ no Explorar), desde que não estejam reprovados
            em liquidez.
          </li>
          <li>O app nunca sugere vender para rebalancear. O equilíbrio vem dos próximos aportes.</li>
        </ol>
      </Card>
    </div>
  );
}

function plural(count: number, one: string, many: string): string {
  return count === 1 ? `1 ${one}` : `${count} ${many}`;
}

function RegisteredNotice({ result }: { result: RegisterPlanOut }) {
  const purchases = result.transactions.length;
  const holdings = result.holdings.length;
  return (
    <div className="rounded-2xl border border-good/30 bg-good-soft px-5 py-4 text-sm text-good">
      Registrado: {plural(purchases, "compra", "compras")} e {plural(holdings, "aplicação", "aplicações")}.{" "}
      {purchases > 0 && (
        <Link href="/carteira" className="font-semibold underline">
          Ver carteira →
        </Link>
      )}{" "}
      {holdings > 0 && (
        <Link href="/renda-fixa" className="font-semibold underline">
          Ver renda fixa →
        </Link>
      )}
    </div>
  );
}

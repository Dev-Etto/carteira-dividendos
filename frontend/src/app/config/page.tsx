"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { DecimalInput, IntegerInput, MoneyInput, PercentInput, type TextInputProps } from "@/components/inputs";
import { Button, Card, ErrorBox, Field, inputCls, Loading, PageHeader } from "@/components/ui";
import { api, type AllocationItem, type Methods, type ProfileOut, type RuleConfigItem, type SyncStatus } from "@/lib/api/client";
import { CLASS_LABEL, num, PROFILE_LABEL } from "@/lib/format";
import { useApi } from "@/lib/useApi";
import { checkDecimal, checkInteger, checkMoney, checkPercent, type Checked } from "@/lib/validation";

const STEP_LABEL: Record<string, string> = {
  universo: "Lista de ativos",
  macro: "Selic, CDI e IPCA (Banco Central)",
  tesouro: "Tesouro Direto",
  cvm: "Balanços (CVM)",
  fiis: "Informes de FIIs (CVM)",
  etfs: "Patrimônio dos ETFs (CVM)",
  mercado: "Preços e proventos",
  avaliacoes: "Avaliações",
};

const RULE_LABEL: Record<string, string> = {
  yield_alvo: "Yield-alvo do preço-teto (%)",
  yield_alvo_exigente: "Yield-alvo exigente (%)",
  margem_ok: "Margem de segurança desejada (%)",
  proventos_anos_ok: "Anos seguidos pagando (ideal)",
  proventos_anos_min: "Anos seguidos pagando (mínimo)",
  roe_ok: "ROE ideal (%)",
  roe_min: "ROE mínimo (%)",
  divida_ok: "Dívida/EBITDA ideal",
  divida_max: "Dívida/EBITDA máximo",
  liquidez_ok: "Liquidez diária ideal (R$)",
  liquidez_min: "Liquidez diária mínima (R$)",
  nota_comprar: "Nota mínima para comprar",
  nota_evitar: "Nota abaixo da qual evitar",
  fii_pl_min: "Patrimônio mínimo (R$)",
  fii_liquidez_min: "Liquidez diária mínima (R$)",
  fii_anos_min: "Anos de funcionamento (mínimo)",
  fii_pvp_papel_min: "Papel: P/VP mínimo ideal",
  fii_pvp_papel_max: "Papel: P/VP máximo",
  fii_pvp_papel_atencao: "Papel: P/VP de atenção",
  fii_pvp_tijolo_min: "Tijolo: P/VP mínimo ideal",
  fii_pvp_tijolo_max: "Tijolo: P/VP máximo",
  fii_pvp_tijolo_atencao: "Tijolo: P/VP de atenção",
  fii_estabilidade_ok: "Rendimentos 12m ÷ anteriores, ideal (%)",
  fii_estabilidade_min: "Rendimentos 12m ÷ anteriores, mínimo (%)",
  fii_spread_papel_tolerancia: "Papel: tolerância abaixo do CDI líquido (p.p.)",
  fii_spread_papel_estresse: "Papel: spread que indica estresse (p.p.)",
  fii_spread_tijolo_ok: "Tijolo: spread ideal sobre a NTN-B (p.p.)",
  fii_credito_ok: "Papel: maior crédito, ideal (% do PL)",
  fii_credito_max: "Papel: maior crédito, máximo (% do PL)",
  fii_imovel_ok: "Tijolo: maior imóvel, ideal (% da receita)",
  fii_imovel_max: "Tijolo: maior imóvel, máximo (% da receita)",
  fii_imoveis_ok: "Tijolo: número de imóveis (ideal)",
  fii_imoveis_min: "Tijolo: número de imóveis (mínimo)",
  fii_vacancia_ok: "Tijolo: vacância ideal (%)",
  fii_vacancia_max: "Tijolo: vacância máxima (%)",
  fii_taxa_adm_ok: "Taxa de administração ideal (% a.a.)",
  fii_taxa_adm_max: "Taxa de administração máxima (% a.a.)",
  etf_liquidez_ok: "Liquidez diária ideal (R$)",
  etf_liquidez_min: "Liquidez diária mínima (R$)",
  etf_pl_ok: "Patrimônio ideal (R$)",
  etf_pl_min: "Patrimônio mínimo (R$)",
  etf_taxa_adm_ok: "Taxa de administração ideal (% a.a.)",
  etf_taxa_adm_max: "Taxa de administração máxima (% a.a.)",
  bazin_yield_alvo: "Yield mínimo dos últimos 12 meses (%)",
  bazin_yield_venda: "Yield em que o Bazin venderia (%)",
  bazin_anos_pagando: "Anos seguidos pagando (mínimo)",
  bazin_divida_pl_max: "Dívida líquida ÷ patrimônio máxima",
  graham_receita_min: "Receita anual mínima (R$)",
  graham_liquidez_corrente_min: "Liquidez corrente mínima",
  graham_anos_lucro: "Anos seguidos com lucro (mínimo)",
  graham_anos_proventos: "Anos seguidos pagando (mínimo)",
  graham_crescimento_min: "Crescimento mínimo do lucro (% a.a.)",
  graham_pl_max: "P/L máximo fixo",
  graham_pl_ligado_juros: "P/L máximo ligado ao juro real (1 = sim, 0 = usa o fixo)",
  graham_pl_x_pvp_max: "P/L × P/VP máximo",
};

/** Seções da tela de limites. Cada uma, menos a das ações pelo Barsi, junta as chaves de um prefixo. */
const PREFIXED_SECTIONS = [
  { title: "Ações pelo Bazin", prefix: "bazin_" },
  { title: "Ações pelo Graham", prefix: "graham_" },
  { title: "FIIs", prefix: "fii_" },
  { title: "ETFs", prefix: "etf_" },
];
const RULE_SECTIONS = [
  {
    title: "Ações pelo Barsi",
    matches: (key: string) => !PREFIXED_SECTIONS.some((s) => key.startsWith(s.prefix)),
  },
  ...PREFIXED_SECTIONS.map((s) => ({ title: s.title, matches: (key: string) => key.startsWith(s.prefix) })),
];

/** Limites guardados como fração (0,06) que a tela mostra e recebe em porcentagem (6). */
const PERCENT_RULES = new Set([
  "yield_alvo",
  "yield_alvo_exigente",
  "margem_ok",
  "roe_ok",
  "roe_min",
  "fii_estabilidade_ok",
  "fii_estabilidade_min",
  "fii_spread_papel_tolerancia",
  "fii_spread_papel_estresse",
  "fii_spread_tijolo_ok",
  "fii_credito_ok",
  "fii_credito_max",
  "fii_imovel_ok",
  "fii_imovel_max",
  "fii_vacancia_ok",
  "fii_vacancia_max",
  "fii_taxa_adm_ok",
  "fii_taxa_adm_max",
  "etf_taxa_adm_ok",
  "etf_taxa_adm_max",
  "bazin_yield_alvo",
  "bazin_yield_venda",
  "graham_crescimento_min",
]);

/** Limites em reais (liquidez e patrimônio). */
const MONEY_RULES = new Set([
  "liquidez_ok",
  "liquidez_min",
  "fii_pl_min",
  "fii_liquidez_min",
  "etf_liquidez_ok",
  "etf_liquidez_min",
  "etf_pl_ok",
  "etf_pl_min",
  "graham_receita_min",
]);

/** Limites que só fazem sentido inteiros (anos, número de imóveis, nota). */
const INTEGER_RULES = new Set([
  "proventos_anos_ok",
  "proventos_anos_min",
  "nota_comprar",
  "nota_evitar",
  "fii_anos_min",
  "fii_imoveis_ok",
  "fii_imoveis_min",
  "bazin_anos_pagando",
  "graham_anos_lucro",
  "graham_anos_proventos",
  "graham_pl_ligado_juros",
]);

const MAX_SCORE = 100;
const MAX_PERCENT = 100;

type RuleInput = { Input: (props: TextInputProps) => React.ReactNode; check: (text: string) => Checked<number> };

const RULE_INPUTS = {
  percent: { Input: PercentInput, check: (text: string) => checkPercent(text) },
  money: { Input: MoneyInput, check: (text: string) => checkMoney(text) },
  integer: { Input: IntegerInput, check: (text: string) => checkInteger(text) },
  score: { Input: IntegerInput, check: (text: string) => checkInteger(text, { max: MAX_SCORE }) },
  decimal: { Input: DecimalInput, check: (text: string) => checkDecimal(text) },
} satisfies Record<string, RuleInput>;

/** Campo e validação de cada limite, pelo tipo do valor. */
function ruleInput(key: string): RuleInput {
  if (PERCENT_RULES.has(key)) return RULE_INPUTS.percent;
  if (MONEY_RULES.has(key)) return RULE_INPUTS.money;
  if (key.startsWith("nota_")) return RULE_INPUTS.score;
  if (INTEGER_RULES.has(key)) return RULE_INPUTS.integer;
  return RULE_INPUTS.decimal;
}

/** Valor da regra como o usuário vê: em % para as frações, com vírgula decimal e sem separador de milhar. */
function ruleText(key: string, value: number): string {
  const shown = PERCENT_RULES.has(key) ? value * 100 : value;
  return shown.toLocaleString("pt-BR", { maximumFractionDigits: 6, useGrouping: false });
}

/** Converte o texto digitado de volta para o valor guardado pela API; null se não for número. */
function ruleValue(key: string, text: string): number | null {
  const n = ruleInput(key).check(text).value;
  if (n === null) return null;
  return PERCENT_RULES.has(key) ? n / 100 : n;
}

export default function Config() {
  const [methodsVersion, setMethodsVersion] = useState(0);
  return (
    <div className="space-y-6">
      <PageHeader title="Configurações" subtitle="Dados do mercado, seu perfil, a divisão da carteira e os limites das regras." />
      <div className="grid items-start gap-5 lg:grid-cols-[7fr_5fr]">
        <SyncCard />
        <div className="space-y-5">
          <ProfileCard />
          <MethodsCard onSaved={() => setMethodsVersion((v) => v + 1)} />
          <AllocationCard key={methodsVersion} />
        </div>
      </div>
      <RulesCard />
    </div>
  );
}

type SyncRun = SyncStatus["runs"][number];

const RUN_CLASS: Record<SyncRun["status"], string> = { ok: "text-good", error: "text-bad", running: "text-muted" };

function runLabel(r: SyncRun): string {
  if (r.status === "ok") return `ok · ${r.rows} linhas`;
  if (r.status === "error") return `erro: ${String(r.error).slice(0, 120)}`;
  return "rodando…";
}

function SyncCard() {
  const { data, reload } = useApi<SyncStatus>("/api/sync/status");
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    if (!data?.running) return;
    const id = setInterval(() => void reload(), 2500);
    return () => clearInterval(id);
  }, [data?.running, reload]);
  async function start() {
    setErr(null);
    try {
      await api.post("/api/sync");
      void reload();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    }
  }
  return (
    <Card
      title="Dados do mercado"
      actions={
        <Button onClick={start} disabled={data?.running}>
          {data?.running ? `Atualizando: ${STEP_LABEL[data.step ?? ""] ?? "…"}` : "Atualizar dados agora"}
        </Button>
      }
    >
      <p className="mb-3 text-sm text-muted">
        A primeira atualização baixa vários anos de balanços e preços e pode levar alguns minutos. Depois disso, o app atualiza
        sozinho todo dia às 19h enquanto a API estiver rodando. Para cotações em tempo real, coloque seu token gratuito da brapi
        no arquivo <code className="rounded bg-neutral-soft px-1.5 text-[13px]">backend/.env</code>.
      </p>
      {err && <ErrorBox error={err} />}
      {data && data.runs.length > 0 && (
        <ul className="divide-y divide-line border-t border-line text-sm">
          {data.runs.map((r, i) => (
            <li key={i} className="flex flex-wrap justify-between gap-2 py-2.5">
              <span>{STEP_LABEL[r.source] ?? r.source}</span>
              <span className={`font-semibold tabular-nums ${RUN_CLASS[r.status]}`}>{runLabel(r)}</span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function ProfileCard() {
  const { data } = useApi<ProfileOut>("/api/perfil");
  if (!data) return null;
  return (
    <Card
      title="Seu perfil"
      actions={
        <Link href="/onboarding" className="text-sm font-semibold text-accent">
          refazer questionário →
        </Link>
      }
    >
      <p className="text-sm text-ink">
        {data.onboarded ? `${PROFILE_LABEL[data.risk_profile]}: ${data.risk_description}` : "Ainda não definido."}
      </p>
    </Card>
  );
}

/** Metodologias: uma para escolher as ações e outra para dividir a carteira. */
function MethodsCard({ onSaved }: { onSaved: () => void }) {
  const methods = useApi<Methods>("/api/metodos");
  const profile = useApi<ProfileOut>("/api/perfil");
  const [choice, setChoice] = useState<{ selection_method?: string; allocation_method?: string }>({});
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  if (!methods.data || !profile.data) return null;
  const selection = choice.selection_method ?? profile.data.selection_method;
  const allocation = choice.allocation_method ?? profile.data.allocation_method;
  const pickedSelection = methods.data.selection.find((m) => m.key === selection);
  const pickedAllocation = methods.data.allocation.find((m) => m.key === allocation);
  async function save() {
    setErr(null);
    setMsg(null);
    try {
      await api.put("/api/perfil/metodos", { selection_method: selection, allocation_method: allocation });
      setChoice({});
      await profile.reload();
      onSaved();
      setMsg("Metodologias salvas. Vereditos e recomendações já seguem a escolha.");
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    }
  }
  return (
    <Card title="Metodologias" help="metodologias">
      <div className="space-y-4">
        <Field label="Para escolher as ações">
          <select
            className={inputCls}
            value={selection}
            onChange={(e) => setChoice((c) => ({ ...c, selection_method: e.target.value }))}
          >
            {methods.data.selection.map((m) => (
              <option key={m.key} value={m.key}>
                {m.label} ({m.author})
              </option>
            ))}
          </select>
        </Field>
        {pickedSelection && <p className="text-[13px] text-muted">{pickedSelection.summary}</p>}
        <Field label="Para dividir a carteira">
          <select
            className={inputCls}
            value={allocation}
            onChange={(e) => setChoice((c) => ({ ...c, allocation_method: e.target.value }))}
          >
            {methods.data.allocation.map((m) => (
              <option key={m.key} value={m.key}>
                {m.label}
              </option>
            ))}
          </select>
        </Field>
        {pickedAllocation && <p className="text-[13px] text-muted">{pickedAllocation.summary}</p>}
        <p className="text-[13px] text-subtle">Trocar a divisão substitui a divisão-alvo abaixo pela sugerida pelo método.</p>
        <div className="flex items-center gap-3">
          <Button onClick={() => void save()}>Salvar metodologias</Button>
          {msg && <span className="text-sm text-good">{msg}</span>}
        </div>
        {err && <p className="text-sm text-bad">{err}</p>}
      </div>
    </Card>
  );
}

/** Divisão-alvo. Os campos guardam o texto digitado e só viram número no total e no envio, para não perder "12," no meio da digitação. */
function AllocationCard() {
  const { data, loading } = useApi<AllocationItem[]>("/api/alocacao");
  const [edits, setEdits] = useState<Record<string, string>>({});
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  if (loading && !data) return <Loading />;
  if (!data) return null;
  const cur = data.map((i) => {
    const typed = edits[i.asset_class];
    const check = typed === undefined ? { value: i.weight_pct, error: null } : checkPercent(typed, { max: MAX_PERCENT });
    return { ...i, text: typed ?? num(i.weight_pct, 0), ...check };
  });
  const valid = cur.every((i) => i.value !== null);
  const total = Math.round(cur.reduce((s, i) => s + (i.value ?? 0), 0) * 100) / 100;
  const ok = valid && Math.abs(total - 100) <= 0.01;
  async function save() {
    setErr(null);
    setMsg(null);
    const body: AllocationItem[] = cur.map((i) => ({ asset_class: i.asset_class, weight_pct: i.value ?? 0 }));
    try {
      await api.put("/api/alocacao", body);
      setMsg("Divisão salva.");
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    }
  }
  return (
    <Card title="Divisão-alvo da carteira (%)" help="diversificacao">
      <div className="grid gap-3 sm:grid-cols-4">
        {cur.map((i) => (
          <Field key={i.asset_class} label={CLASS_LABEL[i.asset_class] ?? i.asset_class} error={i.error}>
            <PercentInput value={i.text} onValueChange={(text) => setEdits((s) => ({ ...s, [i.asset_class]: text }))} />
          </Field>
        ))}
      </div>
      <div className="mt-3 flex items-center gap-3">
        <Button onClick={save} disabled={!ok}>
          Salvar
        </Button>
        <span className={`text-sm ${ok ? "text-muted" : "text-bad"}`}>
          {valid ? `Total: ${num(total, total % 1 ? 2 : 0)}%` : "Preencha todas as classes"}
        </span>
        {msg && <span className="text-sm text-good">{msg}</span>}
      </div>
      {err && (
        <div className="mt-3">
          <ErrorBox error={err} />
        </div>
      )}
    </Card>
  );
}

function RulesCard() {
  const { data, reload } = useApi<RuleConfigItem[]>("/api/regras");
  const [edits, setEdits] = useState<Record<string, string>>({});
  const [confirmReset, setConfirmReset] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  if (!data) return null;
  const rules = data;
  const shown = rules.filter((r) => RULE_LABEL[r.key]);

  async function send(body: Record<string, number>) {
    setErr(null);
    setMsg(null);
    try {
      await api.put("/api/regras", body);
      setEdits({});
      void reload();
      setMsg("Regras salvas e ativos reavaliados.");
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    }
  }

  const invalid = Object.entries(edits).some(([k, v]) => ruleValue(k, v) === null);

  function save() {
    if (invalid) return;
    void send(Object.fromEntries(Object.entries(edits).map(([k, v]) => [k, ruleValue(k, v) ?? 0])));
  }

  function reset() {
    setConfirmReset(false);
    void send(Object.fromEntries(rules.map((r) => [r.key, r.default])));
  }

  return (
    <Card title="Limites das regras" help="veredito">
      <p className="mb-4 text-sm text-muted">
        Os padrões seguem o método Barsi nas ações e um filtro de segurança nos FIIs. Mude com cuidado: regras mais frouxas
        aprovam mais ativos, mas com mais risco.
      </p>
      <div className="space-y-5">
        {RULE_SECTIONS.map((section) => (
          <section key={section.title} className="border-t border-line pt-4">
            <h3 className="mb-3 text-[15px] font-bold text-ink">{section.title}</h3>
            <div className="grid gap-x-4 gap-y-3 sm:grid-cols-2 lg:grid-cols-4">
              {shown
                .filter((r) => section.matches(r.key))
                .map((r) => (
                  <RuleField
                    key={r.key}
                    rule={r}
                    text={edits[r.key] ?? ruleText(r.key, r.value)}
                    onChange={(text) => setEdits((s) => ({ ...s, [r.key]: text }))}
                  />
                ))}
            </div>
          </section>
        ))}
      </div>
      <div className="mt-4 flex flex-wrap items-center gap-3">
        <Button onClick={save} disabled={!Object.keys(edits).length || invalid}>
          Salvar e reavaliar
        </Button>
        {confirmReset ? (
          <>
            <Button variant="ghost" onClick={reset}>
              Confirmar volta aos padrões
            </Button>
            <Button variant="ghost" onClick={() => setConfirmReset(false)}>
              Cancelar
            </Button>
          </>
        ) : (
          <Button variant="ghost" onClick={() => setConfirmReset(true)}>
            Voltar aos padrões
          </Button>
        )}
        {msg && <span className="text-sm text-good">{msg}</span>}
      </div>
      {err && (
        <div className="mt-3">
          <ErrorBox error={err} />
        </div>
      )}
    </Card>
  );
}

/** Um limite das regras, com o campo do tipo do valor e a mensagem de erro embaixo. Vazio também é erro. */
function RuleField({ rule, text, onChange }: { rule: RuleConfigItem; text: string; onChange: (text: string) => void }) {
  const { Input, check } = ruleInput(rule.key);
  const checked = check(text);
  const error = checked.value === null && !checked.error ? "Informe um valor." : checked.error;
  return (
    <Field
      label={RULE_LABEL[rule.key] ?? rule.key}
      hint={rule.value !== rule.default ? `padrão: ${ruleText(rule.key, rule.default)}` : undefined}
      error={error}
    >
      <Input value={text} onValueChange={onChange} />
    </Field>
  );
}

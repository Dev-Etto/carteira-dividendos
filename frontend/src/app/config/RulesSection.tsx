"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState } from "react";

import { DecimalInput, IntegerInput, MoneyInput, PercentInput, type TextInputProps } from "@/components/inputs";
import { Button, Card, ErrorBox, FieldRow, Help, Loading } from "@/components/ui";
import { api, type RuleConfigItem } from "@/lib/api/client";
import { configHref, GROUP_PARAM } from "@/lib/configSections";
import {
  checkRule,
  ruleDisplay,
  findGroup,
  groupFromParam,
  orderedGroups,
  pendingKeys,
  RULE_LABEL,
  ruleGroupOf,
  ruleKind,
  rulesBody,
  ruleText,
  sameRuleValue,
  selectionGroup,
  splitSubsections,
  type RuleGroup,
  type RuleKind,
} from "@/lib/rules";
import { saveStatus } from "@/lib/saveStatus";
import { useApi } from "@/lib/useApi";

import { errorText, SaveBar } from "./parts";

const INPUT: Record<RuleKind, (props: TextInputProps) => React.ReactNode> = {
  percent: PercentInput,
  money: MoneyInput,
  integer: IntegerInput,
  score: IntegerInput,
  decimal: DecimalInput,
};

/** Sub-abas dos grupos: a metodologia escolhida primeiro e marcada, com um ponto onde há alteração não salva. */
function GroupTabs({
  groups,
  active,
  mine,
  pendingByGroup,
}: {
  groups: RuleGroup[];
  active: string;
  mine: string;
  pendingByGroup: Record<string, number>;
}) {
  return (
    <nav aria-label="Grupos de limites" className="mb-4 flex gap-1 overflow-x-auto border-b border-line">
      {groups.map((g) => {
        const current = g.key === active;
        return (
          <Link
            key={g.key}
            href={configHref("regras", g.key)}
            replace
            scroll={false}
            aria-current={current ? "page" : undefined}
            className={`-mb-px inline-flex shrink-0 items-center gap-2 whitespace-nowrap border-b-2 px-3 pb-2.5 pt-1 text-sm font-semibold transition ${
              current ? "border-accent text-accent" : "border-transparent text-muted hover:text-ink"
            }`}
          >
            {g.title}
            {g.key === mine && (
              <span className="rounded-full bg-accent-soft px-2 py-0.5 text-[11px] font-semibold text-accent">sua</span>
            )}
            {(pendingByGroup[g.key] ?? 0) > 0 && (
              <span className="h-2 w-2 rounded-full bg-warn" aria-label="alterações não salvas" title="alterações não salvas" />
            )}
          </Link>
        );
      })}
    </nav>
  );
}

/** Um limite: rótulo, padrão, campo do tipo do valor e o atalho para voltar ao padrão quando difere dele. */
function RuleRow({
  rule,
  label,
  text,
  pending,
  onChange,
}: {
  rule: RuleConfigItem;
  label: string;
  text: string;
  pending: boolean;
  onChange: (text: string) => void;
}) {
  const Input = INPUT[ruleKind(rule.key)];
  const isDefault = sameRuleValue(rule.key, text, rule.default);
  return (
    <FieldRow
      label={label}
      description={
        <>
          Padrão: <span className="tabular-nums">{ruleDisplay(rule.key, rule.default)}</span>
          {pending && <span className="ml-2 font-semibold text-warn">· não salvo</span>}
        </>
      }
      error={checkRule(rule.key, text).error}
      footer={
        !isDefault && (
          <button
            type="button"
            className="text-[13px] font-semibold text-accent hover:underline"
            onClick={() => onChange(ruleText(rule.key, rule.default))}
          >
            Restaurar padrão
          </button>
        )
      }
    >
      <Input className="tabular-nums" value={text} onValueChange={onChange} />
    </FieldRow>
  );
}

/**
 * Limites das regras em sub-abas por grupo, com o da metodologia de seleção escolhida primeiro. As alterações
 * ficam guardadas ao trocar de aba; cada grupo salva só as suas, e "restaurar padrão" só preenche o campo.
 */
export function RulesSection({ selectionMethod, selectionName }: { selectionMethod: string; selectionName: string }) {
  const params = useSearchParams();
  const { data, error, reload } = useApi<RuleConfigItem[]>("/api/regras");
  const [edits, setEdits] = useState<Record<string, string>>({});
  const [saved, setSaved] = useState<{ group: string; text: string } | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  if (error && !data) return <ErrorBox error={error} onRetry={() => void reload()} />;
  if (!data) return <Loading />;

  const groups = orderedGroups(selectionMethod);
  const mine = selectionGroup(selectionMethod);
  const activeKey = groupFromParam(params.get(GROUP_PARAM), selectionMethod);
  const group = findGroup(activeKey);
  const stored = Object.fromEntries(data.map((r) => [r.key, r.value]));
  const pending = pendingKeys(edits, stored);
  const pendingByGroup = Object.fromEntries(groups.map((g) => [g.key, pending.filter((k) => ruleGroupOf(k) === g.key).length]));
  const groupPending = pending.filter((k) => ruleGroupOf(k) === group.key);
  const byKey = new Map(data.map((r) => [r.key, r]));
  const rules = data.filter((r) => RULE_LABEL[r.key] && ruleGroupOf(r.key) === group.key);
  const subsections = splitSubsections(rules.map((r) => ({ key: r.key, label: RULE_LABEL[r.key] ?? r.key })));
  const body = rulesBody(edits, groupPending);
  const textOf = (rule: RuleConfigItem) => edits[rule.key] ?? ruleText(rule.key, rule.value);
  const allDefault = rules.every((r) => sameRuleValue(r.key, textOf(r), r.default));

  function edit(key: string, text: string) {
    setSaved(null);
    setEdits((s) => ({ ...s, [key]: text }));
  }

  function discard() {
    setErr(null);
    setEdits((s) => Object.fromEntries(Object.entries(s).filter(([key]) => ruleGroupOf(key) !== group.key)));
  }

  function restoreGroup() {
    setSaved(null);
    setEdits((s) => ({ ...s, ...Object.fromEntries(rules.map((r) => [r.key, ruleText(r.key, r.default)])) }));
  }

  async function save() {
    if (!body) return;
    setErr(null);
    setSaved(null);
    setSaving(true);
    try {
      await api.put("/api/regras", body);
      await reload();
      discard();
      setSaved({ group: group.key, text: "Limites salvos e ativos reavaliados." });
    } catch (e) {
      setErr(errorText(e));
    }
    setSaving(false);
  }

  const problem = body ? null : "Corrija os campos marcados antes de salvar.";
  const savedText = saved?.group === group.key ? saved.text : null;

  return (
    <div>
      <GroupTabs groups={groups} active={group.key} mine={mine} pendingByGroup={pendingByGroup} />
      <Card>
        <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0 max-w-2xl flex-1">
            <h3 className="flex items-center gap-1.5 text-lg font-bold text-ink">
              {group.title}
              <Help slug="veredito" />
            </h3>
            <p className="mt-1 text-sm text-muted">{group.description}</p>
            {group.key === mine && (
              <p className="mt-1 text-[13px] text-subtle">É a sua metodologia de seleção ({selectionName}).</p>
            )}
          </div>
          <Button variant="ghost" onClick={restoreGroup} disabled={allDefault || saving}>
            Restaurar padrões do grupo
          </Button>
        </div>
        <div className="max-w-3xl space-y-6">
          {subsections.map((s) => (
            <section key={s.title ?? "geral"}>
              {s.title && (
                <h4 className="mb-1 border-b border-line pb-2 text-sm font-bold text-label">FIIs de {s.title.toLowerCase()}</h4>
              )}
              <div className="divide-y divide-line">
                {s.rules.map((r) => {
                  const rule = byKey.get(r.key);
                  if (!rule) return null;
                  return (
                    <div key={r.key} className="py-3.5">
                      <RuleRow
                        rule={rule}
                        label={r.label}
                        text={textOf(rule)}
                        pending={groupPending.includes(r.key)}
                        onChange={(text) => edit(r.key, text)}
                      />
                    </div>
                  );
                })}
              </div>
            </section>
          ))}
        </div>
        {err && (
          <div className="mt-4">
            <ErrorBox error={err} />
          </div>
        )}
        <SaveBar
          status={saveStatus(savedText, problem, groupPending.length)}
          dirty={groupPending.length > 0}
          canSave={groupPending.length > 0 && body !== null}
          saving={saving}
          onSave={() => void save()}
          onDiscard={discard}
          saveLabel="Salvar e reavaliar"
        />
      </Card>
      <p className="mt-3 text-[13px] text-subtle">
        Regras mais frouxas aprovam mais ativos, mas com mais risco. Salvar reavalia todos os ativos com os novos limites.
      </p>
    </div>
  );
}

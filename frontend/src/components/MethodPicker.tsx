"use client";

import type { Method, Methods } from "@/lib/api/client";
import { focusLabel, type MethodChoice } from "@/lib/methods";

const FOCUS_CLASS: Record<string, string> = { valorizacao: "bg-warn-soft text-warn" };
const DEFAULT_FOCUS_CLASS = "bg-neutral-soft text-muted";

function FocusTag({ focus }: { focus: string }) {
  const label = focusLabel(focus);
  if (!label) return null;
  return (
    <span
      className={`inline-flex h-[22px] items-center rounded-full px-2 text-xs font-semibold ${FOCUS_CLASS[focus] ?? DEFAULT_FOCUS_CLASS}`}
    >
      {label}
    </span>
  );
}

/** Um grupo de metodologias como cartões de rádio, com autor, foco e resumo de cada uma. */
function MethodOptions({
  name,
  legend,
  methods,
  value,
  onChange,
  columns = false,
}: {
  name: string;
  legend: string;
  methods: Method[];
  value: string;
  onChange: (key: string) => void;
  columns?: boolean;
}) {
  return (
    <fieldset>
      <legend className="mb-2 text-sm font-semibold text-label">{legend}</legend>
      <div className={`grid gap-3 ${columns ? "sm:grid-cols-2" : ""}`}>
        {methods.map((m) => (
          <label
            key={m.key}
            className={`flex cursor-pointer items-start gap-3 rounded-xl border p-4 text-ink transition ${
              value === m.key ? "border-accent bg-accent-soft ring-1 ring-accent" : "border-line-strong hover:bg-neutral-soft"
            }`}
          >
            <input
              type="radio"
              name={name}
              className="mt-1 accent-[var(--accent)]"
              checked={value === m.key}
              onChange={() => onChange(m.key)}
            />
            <span className="space-y-1">
              <span className="flex flex-wrap items-center gap-2">
                <strong className="text-[15px]">{m.label}</strong>
                <FocusTag focus={m.focus} />
              </span>
              {m.author && <span className="block text-[13px] text-subtle">{m.author}</span>}
              <span className="block text-sm text-muted">{m.summary}</span>
            </span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}

/** As duas escolhas do perfil: a metodologia de seleção de ações e a de divisão da carteira. */
export function MethodPicker({
  methods,
  value,
  onChange,
  columns = false,
}: {
  methods: Methods;
  value: MethodChoice;
  onChange: (choice: Partial<MethodChoice>) => void;
  columns?: boolean;
}) {
  return (
    <div className="space-y-5">
      <MethodOptions
        name="selection_method"
        legend="Para escolher as ações"
        methods={methods.selection}
        value={value.selection_method}
        onChange={(key) => onChange({ selection_method: key })}
        columns={columns}
      />
      <MethodOptions
        name="allocation_method"
        legend="Para dividir a carteira"
        methods={methods.allocation}
        value={value.allocation_method}
        onChange={(key) => onChange({ allocation_method: key })}
        columns={columns}
      />
    </div>
  );
}

"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type ReactNode } from "react";

import { GLOSSARIO_POR_SLUG } from "@/content/glossario";

export function PageHeader({ title, subtitle, children }: { title: string; subtitle?: string; children?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-[30px] font-bold leading-tight tracking-tight text-ink">{title}</h1>
        {subtitle && <p className="mt-1 max-w-3xl text-[15px] text-muted">{subtitle}</p>}
      </div>
      {children}
    </div>
  );
}

export function Card({
  title,
  help,
  children,
  className = "",
  actions,
}: {
  title?: string;
  help?: string;
  children: ReactNode;
  className?: string;
  actions?: ReactNode;
}) {
  return (
    <section className={`rounded-2xl border border-line bg-surface p-6 shadow-card ${className}`}>
      {(title || actions) && (
        <div className="mb-4 flex items-center justify-between gap-2">
          {title && (
            <h2 className="flex items-center gap-1.5 text-lg font-bold text-ink">
              {title}
              {help && <Help slug={help} />}
            </h2>
          )}
          {actions}
        </div>
      )}
      {children}
    </section>
  );
}

export function Stat({ label, value, hint, help }: { label: string; value: ReactNode; hint?: ReactNode; help?: string }) {
  return (
    <div>
      <div className="flex items-center gap-1 text-[13px] font-medium text-muted">
        {label}
        {help && <Help slug={help} />}
      </div>
      <div className="mt-1 text-2xl font-bold tabular-nums tracking-tight text-ink">{value}</div>
      {hint && <div className="mt-0.5 text-[13px] text-subtle">{hint}</div>}
    </div>
  );
}

const ICON_PATHS: Record<string, ReactNode> = {
  comprar: <path d="M3 8.5 L6.5 12 L13 4.5" />,
  aguardar: (
    <>
      <circle cx="8" cy="8" r="6" />
      <path d="M8 5 V8.5 L10 10" />
    </>
  ),
  neutro: <path d="M4 8 H12" />,
  evitar: <path d="M4.5 4.5 L11.5 11.5 M11.5 4.5 L4.5 11.5" />,
};

const NEUTRO = { label: "Neutro", cls: "bg-neutral-soft text-muted" };
const VERDICT: Record<string, { label: string; cls: string }> = {
  comprar: { label: "Comprar", cls: "bg-good-soft text-good" },
  aguardar: { label: "Aguardar", cls: "bg-warn-soft text-warn" },
  neutro: NEUTRO,
  evitar: { label: "Evitar", cls: "bg-bad-soft text-bad" },
};

/** Ícone do veredito, para a cor nunca ser o único sinal. */
function VerdictIcon({ verdict }: { verdict: string }) {
  return (
    <svg
      width="12"
      height="12"
      viewBox="0 0 16 16"
      aria-hidden="true"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.4"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {ICON_PATHS[verdict] ?? ICON_PATHS.neutro}
    </svg>
  );
}

export function VerdictBadge({ verdict }: { verdict?: string | null }) {
  if (!verdict) return <span className="text-xs text-subtle">sem avaliação</span>;
  const v = VERDICT[verdict] ?? NEUTRO;
  return (
    <span
      className={`inline-flex h-[26px] items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 text-[13px] font-semibold ${v.cls}`}
    >
      <VerdictIcon verdict={verdict} />
      {v.label}
    </span>
  );
}

/** Cor de um valor com sinal: verde se ≥ 0, vermelho se negativo, sem cor quando não há valor. */
export function signClass(v: number | null | undefined): string {
  if (v === null || v === undefined) return "";
  return v >= 0 ? "text-good" : "text-bad";
}

export type ScoreTone = "good" | "warn" | "neutral" | "bad";

const VERDICT_TONE: Record<string, ScoreTone> = { comprar: "good", aguardar: "warn", neutro: "neutral", evitar: "bad" };

/**
 * Tom da nota a partir do veredito. Os limites de nota são configuráveis no backend e o veredito
 * já os aplica, então a cor segue o veredito em vez de faixas fixas. Sem veredito, neutro.
 */
export function verdictTone(verdict?: string | null): ScoreTone {
  return VERDICT_TONE[verdict ?? ""] ?? "neutral";
}

const SCORE_STYLE: Record<ScoreTone, string> = {
  good: "bg-good-soft text-good",
  warn: "bg-warn-soft text-warn",
  neutral: "bg-neutral-soft text-muted",
  bad: "bg-bad-soft text-bad",
};

export function ScorePill({ score, verdict }: { score?: number | null; verdict?: string | null }) {
  if (score === null || score === undefined) return <span className="text-subtle">—</span>;
  return (
    <span
      className={`inline-flex h-7 min-w-[42px] items-center justify-center rounded-lg px-1.5 font-bold tabular-nums ${SCORE_STYLE[verdictTone(verdict)]}`}
    >
      {score}
    </span>
  );
}

/** Ação destrutiva com confirmação inline: o primeiro clique pede confirmação, o segundo executa. */
export function ConfirmAction({
  label,
  confirmLabel = "confirmar",
  onConfirm,
}: {
  label: string;
  confirmLabel?: string;
  onConfirm: () => void;
}) {
  const [asking, setAsking] = useState(false);
  if (!asking)
    return (
      <button type="button" className="text-xs text-bad hover:underline" onClick={() => setAsking(true)}>
        {label}
      </button>
    );
  return (
    <span className="inline-flex items-center gap-2 text-xs">
      <button
        type="button"
        className="font-semibold text-bad hover:underline"
        onClick={() => {
          setAsking(false);
          onConfirm();
        }}
      >
        {confirmLabel}
      </button>
      <button type="button" className="text-muted hover:underline" onClick={() => setAsking(false)}>
        cancelar
      </button>
    </span>
  );
}

const SEM_DADO = { icon: "–", cls: "bg-neutral-soft text-muted", label: "sem dado" };
const STATUS: Record<string, { icon: string; cls: string; label: string }> = {
  ok: { icon: "✓", cls: "bg-good-soft text-good", label: "atende" },
  warn: { icon: "!", cls: "bg-warn-soft text-warn", label: "atenção" },
  fail: { icon: "✕", cls: "bg-bad-soft text-bad", label: "não atende" },
  na: SEM_DADO,
};

export function StatusIcon({ status }: { status: string }) {
  const m = STATUS[status] ?? SEM_DADO;
  return (
    <span
      aria-label={m.label}
      title={m.label}
      className={`inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold ${m.cls}`}
    >
      {m.icon}
    </span>
  );
}

/** "?" que abre a explicação do glossário. */
export function Help({ slug }: { slug: string }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLSpanElement>(null);
  const t = GLOSSARIO_POR_SLUG[slug];
  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [open]);
  if (!t) return null;
  return (
    <span ref={ref} className="relative inline-flex">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-label={`O que é ${t.termo}?`}
        className="inline-flex h-4 w-4 items-center justify-center rounded-full border border-line text-[10px] font-semibold text-muted hover:border-accent hover:text-accent"
      >
        ?
      </button>
      {open && (
        <span className="absolute left-0 top-6 z-30 w-72 rounded-lg border border-line bg-surface p-3 text-left text-xs font-normal leading-relaxed text-ink shadow-lg">
          <span className="block font-semibold">{t.termo}</span>
          <span className="mt-1 block text-muted">{t.curto}</span>
          <span className="mt-2 block">{t.explicacao}</span>
          <Link href={`/aprender#${t.slug}`} className="mt-2 block font-medium text-accent hover:underline">
            Ver no glossário →
          </Link>
        </span>
      )}
    </span>
  );
}

export function Loading({ text = "Carregando…" }: { text?: string }) {
  return <div className="py-10 text-center text-sm text-muted">{text}</div>;
}

export function ErrorBox({ error, onRetry }: { error: string; onRetry?: () => void }) {
  return (
    <div className="rounded-xl border border-bad/30 bg-bad-soft p-4 text-sm text-bad">
      {error}
      {onRetry && (
        <button onClick={onRetry} className="ml-3 font-semibold underline">
          Tentar de novo
        </button>
      )}
    </div>
  );
}

export function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="rounded-2xl border border-dashed border-line-strong p-8 text-center">
      <div className="text-sm font-semibold text-ink">{title}</div>
      {children && <div className="mt-2 text-sm text-muted">{children}</div>}
    </div>
  );
}

export function Button({
  children,
  variant = "primary",
  className = "",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "ghost" | "danger" }) {
  const styles = {
    primary: "bg-accent text-white hover:bg-accent-strong disabled:bg-line disabled:text-subtle",
    ghost: "border border-line-strong bg-surface text-ink hover:bg-neutral-soft disabled:opacity-50",
    danger: "text-bad hover:bg-bad-soft",
  }[variant];
  return (
    <button
      {...props}
      className={`inline-flex h-[42px] items-center justify-center gap-2 whitespace-nowrap rounded-[10px] px-[18px] text-sm font-semibold transition ${styles} ${className}`}
    >
      {children}
    </button>
  );
}

export function Field({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-[13px] font-semibold text-label">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-[13px] text-subtle">{hint}</span>}
    </label>
  );
}

export const inputCls =
  "h-[42px] w-full rounded-[10px] border border-line-strong bg-surface px-3 text-[15px] text-ink outline-none focus:border-accent focus:ring-2 focus:ring-accent/20 disabled:bg-neutral-soft disabled:text-subtle";

export function ProgressBar({ value, max, className = "" }: { value: number; max: number; className?: string }) {
  const p = max > 0 ? Math.min(100, (100 * value) / max) : 0;
  return (
    <div className={`h-2 w-full overflow-hidden rounded-full bg-neutral-soft ${className}`}>
      <div className="h-full rounded-full bg-accent transition-all" style={{ width: `${p}%` }} />
    </div>
  );
}

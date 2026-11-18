"use client";

import { useMemo, useState } from "react";

import { Card, PageHeader } from "@/components/ui";
import { GLOSSARIO, TRILHA_INICIO } from "@/content/glossario";

const CATEGORIAS = ["básico", "ações", "setores", "fiis", "etfs", "renda fixa", "carteira"] as const;

const STEP_PREFIX = /^\d+\.\s*/;

export default function Aprender() {
  const [q, setQ] = useState("");
  const filtered = useMemo(
    () => GLOSSARIO.filter((t) => !q || `${t.termo} ${t.curto} ${t.explicacao}`.toLowerCase().includes(q.toLowerCase())),
    [q],
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title="Aprender"
        subtitle="Tudo o que aparece no app, explicado sem jargão. Os “?” espalhados pelas telas levam para cá."
      />

      <Card title="Comece aqui">
        <ol className="grid gap-3 md:grid-cols-5">
          {TRILHA_INICIO.map((p, i) => (
            <li key={p.slug}>
              <a
                href={`#${p.slug}`}
                className="flex h-full flex-col gap-1.5 rounded-xl border border-line bg-surface p-[18px] transition hover:border-accent"
              >
                <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-accent-soft text-sm font-bold text-accent">
                  {i + 1}
                </span>
                <span className="text-[15px] font-bold text-ink">{p.titulo.replace(STEP_PREFIX, "")}</span>
                <span className="text-[13px] text-muted">{p.texto}</span>
              </a>
            </li>
          ))}
        </ol>
      </Card>

      <label className="flex h-12 max-w-xl items-center gap-2.5 rounded-xl border border-line-strong bg-surface px-4 focus-within:border-accent focus-within:ring-2 focus-within:ring-accent/20">
        <svg
          width="18"
          height="18"
          viewBox="0 0 16 16"
          aria-hidden="true"
          className="shrink-0 text-subtle"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinecap="round"
        >
          <circle cx="7" cy="7" r="5" />
          <path d="M11 11 L14 14" />
        </svg>
        <span className="sr-only">Buscar um termo</span>
        <input
          className="w-full bg-transparent text-[15px] text-ink outline-none"
          placeholder="Buscar um termo (ex.: payout, data-com, FGC)"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
      </label>

      {CATEGORIAS.map((cat) => {
        const items = filtered.filter((t) => t.categoria === cat);
        if (!items.length) return null;
        return (
          <section key={cat}>
            <h2 className="mb-3 text-[13px] font-bold uppercase tracking-[0.06em] text-muted">{cat}</h2>
            <div className="grid gap-4 md:grid-cols-2">
              {items.map((t) => (
                <article key={t.slug} id={t.slug} className="rounded-2xl border border-line bg-surface p-5 shadow-card">
                  <h3 className="text-[17px] font-bold text-ink">{t.termo}</h3>
                  <p className="mt-2 font-semibold text-accent">{t.curto}</p>
                  <p className="mt-2 text-sm leading-relaxed text-label">{t.explicacao}</p>
                  {t.exemplo && (
                    <p className="mt-2 rounded-lg bg-neutral-soft px-2.5 py-2 text-[13px] text-muted">Exemplo: {t.exemplo}</p>
                  )}
                </article>
              ))}
            </div>
          </section>
        );
      })}
    </div>
  );
}

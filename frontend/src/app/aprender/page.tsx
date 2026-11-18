"use client";

import { useMemo, useState } from "react";

import { Card, inputCls, PageHeader } from "@/components/ui";
import { GLOSSARIO, TRILHA_INICIO } from "@/content/glossario";

const CATEGORIAS = ["básico", "ações", "setores", "fiis", "etfs", "renda fixa", "carteira"] as const;

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
          {TRILHA_INICIO.map((p) => (
            <li key={p.slug}>
              <a href={`#${p.slug}`} className="block h-full rounded-lg border border-line p-3 transition hover:border-accent">
                <div className="text-sm font-semibold text-ink">{p.titulo}</div>
                <div className="mt-1 text-xs text-muted">{p.texto}</div>
              </a>
            </li>
          ))}
        </ol>
      </Card>

      <input
        className={inputCls}
        placeholder="Buscar um termo (ex.: payout, data-com, FGC)"
        value={q}
        onChange={(e) => setQ(e.target.value)}
      />

      {CATEGORIAS.map((cat) => {
        const items = filtered.filter((t) => t.categoria === cat);
        if (!items.length) return null;
        return (
          <section key={cat}>
            <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted">{cat}</h2>
            <div className="grid gap-3 md:grid-cols-2">
              {items.map((t) => (
                <article key={t.slug} id={t.slug} className="rounded-xl border border-line bg-surface p-4">
                  <h3 className="text-sm font-semibold text-ink">{t.termo}</h3>
                  <p className="mt-1 text-sm font-medium text-accent">{t.curto}</p>
                  <p className="mt-2 text-sm leading-relaxed text-ink">{t.explicacao}</p>
                  {t.exemplo && <p className="mt-2 rounded-lg bg-neutral-soft p-2 text-xs text-muted">Exemplo: {t.exemplo}</p>}
                </article>
              ))}
            </div>
          </section>
        );
      })}
    </div>
  );
}

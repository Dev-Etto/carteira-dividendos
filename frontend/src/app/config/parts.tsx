"use client";

import { type ReactNode } from "react";

import { Button } from "@/components/ui";
import { type SaveStatus, type SaveTone } from "@/lib/saveStatus";

/** Título e descrição curta de uma seção das Configurações. */
export function SectionHeader({
  id,
  title,
  description,
  children,
}: {
  id?: string;
  title: string;
  description: string;
  children?: ReactNode;
}) {
  return (
    <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h2 id={id} className="text-xl font-bold tracking-tight text-ink">
          {title}
        </h2>
        <p className="mt-1 max-w-2xl text-sm text-muted">{description}</p>
      </div>
      {children}
    </div>
  );
}

const TONE_CLASS: Record<SaveTone, string> = {
  good: "text-good",
  warn: "text-warn",
  bad: "text-bad",
  muted: "text-subtle",
};

/**
 * Rodapé de um formulário de ajustes: estado das alterações à esquerda e ações à direita. Fica grudado
 * no pé da tela enquanto o formulário rola, para o "Salvar" estar sempre à mão.
 */
export function SaveBar({
  status,
  dirty,
  canSave,
  saving,
  onSave,
  onDiscard,
  saveLabel = "Salvar",
  extra,
}: {
  status: SaveStatus;
  dirty: boolean;
  canSave: boolean;
  saving: boolean;
  onSave: () => void;
  onDiscard: () => void;
  saveLabel?: string;
  extra?: ReactNode;
}) {
  return (
    <div className="sticky bottom-0 z-10 -mx-6 -mb-6 mt-6 flex flex-wrap items-center justify-between gap-3 rounded-b-2xl border-t border-line bg-surface px-6 py-4">
      <p role="status" className={`flex items-center gap-2 text-sm font-medium ${TONE_CLASS[status.tone]}`}>
        {dirty && <span aria-hidden="true" className="h-2 w-2 rounded-full bg-warn" />}
        {status.text}
      </p>
      <div className="flex flex-wrap items-center gap-2">
        {extra}
        {dirty && (
          <Button variant="ghost" onClick={onDiscard} disabled={saving}>
            Descartar
          </Button>
        )}
        <Button onClick={onSave} disabled={!canSave || saving}>
          {saving ? "Salvando…" : saveLabel}
        </Button>
      </div>
    </div>
  );
}

export function errorText(e: unknown): string {
  return e instanceof Error ? e.message : String(e);
}

"use client";

import { useState } from "react";

import { api } from "@/lib/api/client";

/** Estrela que marca o ETF como favorito: só os favoritos recebem a fatia de ETFs do aporte. */
export function FavoriteButton({ ticker, favorite, onChange }: { ticker: string; favorite: boolean; onChange: () => void }) {
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function toggle() {
    setBusy(true);
    setErr(null);
    try {
      await api.patch(`/api/ativos/${ticker}`, { favorite: !favorite });
      onChange();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  const label = favorite ? "Tirar dos favoritos" : "Marcar como favorito para o aporte";
  return (
    <button
      type="button"
      onClick={() => void toggle()}
      disabled={busy}
      aria-pressed={favorite}
      aria-label={label}
      title={err ?? label}
      className={`text-lg leading-none disabled:opacity-50 ${favorite ? "text-warn" : "text-muted hover:text-ink"}`}
    >
      {favorite ? "★" : "☆"}
    </button>
  );
}

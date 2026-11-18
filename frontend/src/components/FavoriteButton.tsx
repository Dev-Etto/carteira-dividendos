"use client";

import { useState } from "react";

import { api } from "@/lib/api/client";

const SIZE_CLS = {
  normal: "h-9 w-9 rounded-[10px] text-xl",
  large: "h-[52px] w-[52px] rounded-[14px] border text-[26px]",
};

const LARGE_TONE = { on: "border-warn/40 bg-warn-soft", off: "border-line-strong bg-surface" };

/**
 * Estrela que marca o ETF como favorito: só os favoritos recebem a fatia de ETFs do aporte.
 * `large` é a versão com moldura usada no topo da ficha.
 */
export function FavoriteButton({
  ticker,
  favorite,
  onChange,
  large = false,
}: {
  ticker: string;
  favorite: boolean;
  onChange: () => void;
  large?: boolean;
}) {
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
  const tone = favorite ? "text-warn" : "text-subtle hover:text-ink";
  const frame = large ? LARGE_TONE[favorite ? "on" : "off"] : "hover:bg-neutral-soft";
  return (
    <button
      type="button"
      onClick={() => void toggle()}
      disabled={busy}
      aria-pressed={favorite}
      aria-label={label}
      title={err ?? label}
      className={`inline-flex items-center justify-center leading-none transition disabled:opacity-50 ${SIZE_CLS[large ? "large" : "normal"]} ${frame} ${tone}`}
    >
      {favorite ? "★" : "☆"}
    </button>
  );
}

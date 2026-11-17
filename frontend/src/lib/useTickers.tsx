"use client";

import type { AssetRow } from "./api/client";
import { useApi } from "./useApi";

/** Tickers das ações e dos FIIs do universo, para autocompletar campos de ticker. */
export function useTickers(): AssetRow[] {
  return useApi<AssetRow[]>("/api/ativos").data ?? [];
}

/** datalist com os tickers; ligue ao input com `list={id}`. */
export function TickerOptions({ id, assets }: { id: string; assets: AssetRow[] }) {
  return (
    <datalist id={id}>
      {assets.map((a) => (
        <option key={a.ticker} value={a.ticker}>
          {a.name}
        </option>
      ))}
    </datalist>
  );
}

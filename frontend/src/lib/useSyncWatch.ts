"use client";

import { useEffect, useState } from "react";

import { api, type SyncStatus } from "./api/client";

const POLL_MS = 2500;

/**
 * Acompanha a coleta em segundo plano disparada por uma ação do usuário (ex.: cadastrar um ativo).
 * `watch(rótulo)` começa a consultar o status do sync; quando ele não está mais rodando (ou a consulta
 * falha), chama `onFinished` e volta a `watching = null`. Se nada estava rodando, termina na hora.
 */
export function useSyncWatch(onFinished: () => void) {
  const [watching, setWatching] = useState<string | null>(null);

  useEffect(() => {
    if (watching === null) return;
    let active = true;
    const timer = window.setInterval(() => void check(), POLL_MS);
    async function check() {
      const status = await api.get<SyncStatus>("/api/sync/status").catch(() => null);
      if (!active || status?.running) return;
      active = false;
      window.clearInterval(timer);
      setWatching(null);
      onFinished();
    }
    void check();
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [watching, onFinished]);

  return { watching, watch: setWatching };
}

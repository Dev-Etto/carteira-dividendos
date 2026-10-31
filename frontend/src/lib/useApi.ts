"use client";

import { useCallback, useEffect, useState } from "react";

import { api } from "./api/client";

type Loaded<T> = { path: string | null; data: T | null; error: string | null };

function errorMessage(e: unknown): string {
  return e instanceof Error ? e.message : String(e);
}

/**
 * Busca `path` na API e mantém o resultado.
 * O resultado guarda o path de origem: enquanto ele difere do path atual, a busca está em andamento,
 * e respostas de um path antigo são descartadas (ex.: trocar de ticker antes da resposta chegar).
 */
export function useApi<T>(path: string | null) {
  const [loaded, setLoaded] = useState<Loaded<T>>({ path: null, data: null, error: null });
  const [reloading, setReloading] = useState(false);

  const fetchInto = useCallback(async (target: string, isCurrent: () => boolean) => {
    try {
      const data = await api.get<T>(target);
      if (isCurrent()) setLoaded({ path: target, data, error: null });
    } catch (e) {
      if (isCurrent()) setLoaded((s) => ({ path: target, data: s.path === target ? s.data : null, error: errorMessage(e) }));
    }
  }, []);

  useEffect(() => {
    if (path === null) return;
    let current = true;
    void fetchInto(path, () => current);
    return () => {
      current = false;
    };
  }, [path, fetchInto]);

  const reload = useCallback(async () => {
    if (path === null) return;
    setReloading(true);
    setLoaded((s) => ({ ...s, error: null }));
    await fetchInto(path, () => true);
    setReloading(false);
  }, [path, fetchInto]);

  const setData = useCallback((data: T | null) => setLoaded((s) => ({ ...s, data })), []);

  const isCurrentPath = loaded.path === path;
  return {
    data: isCurrentPath ? loaded.data : null,
    error: isCurrentPath ? loaded.error : null,
    loading: path !== null && (!isCurrentPath || reloading),
    reload,
    setData,
  };
}

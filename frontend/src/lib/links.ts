const INVESTIDOR10_SECTION: Record<string, string> = { acao: "acoes", fii: "fiis", etf: "etfs" };

/** Página do ativo no Investidor10, para quem quer se aprofundar além do que o app mostra. */
export function investidor10Url(ticker: string, assetClass: string): string {
  const section = INVESTIDOR10_SECTION[assetClass] ?? "acoes";
  return `https://investidor10.com.br/${section}/${ticker.trim().toLowerCase()}/`;
}

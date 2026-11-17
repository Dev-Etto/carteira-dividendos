import { investidor10Url } from "@/lib/links";

/** Link externo para a página do ativo no Investidor10, em nova aba. */
export function Investidor10Link({
  ticker,
  assetClass,
  compact = false,
}: {
  ticker: string;
  assetClass: string;
  compact?: boolean;
}) {
  const style = compact
    ? "text-xs text-muted hover:text-accent"
    : "rounded-lg border border-line px-4 py-2 text-sm font-medium text-ink hover:bg-neutral-soft";
  return (
    <a
      href={investidor10Url(ticker, assetClass)}
      target="_blank"
      rel="noopener noreferrer"
      className={style}
      title={`Abrir ${ticker} no Investidor10 em nova aba`}
    >
      {compact ? "Investidor10 ↗" : "Ver no Investidor10 ↗"}
    </a>
  );
}

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
    ? "text-xs text-subtle hover:text-accent"
    : "inline-flex h-[42px] items-center whitespace-nowrap rounded-[10px] border border-line-strong bg-surface px-4 text-sm font-semibold text-ink hover:bg-neutral-soft";
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

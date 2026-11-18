import type { Filing } from "@/lib/api/client";
import { dateBr, FILING_LABEL } from "@/lib/format";

const CATEGORY_STYLE: Record<string, string> = {
  fato_relevante: "bg-warn-soft text-warn",
  aviso_acionistas: "bg-accent-soft text-accent",
};

/** Comunicados à CVM, do mais novo ao mais velho, com link para o documento original. */
export function FilingList({ filings, showTicker = false }: { filings: Filing[]; showTicker?: boolean }) {
  return (
    <ul className="divide-y divide-line border-t border-line">
      {filings.map((f) => (
        <li key={`${f.ticker}-${f.link}-${f.delivered_on}`} className="py-3">
          <div className="flex flex-wrap items-center gap-2 text-[13px]">
            <span className="tabular-nums text-subtle">{dateBr(f.delivered_on)}</span>
            {showTicker && <span className="font-semibold text-ink">{f.ticker}</span>}
            <span
              className={`inline-flex h-[22px] items-center rounded-full px-2 font-semibold ${CATEGORY_STYLE[f.category] ?? "bg-neutral-soft text-label"}`}
            >
              {FILING_LABEL[f.category] ?? f.category}
            </span>
          </div>
          <a href={f.link} target="_blank" rel="noopener noreferrer" className="mt-1 block text-sm text-ink hover:text-accent">
            {f.subject || f.kind || "Documento"} <span aria-hidden="true">↗</span>
          </a>
        </li>
      ))}
    </ul>
  );
}

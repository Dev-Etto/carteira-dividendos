import { brl, CLASS_LABEL, num } from "@/lib/format";

type Slice = { asset_class: string; value: number; current_pct: number; target_pct: number };

export function AllocationBars({ classes }: { classes: Slice[] }) {
  return (
    <div className="space-y-5">
      {classes.map((c) => {
        const gap = c.target_pct - c.current_pct;
        return (
          <div key={c.asset_class}>
            <div className="mb-2 flex items-baseline justify-between gap-3 text-sm">
              <span className="font-bold text-ink">{CLASS_LABEL[c.asset_class]}</span>
              <span className="tabular-nums text-muted">
                <strong className="text-ink">{num(c.current_pct, 0)}%</strong> de {num(c.target_pct, 0)}% alvo · {brl(c.value)}
              </span>
            </div>
            <div className="relative h-2.5 w-full rounded-full bg-neutral-soft">
              <div className="h-full rounded-full bg-accent" style={{ width: `${Math.min(100, c.current_pct)}%` }} />
              <div
                className="absolute top-[-3px] h-[16px] w-0.5 bg-ink"
                style={{ left: `${Math.min(100, c.target_pct)}%` }}
                title={`alvo ${num(c.target_pct, 0)}%`}
              />
            </div>
            {gap > 2 && (
              <div className="mt-1.5 text-[13px] text-subtle">
                {num(gap, 0)} p.p. abaixo do alvo: recebe mais nos próximos aportes
              </div>
            )}
          </div>
        );
      })}
      <p className="text-[13px] text-subtle">
        A barra preta marca o alvo do seu perfil. O app corrige a diferença pelos aportes, sem vender nada.
      </p>
    </div>
  );
}

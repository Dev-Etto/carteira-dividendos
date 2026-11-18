"use client";

import { useState } from "react";

import { FavoriteButton } from "@/components/FavoriteButton";
import { PercentInput } from "@/components/inputs";
import { Button, Card, ErrorBox, Field, Help, inputCls, Stat } from "@/components/ui";
import { api, type AssetDetail } from "@/lib/api/client";
import { brl, brlCompact, dateBr, num, pct } from "@/lib/format";
import { checkPercent } from "@/lib/validation";

type Extras = Record<string, number | null | undefined>;

const MAX_FEE_PCT = 10;

/** Situação do ETF (só a liquidez reprova), o resumo do checklist e a estrela de favorito. */
export function EtfHeader({ data, onChange }: { data: AssetDetail; onChange: () => void }) {
  const avoid = data.verdict === "evitar";
  return (
    <div className="flex items-center gap-4">
      <FavoriteButton ticker={data.ticker} favorite={data.favorite} onChange={onChange} large />
      <div>
        <div className="flex items-center gap-2.5">
          <span
            className={`inline-flex h-[26px] items-center rounded-full px-2.5 text-[13px] font-semibold ${avoid ? "bg-bad-soft text-bad" : "bg-good-soft text-good"}`}
          >
            {avoid ? "Evitar" : "Apto"}
          </span>
          <span className="text-[13px] text-subtle">{data.favorite ? "favorito: recebe aportes" : "não é favorito"}</span>
          <Help slug="etf" />
        </div>
        <p className="mt-1.5 max-w-2xl text-base text-ink">{data.summary}</p>
      </div>
    </div>
  );
}

/** DY quando a fonte traz proventos; senão, o que o usuário informou sobre a distribuição. */
function distributionValue(data: AssetDetail): string {
  if (data.dividend_yield) return pct(data.dividend_yield);
  if (data.extras.distribui === true) return "distribui";
  if (data.extras.distribui === false) return "reinveste";
  return "—";
}

export function EtfStats({ data, ex }: { data: AssetDetail; ex: Extras }) {
  return (
    <>
      <Stat label="Preço atual" value={brl(data.price)} hint={data.price_at ? `em ${dateBr(data.price_at)}` : undefined} />
      <Stat
        label="Dividend yield 12m"
        help="etf-distribui"
        value={distributionValue(data)}
        hint={data.dividend_yield ? undefined : "o Yahoo não traz proventos de ETFs"}
      />
      <Stat label="Patrimônio" help="etf" value={brlCompact(ex.patrimonio)} />
      <Stat
        label="Taxa de administração"
        help="taxa-administracao"
        value={ex.taxa_adm_ano === null || ex.taxa_adm_ano === undefined ? "—" : pct(ex.taxa_adm_ano, 2)}
        hint="ao ano, informada por você"
      />
      <Stat label="Liquidez diária" help="liquidez" value={brlCompact(data.avg_daily_volume_brl)} />
    </>
  );
}

const DISTRIBUTES_OPTIONS = [
  { value: "", label: "Não sei" },
  { value: "sim", label: "Sim, repassa os proventos" },
  { value: "nao", label: "Não, reinveste" },
];

function distributesText(value: boolean | null | undefined): string {
  if (value === true) return "sim";
  if (value === false) return "nao";
  return "";
}

/**
 * O que o usuário informa sobre o ETF: a taxa de administração e se ele distribui proventos. Nenhuma
 * fonte gratuita estruturada traz esses dados (o Yahoo não informa proventos de ETFs brasileiros).
 */
export function EtfInfoCard({ data, ex, onChange }: { data: AssetDetail; ex: Extras; onChange: () => void }) {
  const current = ex.taxa_adm_ano;
  const [fee, setFee] = useState(current === null || current === undefined ? "" : num(current * 100, 2));
  const [distributes, setDistributes] = useState(distributesText(data.extras.distribui as boolean | null | undefined));
  const [err, setErr] = useState<string | null>(null);
  const feeCheck = checkPercent(fee, { max: MAX_FEE_PCT });

  async function save(body: { admin_fee: number | null; distributes: boolean | null }) {
    setErr(null);
    try {
      await api.patch(`/api/ativos/${data.ticker}`, body);
      onChange();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    }
  }

  function submit() {
    if (feeCheck.error) return;
    const adminFee = feeCheck.value === null ? null : feeCheck.value / 100;
    void save({ admin_fee: adminFee, distributes: distributes ? distributes === "sim" : null });
  }

  return (
    <Card title="Informado por você" help="etf-distribui" className="border-accent/30">
      <p className="mb-4 text-sm text-muted">
        Taxa e distribuição estão no site da gestora ou no regulamento do ETF. Deixe em branco o que não souber.
      </p>
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Taxa de administração (% ao ano)" error={feeCheck.error}>
          <PercentInput value={fee} onValueChange={setFee} placeholder="0,50" />
        </Field>
        <Field label="Distribui proventos?">
          <select className={inputCls} value={distributes} onChange={(e) => setDistributes(e.target.value)}>
            {DISTRIBUTES_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </Field>
      </div>
      <div className="mt-4">
        <Button onClick={submit} disabled={Boolean(feeCheck.error)}>
          Salvar
        </Button>
      </div>
      {err && (
        <div className="mt-3">
          <ErrorBox error={err} />
        </div>
      )}
    </Card>
  );
}

"use client";

import { useState } from "react";

import { FavoriteButton } from "@/components/FavoriteButton";
import { Button, Card, ErrorBox, Field, Help, inputCls, Stat } from "@/components/ui";
import { api, type AssetDetail } from "@/lib/api/client";
import { brl, brlCompact, dateBr, num, parseNumber, pct } from "@/lib/format";

type Extras = Record<string, number | null | undefined>;

const MAX_FEE_PCT = 10;

/** Situação do ETF (só a liquidez reprova), o resumo do checklist e a estrela de favorito. */
export function EtfHeader({ data, onChange }: { data: AssetDetail; onChange: () => void }) {
  const avoid = data.verdict === "evitar";
  return (
    <div className="flex items-start gap-3">
      <FavoriteButton ticker={data.ticker} favorite={data.favorite} onChange={onChange} />
      <div>
        <div className="flex items-center gap-2">
          <span
            className={`rounded-md px-2 py-0.5 text-xs font-medium ${avoid ? "bg-bad-soft text-bad" : "bg-good-soft text-good"}`}
          >
            {avoid ? "Evitar" : "Apto"}
          </span>
          <span className="text-xs text-muted">{data.favorite ? "favorito: recebe aportes" : "não é favorito"}</span>
          <Help slug="etf" />
        </div>
        <p className="mt-1 max-w-xl text-sm text-ink">{data.summary}</p>
      </div>
    </div>
  );
}

export function EtfStats({ data, ex }: { data: AssetDetail; ex: Extras }) {
  const reinvests = ex.rendimentos_12m === 0;
  return (
    <>
      <Stat label="Preço atual" value={brl(data.price)} hint={data.price_at ? `em ${dateBr(data.price_at)}` : undefined} />
      <Stat
        label="Dividend yield 12m"
        help="etf-distribui"
        value={reinvests ? "reinveste" : pct(data.dividend_yield)}
        hint={reinvests ? "não paga proventos" : undefined}
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

/** Valor em % digitado (ex.: "0,5") convertido para a fração que a API guarda; null se inválido. */
function feeFraction(text: string): number | null {
  const n = parseNumber(text);
  if (n === null || n < 0 || n > MAX_FEE_PCT) return null;
  return n / 100;
}

/** A taxa de administração não tem fonte gratuita estruturada: o usuário informa a do site da gestora. */
export function EtfFeeCard({ data, ex, onChange }: { data: AssetDetail; ex: Extras; onChange: () => void }) {
  const current = ex.taxa_adm_ano;
  const [text, setText] = useState(current === null || current === undefined ? "" : num(current * 100, 2));
  const [err, setErr] = useState<string | null>(null);

  async function save(adminFee: number | null) {
    setErr(null);
    try {
      await api.patch(`/api/ativos/${data.ticker}`, { admin_fee: adminFee });
      onChange();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    }
  }

  function submit() {
    if (!text.trim()) return void save(null);
    const fee = feeFraction(text);
    if (fee === null) return setErr(`Informe a taxa em % ao ano, entre 0 e ${MAX_FEE_PCT}.`);
    void save(fee);
  }

  return (
    <Card title="Taxa de administração" help="taxa-administracao">
      <p className="mb-3 text-sm text-muted">Está no site da gestora ou no regulamento do ETF. Deixe em branco para apagar.</p>
      <div className="flex items-end gap-3">
        <Field label="% ao ano">
          <input
            className={inputCls}
            inputMode="decimal"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="0,50"
          />
        </Field>
        <Button onClick={submit}>Salvar</Button>
      </div>
      {err && (
        <div className="mt-3">
          <ErrorBox error={err} />
        </div>
      )}
    </Card>
  );
}

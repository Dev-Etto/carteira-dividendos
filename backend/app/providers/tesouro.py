"""Tesouro Direto — CSV público de preços e taxas (Tesouro Transparente)."""

import io
from dataclasses import dataclass
from datetime import date

import pandas as pd

from app.providers.base import get_cached

CSV_URL = (
    "https://www.tesourotransparente.gov.br/ckan/dataset/df56aa42-484a-4a59-8184-7676580c81e3/"
    "resource/796d2059-14e9-44e3-80c9-2d9e30b405c1/download/precotaxatesourodireto.csv"
)


@dataclass
class BondQuote:
    name: str
    maturity: date
    date: date
    buy_rate: float | None
    sell_rate: float | None
    buy_price: float | None
    sell_price: float | None


def _num(v: object) -> float | None:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    s = str(v).strip().replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def parse_csv(content: bytes, last_days: int = 400) -> list[BondQuote]:
    df = pd.read_csv(io.BytesIO(content), sep=";", dtype=str, encoding="latin-1")
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    df["data_base"] = pd.to_datetime(df["data_base"], format="%d/%m/%Y")
    df["data_vencimento"] = pd.to_datetime(df["data_vencimento"], format="%d/%m/%Y")
    cutoff = df["data_base"].max() - pd.Timedelta(days=last_days)
    df = df[df["data_base"] >= cutoff]
    out = []
    for r in df.to_dict("records"):
        br, sr = _num(r.get("taxa_compra_manha")), _num(r.get("taxa_venda_manha"))
        out.append(
            BondQuote(
                name=str(r["tipo_titulo"]).strip(),
                maturity=r["data_vencimento"].date(),
                date=r["data_base"].date(),
                buy_rate=br / 100 if br is not None else None,
                sell_rate=sr / 100 if sr is not None else None,
                buy_price=_num(r.get("pu_compra_manha")),
                sell_price=_num(r.get("pu_venda_manha")),
            )
        )
    return out


async def fetch_bonds() -> list[BondQuote]:
    path = await get_cached(CSV_URL, max_age_hours=12, suffix=".csv")
    return parse_csv(path.read_bytes())

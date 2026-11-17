"""Cotações (brapi, plano grátis) e histórico de preços/proventos (Yahoo Finance via yfinance).

O yfinance não é oficial: se falhar, o app continua com o que já está no banco
e a ficha mostra a data do último dado. O plano grátis da brapi aceita uma requisição
por vez, por isso as cotações passam por `_brapi_lock`.
"""

import asyncio
from datetime import date

import pandas as pd
import yfinance as yf

from app.core.config import get_settings
from app.providers.base import DividendEvent, PricePoint, Quote, SplitInfo, client

BRAPI_URL = "https://brapi.dev/api/quote/{ticker}"

_brapi_lock = asyncio.Semaphore(1)


def parse_brapi(payload: dict, ticker: str) -> Quote | None:
    results = payload.get("results") or []
    if not results:
        return None
    r = results[0]
    price = r.get("regularMarketPrice")
    if price is None:
        return None
    return Quote(
        ticker=ticker,
        price=float(price),
        volume=float(r["regularMarketVolume"]) if r.get("regularMarketVolume") is not None else None,
        market_cap=float(r["marketCap"]) if r.get("marketCap") else None,
        name=r.get("longName") or r.get("shortName"),
        source="brapi",
    )


async def brapi_quote(ticker: str) -> Quote | None:
    token = get_settings().brapi_token
    if not token:
        return None
    async with _brapi_lock, client() as c:
        r = await c.get(BRAPI_URL.format(ticker=ticker), params={"token": token})
        if r.status_code != 200:
            return None
        return parse_brapi(r.json(), ticker)


def history_to_points(df: pd.DataFrame) -> tuple[list[PricePoint], list[DividendEvent], list[SplitInfo]]:
    prices: list[PricePoint] = []
    divs: list[DividendEvent] = []
    splits: list[SplitInfo] = []
    if df is None or df.empty:
        return prices, divs, splits
    for idx, row in df.iterrows():
        d = pd.Timestamp(str(idx)).date()
        close = row.get("Close")
        if pd.notna(close):
            vol = row.get("Volume")
            prices.append(PricePoint(d, float(close), float(vol) if pd.notna(vol) else 0.0))
        dv = row.get("Dividends", 0)
        if pd.notna(dv) and float(dv) > 0:
            divs.append(DividendEvent(d, float(dv)))
        sp = row.get("Stock Splits", 0)
        if pd.notna(sp) and float(sp) > 0:
            splits.append(SplitInfo(d, float(sp)))
    return prices, divs, splits


def _shares_outstanding(t: yf.Ticker) -> float | None:
    """Quantidade de ações. É opcional, e o fast_info do yfinance falha de vários jeitos, então qualquer erro vira None."""
    try:
        return float(t.fast_info.get("shares") or 0) or None
    except Exception:  # noqa: BLE001
        return None


def _yahoo_sync(ticker: str, start: date | None) -> tuple[pd.DataFrame, float | None]:
    t = yf.Ticker(f"{ticker}.SA")
    window = {"start": start.isoformat()} if start else {"period": "max"}
    return t.history(**window, auto_adjust=False, actions=True), _shares_outstanding(t)


async def yahoo_history(
    ticker: str, start: date | None = None
) -> tuple[list[PricePoint], list[DividendEvent], list[SplitInfo], float | None]:
    df, shares = await asyncio.to_thread(_yahoo_sync, ticker, start)
    prices, divs, splits = history_to_points(df)
    return prices, divs, splits, shares


def _yahoo_long_name_sync(ticker: str) -> str | None:
    """Nome completo no Yahoo; nos ETFs é a denominação social registrada na CVM. Opcional: qualquer erro vira None."""
    try:
        name = yf.Ticker(f"{ticker}.SA").info.get("longName")
    except Exception:  # noqa: BLE001
        return None
    return str(name) if name else None


async def yahoo_long_name(ticker: str) -> str | None:
    return await asyncio.to_thread(_yahoo_long_name_sync, ticker)

"""Infra comum dos providers: cliente HTTP com retry e cache de arquivos em disco."""

import hashlib
import time
import unicodedata
import zipfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Protocol

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.core.config import get_settings

DOWNLOAD_ERRORS = (httpx.HTTPError, zipfile.BadZipFile)
USER_AGENT = "carteira-dividendos/0.1 (uso pessoal; github.com/Dev-Etto)"


@dataclass
class Quote:
    ticker: str
    price: float
    volume: float | None
    market_cap: float | None
    name: str | None
    source: str


@dataclass
class PricePoint:
    date: date
    close: float
    volume: float


@dataclass
class DividendEvent:
    ex_date: date
    amount: float
    kind: str = "dividendo"


@dataclass
class SplitInfo:
    date: date
    ratio: float


class MarketDataProvider(Protocol):
    name: str

    async def quote(self, ticker: str) -> Quote | None: ...


def normalize(text: str) -> str:
    """minúsculas e sem acentos, para comparar descrições de contas da CVM."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower().strip()


def client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=httpx.Timeout(60.0, connect=15.0),
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
    )


RETRY_STATUS = {429, 500, 502, 503, 504}


def _is_transient(e: BaseException) -> bool:
    """Só vale tentar de novo em falha de rede ou erro temporário do servidor; 4xx não muda na segunda tentativa."""
    if isinstance(e, httpx.HTTPStatusError):
        return e.response.status_code in RETRY_STATUS
    return isinstance(e, httpx.TransportError)


@retry(
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception(_is_transient),
    reraise=True,
)
async def get_bytes(url: str, params: dict | None = None) -> bytes:
    async with client() as c:
        r = await c.get(url, params=params)
        r.raise_for_status()
        return r.content


async def get_cached(url: str, max_age_hours: float, suffix: str = "") -> Path:
    """Baixa um arquivo e guarda em data/cache; reaproveita enquanto for recente."""
    cache_dir = get_settings().cache_dir
    cache_dir.mkdir(parents=True, exist_ok=True)
    name = hashlib.sha1(url.encode()).hexdigest()[:16] + suffix
    path = cache_dir / name
    if path.exists() and (time.time() - path.stat().st_mtime) < max_age_hours * 3600:
        return path
    data = await get_bytes(url)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    tmp.replace(path)
    return path

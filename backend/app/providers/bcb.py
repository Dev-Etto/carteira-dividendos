"""Banco Central — API SGS (séries temporais). Fonte oficial e gratuita.

O endpoint /dados/ultimos/{n} aceita no máximo 20 valores, por isso a coleta pede por intervalo de datas
(séries diárias aceitam janelas de até 10 anos). Os valores chegam em % e são guardados em fração decimal.

Séries: selic_meta (432, meta Selic % a.a.), cdi (4389, CDI anualizado base 252, % a.a.),
ipca_12m (13522, IPCA acumulado em 12 meses, %).
"""

import json
from datetime import date, datetime, timedelta

from app.providers.base import get_bytes

SGS_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados"

SERIES = {
    "selic_meta": 432,
    "cdi": 4389,
    "ipca_12m": 13522,
}


def parse_sgs(payload: bytes) -> list[tuple[date, float]]:
    rows = json.loads(payload)
    out = []
    for r in rows:
        d = datetime.strptime(r["data"], "%d/%m/%Y").date()
        out.append((d, float(str(r["valor"]).replace(",", ".")) / 100))
    return out


async def fetch_series(name: str, days: int = 400, today: date | None = None) -> list[tuple[date, float]]:
    end = today or date.today()
    start = end - timedelta(days=days)
    data = await get_bytes(
        SGS_URL.format(code=SERIES[name]),
        params={"formato": "json", "dataInicial": f"{start:%d/%m/%Y}", "dataFinal": f"{end:%d/%m/%Y}"},
    )
    return parse_sgs(data)

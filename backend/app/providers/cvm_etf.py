"""CVM Dados Abertos — cadastro de classes de fundos, para o patrimônio dos ETFs.

O cadastro não traz o ticker. Mas a denominação social registrada na CVM é o nome que o Yahoo
mostra para o ETF (ex.: "ISHARES IBOVESPA CLASSE DE ÍNDICE - RESPONSABILIDADE LIMITADA"), então
a ligação ticker → CNPJ é feita pelo nome normalizado.
"""

import io
import re
import zipfile
from dataclasses import dataclass
from datetime import date

import pandas as pd

from app.providers.base import get_cached, normalize
from app.providers.cvm import only_digits

REGISTRO_URL = "https://dados.cvm.gov.br/dados/FI/CAD/DADOS/registro_fundo_classe.zip"
CLASSES_FILE = "registro_classe.csv"
INDEX_FUND_MARK = "indice"
ACTIVE_STATUS = "em funcionamento normal"


@dataclass
class IndexFund:
    cnpj: str
    name: str
    equity: float | None
    equity_date: date | None


def name_key(name: str) -> str:
    """Nome sem acentos, minúsculo e com espaços simples, para comparar o nome do Yahoo com o da CVM."""
    return re.sub(r"\s+", " ", normalize(name))


def _equity(value: object) -> float | None:
    """Patrimônio do CSV lido como texto; célula vazia (NaN) ou inválida vira None."""
    if not isinstance(value, str):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _equity_date(value: object) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def parse_index_funds(content: bytes) -> dict[str, IndexFund]:
    """Fundos de índice em funcionamento, indexados pelo nome normalizado."""
    zf = zipfile.ZipFile(io.BytesIO(content))
    if CLASSES_FILE not in zf.namelist():
        return {}
    with zf.open(CLASSES_FILE) as f:
        df = pd.read_csv(f, sep=";", encoding="latin-1", dtype=str)
    keys = df["Denominacao_Social"].fillna("").map(name_key)
    active = df["Situacao"].fillna("").map(normalize) == ACTIVE_STATUS
    funds = df[keys.str.contains(INDEX_FUND_MARK) & active].assign(key=keys)
    return {
        str(row["key"]): IndexFund(
            cnpj=only_digits(row["CNPJ_Classe"]),
            name=str(row["Denominacao_Social"]).strip(),
            equity=_equity(row["Patrimonio_Liquido"]),
            equity_date=_equity_date(row["Data_Patrimonio_Liquido"]),
        )
        for _, row in funds.iterrows()
    }


async def fetch_index_funds() -> dict[str, IndexFund]:
    path = await get_cached(REGISTRO_URL, max_age_hours=24, suffix=".zip")
    return parse_index_funds(path.read_bytes())

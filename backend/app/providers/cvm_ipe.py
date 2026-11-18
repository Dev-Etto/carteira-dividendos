"""CVM Dados Abertos — comunicados das companhias (IPE): fatos relevantes, comunicados ao mercado,
avisos aos acionistas e relatórios de proventos. O arquivo do ano traz todas as entregas; o app guarda
só estas categorias, que são as que mudam a tese de quem investe, e deixa de fora as de rotina
(posição de valores mobiliários, atas, estatuto)."""

import io
import zipfile
from dataclasses import dataclass
from datetime import date

import pandas as pd

from app.providers.base import get_cached, normalize
from app.providers.cvm import only_digits

IPE_URL = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/IPE/DADOS/ipe_cia_aberta_{year}.zip"
CATEGORIES = {
    "fato relevante": "fato_relevante",
    "comunicado ao mercado": "comunicado",
    "aviso aos acionistas": "aviso_acionistas",
    "relatorio proventos": "proventos",
}
"""Categoria da CVM (sem acentos, minúsculas) → chave guardada no app."""


@dataclass(frozen=True)
class Filing:
    cnpj: str
    protocol: str
    delivered_on: date
    category: str
    kind: str
    subject: str
    link: str


def _text(value: object) -> str:
    """Texto da célula; as vazias chegam do pandas como NaN (float)."""
    if not isinstance(value, str):
        return ""
    return value.strip()


def parse_ipe_zip(content: bytes, cnpjs: set[str]) -> list[Filing]:
    """Comunicados das empresas pedidas, nas categorias que o app guarda, na versão mais nova de cada protocolo."""
    zf = zipfile.ZipFile(io.BytesIO(content))
    with zf.open(zf.namelist()[0]) as f:
        df = pd.read_csv(f, sep=";", encoding="latin-1", dtype=str)
    df["cnpj"] = df["CNPJ_Companhia"].map(only_digits)
    df["category"] = df["Categoria"].map(lambda s: CATEGORIES.get(normalize(_text(s))))
    df = df[df["cnpj"].isin(cnpjs) & df["category"].notna()].copy()
    df["Versao"] = pd.to_numeric(df["Versao"], errors="coerce").fillna(1)
    df = df.sort_values("Versao").drop_duplicates("Protocolo_Entrega", keep="last")
    return [
        Filing(
            cnpj=_text(r.cnpj),
            protocol=_text(r.Protocolo_Entrega),
            delivered_on=date.fromisoformat(_text(r.Data_Entrega)[:10]),
            category=_text(r.category),
            kind=_text(r.Tipo),
            subject=_text(r.Assunto) or _text(r.Especie),
            link=_text(r.Link_Download),
        )
        for r in df.itertuples()
        if _text(r.Data_Entrega)
    ]


async def fetch_filings(year: int, cnpjs: set[str]) -> list[Filing]:
    path = await get_cached(IPE_URL.format(year=year), max_age_hours=12, suffix=".zip")
    return parse_ipe_zip(path.read_bytes(), cnpjs)

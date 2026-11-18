"""SUSEP — base estatística (SES): índice combinado das seguradoras.

A base completa é um ZIP de ~580 MB, atualizado mensalmente; o app guarda em cache por 30 dias e lê só a
DRE (quadro 23 do SES_Balanco) das seguradoras pedidas, em pedaços, sem carregar o arquivo inteiro.

Índice combinado = (sinistros ocorridos + custos de aquisição + outras receitas e despesas operacionais
+ resultado com resseguro + despesas administrativas + despesas com tributos) ÷ prêmios ganhos. A DRE da
SUSEP é acumulada no ano; os últimos 12 meses saem do acumulado do mês mais recente, mais o ano anterior
fechado, menos o acumulado do mesmo mês do ano anterior.

As companhias abertas (BB Seguridade, Caixa Seguridade, Porto) são holdings: a lista de seguradoras de cada
uma fica em data/seguradoras_susep.csv, mantida à mão, e o índice da holding soma os números delas.
"""

import zipfile
from dataclasses import dataclass
from typing import IO

import pandas as pd

from app.providers.base import get_cached

BASE_URL = "https://www2.susep.gov.br/download/estatisticas/BaseCompleta.zip"
BALANCE_MEMBER = "SES_Balanco.csv"
DRE_QUADRO = "23"
PREMIUMS = "4027"
EXPENSES = ("11232", "11237", "6202", "11238", "4069", "4070")
"""Sinistros ocorridos, custos de aquisição, outras receitas e despesas operacionais, resultado com resseguro,
despesas administrativas e despesas com tributos: vêm negativos quando são despesa."""
CHUNK_ROWS = 1_000_000
MONTHS = ("jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez")


@dataclass(frozen=True)
class CombinedRatio:
    ticker: str
    ratio_pct: float
    reference: str


def _number(values: pd.Series) -> pd.Series:
    """Valores no formato brasileiro ("1.234,56")."""
    return pd.to_numeric(values.str.replace(".", "", regex=False).str.replace(",", ".", regex=False), errors="coerce")


def read_dre(csv_file: IO[bytes], entities: set[str]) -> pd.DataFrame:
    """Linhas da DRE (prêmios e despesas do índice) das seguradoras pedidas, com o valor numérico."""
    wanted = {PREMIUMS, *EXPENSES}
    parts = []
    for chunk in pd.read_csv(csv_file, sep=";", encoding="latin-1", dtype=str, chunksize=CHUNK_ROWS):
        rows = chunk[
            chunk["coenti"].str.strip().isin(entities)
            & (chunk["quadro"].str.strip() == DRE_QUADRO)
            & chunk["cmpid"].str.strip().isin(wanted)
        ]
        parts.append(rows)
    dre = pd.concat(parts) if parts else pd.DataFrame(columns=["coenti", "damesano", "cmpid", "valor"])
    return dre.assign(coenti=dre["coenti"].str.strip(), cmpid=dre["cmpid"].str.strip(), v=_number(dre["valor"]))


def _ytd(dre: pd.DataFrame, entities: set[str], month: str) -> tuple[float, float]:
    """Prêmios ganhos e despesas do índice acumulados no ano até `month` (AAAAMM), somando as seguradoras."""
    rows = dre[dre["coenti"].isin(entities) & (dre["damesano"] == month)]
    premiums = float(rows.loc[rows["cmpid"] == PREMIUMS, "v"].sum())
    expenses = -float(rows.loc[rows["cmpid"].isin(EXPENSES), "v"].sum())
    return premiums, expenses


def last_twelve_months(dre: pd.DataFrame, entities: set[str], month: str) -> tuple[float, float]:
    """Prêmios e despesas dos 12 meses até `month`: acumulado do mês + ano anterior fechado − acumulado do
    mesmo mês do ano anterior. Em dezembro, o próprio acumulado já é o ano."""
    current = _ytd(dre, entities, month)
    year, mm = int(month[:4]), month[4:]
    if mm == "12":
        return current
    full = _ytd(dre, entities, f"{year - 1}12")
    same = _ytd(dre, entities, f"{year - 1}{mm}")
    return current[0] + full[0] - same[0], current[1] + full[1] - same[1]


def month_label(month: str) -> str:
    """202609 → "set/26"."""
    return f"{MONTHS[int(month[4:]) - 1]}/{month[2:4]}"


def combined_ratios(dre: pd.DataFrame, groups: dict[str, set[str]]) -> list[CombinedRatio]:
    """Índice combinado de cada holding nos últimos 12 meses, no mês mais recente com dados."""
    if dre.empty:
        return []
    month = str(dre["damesano"].max())
    out = []
    for ticker, entities in groups.items():
        premiums, expenses = last_twelve_months(dre, entities, month)
        if premiums > 0:
            out.append(CombinedRatio(ticker=ticker, ratio_pct=round(100 * expenses / premiums, 1), reference=month_label(month)))
    return out


def parse_base(content_path: str, groups: dict[str, set[str]]) -> list[CombinedRatio]:
    entities = set().union(*groups.values()) if groups else set()
    with zipfile.ZipFile(content_path) as zf, zf.open(BALANCE_MEMBER) as f:
        return combined_ratios(read_dre(f, entities), groups)


async def fetch_combined_ratios(groups: dict[str, set[str]]) -> list[CombinedRatio]:
    path = await get_cached(BASE_URL, max_age_hours=24 * 30, suffix=".zip")
    return parse_base(str(path), groups)

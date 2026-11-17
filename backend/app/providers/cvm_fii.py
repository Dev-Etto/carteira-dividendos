"""CVM Dados Abertos — informes mensal e trimestral de FIIs.

Mensal: cadastro (ISIN, início, negociação em bolsa, segmento), cotistas, patrimônio, valor
patrimonial da cota, taxa de administração e composição do ativo (crédito, imóveis, cotas de FII).
Trimestral: imóveis (área, vacância, participação na receita) e ativos financeiros (CRI, LCI...).

Os ZIPs trazem CSVs em latin-1 separados por ';', com valores em R$ e percentuais em fração.
Um mesmo mês pode ter várias versões do informe; fica a de maior número.
"""

import io
import re
import zipfile
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

import pandas as pd

from app.providers.base import get_cached
from app.providers.cvm import only_digits

MENSAL_URL = "https://dados.cvm.gov.br/dados/FII/DOC/INF_MENSAL/DADOS/inf_mensal_fii_{year}.zip"
TRIMESTRAL_URL = "https://dados.cvm.gov.br/dados/FII/DOC/INF_TRIMESTRAL/DADOS/inf_trimestral_fii_{year}.zip"

PAPER_COLUMNS = ("CRI", "CRI_CRA", "LCI", "LCI_LCA", "Letras_Hipotecarias", "LIG")
BRICK_COLUMNS = (
    "Direitos_Bens_Imoveis",
    "Terrenos",
    "Imoveis_Renda_Acabados",
    "Imoveis_Renda_Construcao",
    "Imoveis_Venda_Acabados",
    "Imoveis_Venda_Construcao",
    "Outros_Direitos_Reais",
    "Acoes_Sociedades_Atividades_FII",
    "Cotas_Sociedades_Atividades_FII",
)
FOF_COLUMNS = ("FII",)
CASH_COLUMNS = ("Disponibilidades", "Titulos_Publicos", "Titulos_Privados", "Fundos_Renda_Fixa")
CREDIT_TYPES = frozenset({"CRI/CRA", "LCI/LCA", "LIG"})
RENTAL_CLASS = "Imóveis para renda"
FINISHED_RENTAL_CLASS = "Imóveis para renda acabados"
MIN_CONSISTENT_AREA = 0.5
"""Fração mínima da área com vacância consistente para calcular a vacância do fundo."""
REVENUE_SHARE_TOLERANCE = 1.05
"""Soma máxima aceitável das participações dos imóveis na receita; acima disso o informe está inconsistente."""

FII_ISIN_KIND = "CTF"
"""No ISIN de cota de FII (ex.: BRMXRFCTF008), as posições 7 a 9 são CTF e as 4 letras do ticker vêm logo após o BR."""


@dataclass
class FiiMonthly:
    cnpj: str
    ref_date: date
    ticker: str
    name: str
    started_on: date | None
    listed: bool
    segment: str | None
    holders: int | None
    equity: float | None
    shares: float | None
    nav_per_share: float | None
    admin_fee: float | None
    paper: float
    brick: float
    fof: float
    cash: float


@dataclass
class FiiQuarterly:
    cnpj: str
    ref_date: date
    properties: int | None
    vacancy: float | None
    largest_property_share: float | None
    largest_credit_value: float | None


def ticker_from_isin(isin: object) -> str | None:
    code = str(isin or "").strip().upper()
    if len(code) != 12 or not code.startswith("BR") or code[6:9] != FII_ISIN_KIND:
        return None
    return f"{code[2:6]}11"


def _read(zf: zipfile.ZipFile, table: str, columns: Iterable[str] = ()) -> pd.DataFrame:
    """Tabela do ZIP (ex.: "geral" lê inf_mensal_fii_geral_2026.csv) com a coluna cnpj só com dígitos.
    Garante as colunas pedidas mesmo se o arquivo faltar."""
    pattern = re.compile(rf"_fii_{table}_\d{{4}}\.csv$")
    name = next((n for n in zf.namelist() if pattern.search(n)), None)
    required = ["CNPJ_Fundo_Classe", "Data_Referencia", "Versao", *columns]
    df = pd.DataFrame(columns=required)
    if name is not None:
        with zf.open(name) as f:
            df = pd.read_csv(f, sep=";", encoding="latin-1", dtype=str)
    df = df.reindex(columns=list(dict.fromkeys([*df.columns, *required])))
    return df.assign(cnpj=df["CNPJ_Fundo_Classe"].map(only_digits))


def _latest_version(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.assign(Versao=pd.to_numeric(df["Versao"], errors="coerce").fillna(0))
    keep = df["Versao"] == df.groupby(["cnpj", "Data_Referencia"])["Versao"].transform("max")
    return df[keep].drop_duplicates(["cnpj", "Data_Referencia"], keep="last")


Cell = str | float | None
"""Célula de um CSV lido como texto: string, NaN (float) quando vazia, ou None."""


def _text(value: Cell) -> str | None:
    if not isinstance(value, str):
        return None
    return value.strip() or None


def _number(value: Cell) -> float | None:
    text = _text(value)
    if text is None:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _day(value: Cell) -> date | None:
    text = _text(value)
    if text is None:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _composition(row: pd.Series) -> dict[str, float]:
    """Peso de crédito, imóveis, cotas de FII e caixa no ativo do fundo (somam 1 quando há ativo)."""
    groups = {"paper": PAPER_COLUMNS, "brick": BRICK_COLUMNS, "fof": FOF_COLUMNS, "cash": CASH_COLUMNS}
    totals = {key: sum(_number(row.get(col)) or 0.0 for col in cols) for key, cols in groups.items()}
    total = sum(totals.values())
    if total <= 0:
        return dict.fromkeys(groups, 0.0)
    return {key: value / total for key, value in totals.items()}


def _monthly_row(row: pd.Series) -> FiiMonthly:
    holders = _number(row.get("Total_Numero_Cotistas"))
    return FiiMonthly(
        cnpj=str(row["cnpj"]),
        ref_date=date.fromisoformat(str(row["Data_Referencia"])),
        ticker=str(row["ticker"]),
        name=_text(row.get("Nome_Fundo_Classe")) or str(row["ticker"]),
        started_on=_day(row.get("Data_Funcionamento")),
        listed=_text(row.get("Mercado_Negociacao_Bolsa")) == "S",
        segment=_text(row.get("Segmento_Atuacao")),
        holders=int(holders) if holders is not None else None,
        equity=_number(row.get("Patrimonio_Liquido")),
        shares=_number(row.get("Cotas_Emitidas")),
        nav_per_share=_number(row.get("Valor_Patrimonial_Cotas")),
        admin_fee=_number(row.get("Percentual_Despesas_Taxa_Administracao")),
        **_composition(row),
    )


def _current_fund(reports: list[FiiMonthly]) -> list[FiiMonthly]:
    """Quando o mesmo ISIN aparece em mais de um CNPJ (fundo incorporado que ainda consta nos dados),
    fica o fundo com o informe mais recente e, no empate, o de maior patrimônio."""
    latest = max(reports, key=lambda r: (r.ref_date, r.equity or 0.0))
    return [r for r in reports if r.cnpj == latest.cnpj]


def parse_monthly(content: bytes, tickers: Iterable[str]) -> dict[str, list[FiiMonthly]]:
    """Informes mensais dos tickers pedidos, do mais antigo para o mais recente."""
    wanted = {t.upper() for t in tickers}
    zf = zipfile.ZipFile(io.BytesIO(content))
    general = _latest_version(_read(zf, "geral"))
    if general.empty:
        return {}
    general = general.assign(ticker=general["Codigo_ISIN"].map(ticker_from_isin))
    general = general[general["ticker"].isin(wanted)]
    keys = ["cnpj", "Data_Referencia"]
    complement = _latest_version(_read(zf, "complemento")).drop(columns=["CNPJ_Fundo_Classe", "Versao"], errors="ignore")
    balance = _latest_version(_read(zf, "ativo_passivo")).drop(columns=["CNPJ_Fundo_Classe", "Versao"], errors="ignore")
    merged = general.merge(complement, on=keys, how="left", suffixes=("", "_c")).merge(
        balance, on=keys, how="left", suffixes=("", "_b")
    )
    out: dict[str, list[FiiMonthly]] = {}
    for _, row in merged.sort_values("Data_Referencia").iterrows():
        out.setdefault(str(row["ticker"]), []).append(_monthly_row(row))
    return {ticker: _current_fund(reports) for ticker, reports in out.items()}


def _vacancy(properties: pd.DataFrame) -> float | None:
    """Vacância física média ponderada pela área dos imóveis para renda acabados.

    Descarta o imóvel informado como 100% vago e ao mesmo tempo gerando receita (contradição comum
    nos informes). Se o que sobra cobre menos de MIN_CONSISTENT_AREA da área, devolve None em vez
    de um número que representaria só parte do fundo.
    """
    finished = properties[properties["Classe"] == FINISHED_RENTAL_CLASS]
    vacancy = pd.to_numeric(finished["Percentual_Vacancia"], errors="coerce")
    revenue = pd.to_numeric(finished["Percentual_Receitas_FII"], errors="coerce").fillna(0)
    area = pd.to_numeric(finished["Area"], errors="coerce")
    valid = vacancy.between(0, 1) & (area > 0) & ~((vacancy >= 1) & (revenue > 0))
    total_area = area[area > 0].sum()
    if not valid.any() or area[valid].sum() < MIN_CONSISTENT_AREA * total_area:
        return None
    return float((vacancy[valid] * area[valid]).sum() / area[valid].sum())


def _largest_property_share(properties: pd.DataFrame) -> float | None:
    rental = properties[properties["Classe"].astype("string").fillna("").str.startswith(RENTAL_CLASS)]
    shares = pd.to_numeric(rental["Percentual_Receitas_FII"], errors="coerce").dropna()
    if shares.empty or not shares.between(0, 1).all() or shares.sum() > REVENUE_SHARE_TOLERANCE:
        return None
    return float(shares.max())


def _largest_credit_value(assets: pd.DataFrame) -> float | None:
    values = pd.to_numeric(assets.loc[assets["Tipo"].isin(CREDIT_TYPES), "Valor"], errors="coerce").dropna()
    if values.empty:
        return None
    return float(values.max())


def _quarterly_for(cnpj: str, ref: str, properties: pd.DataFrame, assets: pd.DataFrame) -> FiiQuarterly:
    own = properties[(properties["cnpj"] == cnpj) & (properties["Data_Referencia"] == ref)]
    rental = own[own["Classe"].astype("string").fillna("").str.startswith(RENTAL_CLASS)]
    credit = assets[(assets["cnpj"] == cnpj) & (assets["Data_Referencia"] == ref)]
    return FiiQuarterly(
        cnpj=cnpj,
        ref_date=date.fromisoformat(ref),
        properties=len(rental) if len(own) else None,
        vacancy=_vacancy(own),
        largest_property_share=_largest_property_share(own),
        largest_credit_value=_largest_credit_value(credit),
    )


def parse_quarterly(content: bytes, cnpjs: Iterable[str]) -> dict[str, FiiQuarterly]:
    """Informe trimestral mais recente de cada CNPJ pedido."""
    wanted = {only_digits(c) for c in cnpjs}
    zf = zipfile.ZipFile(io.BytesIO(content))
    general = _latest_version(_read(zf, "geral"))
    if general.empty:
        return {}
    general = general[general["cnpj"].isin(wanted)]
    latest = general.groupby("cnpj")["Data_Referencia"].max()
    properties = _read(zf, "imovel", ("Classe", "Area", "Percentual_Vacancia", "Percentual_Receitas_FII"))
    assets = _read(zf, "ativo", ("Tipo", "Valor"))
    return {str(cnpj): _quarterly_for(str(cnpj), str(ref), properties, assets) for cnpj, ref in latest.items()}


async def fetch_monthly(year: int, tickers: Iterable[str]) -> dict[str, list[FiiMonthly]]:
    path = await get_cached(MENSAL_URL.format(year=year), max_age_hours=24 * 7, suffix=".zip")
    return parse_monthly(path.read_bytes(), tickers)


async def fetch_quarterly(year: int, cnpjs: Iterable[str]) -> dict[str, FiiQuarterly]:
    path = await get_cached(TRIMESTRAL_URL.format(year=year), max_age_hours=24 * 7, suffix=".zip")
    return parse_quarterly(path.read_bytes(), cnpjs)

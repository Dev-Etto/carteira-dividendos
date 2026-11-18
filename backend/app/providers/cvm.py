"""CVM Dados Abertos — balanços anuais (DFP) e mapeamento CNPJ ↔ ticker (FCA).

Os arquivos são ZIPs com CSVs em latin-1 separados por ';'. Valores vêm em
milhares (ESCALA_MOEDA = MIL) na maioria das empresas; convertemos para reais.
"""

import io
import zipfile
from dataclasses import dataclass, field
from datetime import date

import pandas as pd

from app.providers.base import DOWNLOAD_ERRORS, get_cached, normalize

DFP_URL = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS/dfp_cia_aberta_{year}.zip"
FCA_URL = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/FCA/DADOS/fca_cia_aberta_{year}.zip"


@dataclass
class AnnualStatement:
    cnpj: str
    year: int
    published_at: date | None = None
    values: dict[str, float] = field(default_factory=dict)


def only_digits(cnpj: str) -> str:
    return "".join(ch for ch in str(cnpj) if ch.isdigit())


def _read_member(zf: zipfile.ZipFile, contains: str) -> pd.DataFrame | None:
    name = next((n for n in zf.namelist() if contains in n), None)
    if name is None:
        return None
    with zf.open(name) as f:
        return pd.read_csv(f, sep=";", encoding="latin-1", dtype=str)


def _prepare(df: pd.DataFrame | None, cnpjs: set[str]) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.copy()
    df["cnpj"] = df["CNPJ_CIA"].map(only_digits)
    df = df[df["cnpj"].isin(cnpjs)]
    if "ORDEM_EXERC" in df:
        df = df[df["ORDEM_EXERC"].map(lambda s: normalize(str(s)).startswith("ultimo"))]
    if df.empty:
        return df
    df["VERSAO"] = df["VERSAO"].astype(int)
    df = df[df["VERSAO"] == df.groupby("cnpj")["VERSAO"].transform("max")]
    scale = df["ESCALA_MOEDA"].map(lambda s: 1000.0 if normalize(str(s)) == "mil" else 1.0)
    df["valor"] = pd.to_numeric(df["VL_CONTA"], errors="coerce") * scale
    df["ds"] = df["DS_CONTA"].map(lambda s: normalize(str(s)))
    df["cd"] = df["CD_CONTA"].astype(str)
    return df


def _code(df: pd.DataFrame, code: str) -> float | None:
    s = df.loc[df["cd"] == code, "valor"]
    return float(s.iloc[0]) if len(s) and pd.notna(s.iloc[0]) else None


def _sum_codes(df: pd.DataFrame, codes: list[str]) -> float | None:
    vals = [v for v in (_code(df, c) for c in codes) if v is not None]
    return float(sum(vals)) if vals else None


def _depth(code: str) -> int:
    return code.count(".")


def extract_net_income(dre: pd.DataFrame) -> float | None:
    """Lucro atribuído aos sócios da controladora (3.11.01). Algumas empresas entregam essa linha zerada
    com o lucro consolidado (3.11) preenchido; nesse caso vale o consolidado menos os minoritários (3.11.02)."""
    v = _code(dre, "3.11.01")
    total = _code(dre, "3.11")
    if v is not None and (v != 0 or not total):
        return v
    if total is not None:
        return total - (_code(dre, "3.11.02") or 0.0)
    top = dre[(dre["cd"].map(_depth) == 1) & dre["ds"].str.contains("lucro") & dre["ds"].str.contains("periodo")]
    if top.empty:
        return None
    row = top.sort_values("cd").iloc[-1]
    child = dre[dre["cd"].str.startswith(row["cd"] + ".") & dre["ds"].str.contains("controladora")]
    if not child.empty and pd.notna(child.iloc[0]["valor"]):
        return float(child.iloc[0]["valor"])
    return float(row["valor"]) if pd.notna(row["valor"]) else None


def extract_equity(bpp: pd.DataFrame) -> float | None:
    top = bpp[(bpp["cd"].map(_depth) == 1) & bpp["ds"].str.contains("patrimonio liquido")]
    if top.empty:
        return None
    row = top.iloc[0]
    total = float(row["valor"]) if pd.notna(row["valor"]) else None
    if total is None:
        return None
    minority = bpp[bpp["cd"].str.startswith(row["cd"] + ".") & bpp["ds"].str.contains("nao controlador")]
    if not minority.empty and pd.notna(minority.iloc[0]["valor"]):
        total -= float(minority.iloc[0]["valor"])
    return total


def extract_dividends_paid(dfc: pd.DataFrame) -> float | None:
    """Dividendos e JCP pagos (DFC, atividades de financiamento), somando só as linhas mais específicas
    para não contar o pai e o filho."""
    fin = dfc[dfc["cd"].str.startswith("6.03.")]
    mask = fin["ds"].str.contains("dividendo") | fin["ds"].str.contains("capital proprio") | fin["ds"].str.contains("jcp")
    rows = fin[mask]
    rows = rows[~rows["cd"].map(lambda c: any(o != c and o.startswith(c + ".") for o in rows["cd"]))]
    if rows.empty:
        return None
    return float(rows["valor"].fillna(0).sum())


def _published_dates(index: pd.DataFrame | None) -> dict[str, date]:
    """Data de entrega mais recente de cada empresa, pelo índice do DFP."""
    if index is None or "DT_RECEB" not in index:
        return {}
    received = (
        index.assign(cnpj=index["CNPJ_CIA"].map(only_digits), received=pd.to_datetime(index["DT_RECEB"], errors="coerce"))
        .groupby("cnpj")["received"]
        .max()
        .dropna()
    )
    return {str(cnpj): day for cnpj, day in received.dt.date.items()}


def parse_dfp_zip(content: bytes, cnpjs: set[str], year: int) -> dict[str, AnnualStatement]:
    zf = zipfile.ZipFile(io.BytesIO(content))
    dre = _prepare(_read_member(zf, f"DRE_con_{year}"), cnpjs)
    bpa = _prepare(_read_member(zf, f"BPA_con_{year}"), cnpjs)
    bpp = _prepare(_read_member(zf, f"BPP_con_{year}"), cnpjs)
    dfc_mi = _prepare(_read_member(zf, f"DFC_MI_con_{year}"), cnpjs)
    dfc_md = _prepare(_read_member(zf, f"DFC_MD_con_{year}"), cnpjs)
    dva = _prepare(_read_member(zf, f"DVA_con_{year}"), cnpjs)
    index = _read_member(zf, f"dfp_cia_aberta_{year}.csv")

    published = _published_dates(index)

    out: dict[str, AnnualStatement] = {}
    for cnpj in cnpjs:
        d_dre = dre[dre["cnpj"] == cnpj] if not dre.empty else dre
        if d_dre.empty:
            continue
        d_bpa = bpa[bpa["cnpj"] == cnpj] if not bpa.empty else bpa
        d_bpp = bpp[bpp["cnpj"] == cnpj] if not bpp.empty else bpp
        d_dva = dva[dva["cnpj"] == cnpj] if not dva.empty else dva
        d_dfc = dfc_mi[dfc_mi["cnpj"] == cnpj] if not dfc_mi.empty else dfc_mi
        if d_dfc.empty and not dfc_md.empty:
            d_dfc = dfc_md[dfc_md["cnpj"] == cnpj]

        v: dict[str, float | None] = {
            "revenue": _code(d_dre, "3.01"),
            "ebit": _code(d_dre, "3.05"),
            "net_income": extract_net_income(d_dre),
        }
        if not d_bpp.empty:
            v["equity"] = extract_equity(d_bpp)
            v["gross_debt"] = _sum_codes(d_bpp, ["2.01.04", "2.02.01"])
            v["current_liabilities"] = _code(d_bpp, "2.01")
            v["short_term_debt"] = _code(d_bpp, "2.01.04")
        if not d_bpa.empty:
            v["cash"] = _sum_codes(d_bpa, ["1.01.01", "1.01.02"])
            v["current_assets"] = _code(d_bpa, "1.01")
            v["fixed_assets"] = _code(d_bpa, "1.02.03")
        if not d_dva.empty:
            v["depreciation"] = _code(d_dva, "7.04.01")
        if not d_dfc.empty:
            v["operating_cash_flow"] = _code(d_dfc, "6.01")
            v["investing_cash_flow"] = _code(d_dfc, "6.02")
            v["dividends_paid"] = extract_dividends_paid(d_dfc)
        out[cnpj] = AnnualStatement(
            cnpj=cnpj, year=year, published_at=published.get(cnpj), values={k: x for k, x in v.items() if x is not None}
        )
    return out


def parse_fca_tickers(content: bytes) -> dict[str, str]:
    """Devolve {ticker: cnpj} a partir do arquivo de valores mobiliários do FCA."""
    zf = zipfile.ZipFile(io.BytesIO(content))
    df = _read_member(zf, "valor_mobiliario")
    if df is None:
        return {}
    cnpj_col = next(c for c in df.columns if "CNPJ" in c.upper())
    tick_col = next(c for c in df.columns if "CODIGO_NEGOCIACAO" in normalize(c).upper().replace(" ", "_"))
    out: dict[str, str] = {}
    for cnpj, tick in zip(df[cnpj_col], df[tick_col], strict=False):
        if isinstance(tick, str) and tick.strip():
            out[tick.strip().upper()] = only_digits(cnpj)
    return out


async def fetch_dfp(year: int, cnpjs: set[str]) -> dict[str, AnnualStatement]:
    path = await get_cached(DFP_URL.format(year=year), max_age_hours=24 * 7, suffix=".zip")
    return parse_dfp_zip(path.read_bytes(), cnpjs, year)


async def _ticker_map_of(year: int) -> dict[str, str]:
    try:
        path = await get_cached(FCA_URL.format(year=year), max_age_hours=24 * 30, suffix=".zip")
    except DOWNLOAD_ERRORS:
        return {}
    return parse_fca_tickers(path.read_bytes())


async def fetch_ticker_map(year: int) -> dict[str, str]:
    """Mapa ticker → CNPJ do FCA do ano; se o do ano ainda não saiu, usa o do ano anterior."""
    return await _ticker_map_of(year) or await _ticker_map_of(year - 1)

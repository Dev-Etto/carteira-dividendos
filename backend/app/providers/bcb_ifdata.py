"""Banco Central — IF.data: índice de Basileia dos conglomerados prudenciais.

O IF.data é trimestral e sai com uns três meses de atraso; a coleta tenta do trimestre mais recente para
trás até achar dados. Cada conglomerado é ligado à ação pela raiz do CNPJ da instituição líder (os 8
primeiros dígitos), que é a mesma do CNPJ da companhia aberta. Inadimplência acima de 90 dias não está
no IF.data com a mesma definição dos releases dos bancos, então continua manual.
"""

import json
from dataclasses import dataclass
from datetime import date
from urllib.parse import quote, urlencode

from app.providers.base import get_bytes

BASE_URL = "https://olinda.bcb.gov.br/olinda/servico/IFDATA/versao/v1/odata/"
CADASTRO = BASE_URL + "IfDataCadastro(AnoMes=@AnoMes)"
VALORES = BASE_URL + "IfDataValores(AnoMes=@AnoMes,TipoInstituicao=@TipoInstituicao,Relatorio=@Relatorio)"
PRUDENTIAL = 1
CAPITAL_REPORT = "'5'"
BASEL_COLUMN = "Índice de Basileia"
QUARTERS_BACK = 4


@dataclass(frozen=True)
class Basel:
    cnpj_root: str
    institution: str
    ratio_pct: float
    reference: str


def recent_quarters(today: date, count: int = QUARTERS_BACK) -> list[int]:
    """Trimestres (AAAAMM) do mais recente já encerrado para trás."""
    year, month = today.year, (today.month - 1) // 3 * 3
    out = []
    for _ in range(count):
        year, month = (year - 1, 12) if month == 0 else (year, month)
        out.append(year * 100 + month)
        month -= 3
    return out


def quarter_label(anomes: int) -> str:
    """202606 → "2T26"."""
    return f"{anomes % 100 // 3}T{anomes // 100 % 100:02d}"


def parse_basel(cadastro: bytes, valores: bytes, anomes: int) -> list[Basel]:
    """Basileia (em %) de cada conglomerado prudencial, com a raiz do CNPJ do líder."""
    ratios = {
        v["CodInst"]: float(v["Saldo"])
        for v in json.loads(valores)["value"]
        if str(v.get("NomeColuna", "")).startswith(BASEL_COLUMN) and v.get("Saldo") is not None
    }
    return [
        Basel(
            cnpj_root=str(c["CnpjInstituicaoLider"]),
            institution=str(c["NomeInstituicao"]),
            ratio_pct=round(ratios[c["CodInst"]] * 100, 2),
            reference=quarter_label(anomes),
        )
        for c in json.loads(cadastro)["value"]
        if c["CodInst"] in ratios and c.get("CnpjInstituicaoLider")
    ]


def odata_url(endpoint: str, params: dict[str, str]) -> str:
    """URL com espaços como %20: o OData do Banco Central não entende o "+" que o httpx usa nos parâmetros."""
    return f"{endpoint}?{urlencode(params, quote_via=quote, safe="@$',()")}"


async def _download(anomes: int) -> list[Basel]:
    common = {"@AnoMes": str(anomes), "$format": "json"}
    capital = {"@TipoInstituicao": str(PRUDENTIAL), "@Relatorio": CAPITAL_REPORT}
    basel_only = {"$filter": f"startswith(NomeColuna,'{BASEL_COLUMN}')"}
    valores = await get_bytes(odata_url(VALORES, common | capital | basel_only))
    cadastro = await get_bytes(odata_url(CADASTRO, common))
    return parse_basel(cadastro, valores, anomes)


async def fetch_basel(today: date | None = None) -> list[Basel]:
    """Basileia do trimestre mais recente publicado; vazio se nenhum dos últimos 4 tiver dados."""
    for anomes in recent_quarters(today or date.today()):
        found = await _download(anomes)
        if found:
            return found
    return []

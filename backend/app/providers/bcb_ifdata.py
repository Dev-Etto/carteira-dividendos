"""Banco Central — IF.data: índice de Basileia e crédito vencido dos conglomerados prudenciais.

O IF.data é trimestral e sai com uns três meses de atraso; a coleta tenta do trimestre mais recente para
trás até achar dados. Cada conglomerado é ligado à ação pela raiz do CNPJ da instituição líder (os 8
primeiros dígitos), que é a mesma do CNPJ da companhia aberta.

Inadimplência: o IF.data não tem o atraso acima de 90 dias dos releases dos bancos, mas tem, por modalidade
de crédito (relatórios 11, pessoa física, e 13, pessoa jurídica), o saldo vencido há mais de 15 dias e o
total. O app calcula o vencido ÷ total do banco e do sistema inteiro pela mesma conta, então a comparação
é justa mesmo com outra régua de dias. O total usado é a soma das mesmas modalidades que têm o vencido; o
"Total da Carteira" do relatório inclui o exterior, que não tem essa coluna.
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


CREDIT_REPORTS = ("'11'", "'13'")
OVERDUE_PREFIX = "Vencido"
TOTAL_COLUMN = "Total"


@dataclass(frozen=True)
class Overdue:
    cnpj_root: str
    institution: str
    overdue_pct: float
    reference: str


@dataclass(frozen=True)
class OverdueReport:
    """Crédito vencido há mais de 15 dias de cada conglomerado e do sistema inteiro, em %."""

    banks: list[Overdue]
    system_pct: float | None
    reference: str


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


def _credit_sums(rows: list[dict]) -> tuple[dict[str, float], dict[str, float]]:
    """Vencido e total por instituição, só nas linhas de modalidade (as que têm grupo)."""
    overdue: dict[str, float] = {}
    total: dict[str, float] = {}
    for r in rows:
        column, code, value = str(r.get("NomeColuna", "")), r["CodInst"], float(r.get("Saldo") or 0)
        by_modality = bool(r.get("Grupo"))
        overdue[code] = overdue.get(code, 0.0) + (value if by_modality and column.startswith(OVERDUE_PREFIX) else 0.0)
        total[code] = total.get(code, 0.0) + (value if by_modality and column == TOTAL_COLUMN else 0.0)
    return overdue, total


def parse_overdue(cadastro: bytes, credit: list[bytes], anomes: int) -> OverdueReport:
    """Junta os relatórios de crédito de pessoa física e jurídica e calcula o vencido ÷ total."""
    rows = [r for payload in credit for r in json.loads(payload)["value"]]
    overdue, total = _credit_sums(rows)
    reference = quarter_label(anomes)
    banks = [
        Overdue(
            cnpj_root=str(c["CnpjInstituicaoLider"]),
            institution=str(c["NomeInstituicao"]),
            overdue_pct=round(100 * overdue[c["CodInst"]] / total[c["CodInst"]], 2),
            reference=reference,
        )
        for c in json.loads(cadastro)["value"]
        if total.get(c["CodInst"]) and c.get("CnpjInstituicaoLider")
    ]
    system_total = sum(total.values())
    system = round(100 * sum(overdue.values()) / system_total, 2) if system_total else None
    return OverdueReport(banks=banks, system_pct=system, reference=reference)


async def _download_overdue(anomes: int) -> OverdueReport:
    common = {"@AnoMes": str(anomes), "$format": "json"}
    wanted = {"$filter": f"startswith(NomeColuna,'{OVERDUE_PREFIX}') or NomeColuna eq '{TOTAL_COLUMN}'"}
    credit = [
        await get_bytes(odata_url(VALORES, common | {"@TipoInstituicao": str(PRUDENTIAL), "@Relatorio": report} | wanted))
        for report in CREDIT_REPORTS
    ]
    cadastro = await get_bytes(odata_url(CADASTRO, common))
    return parse_overdue(cadastro, credit, anomes)


async def fetch_overdue(today: date | None = None) -> OverdueReport | None:
    """Crédito vencido do trimestre mais recente publicado; None se nenhum dos últimos 4 tiver dados."""
    for anomes in recent_quarters(today or date.today()):
        report = await _download_overdue(anomes)
        if report.banks:
            return report
    return None


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

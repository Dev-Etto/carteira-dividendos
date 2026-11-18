"""B3 — proventos em dinheiro das companhias listadas, a mesma API pública do site "Empresas listadas".

Serve para completar o histórico do Yahoo, que às vezes perde anos inteiros de proventos. Cada consulta
leva os parâmetros em JSON codificado em base64 no fim da URL. `GetListedSupplementCompany` devolve o nome
de pregão da empresa (pelos 4 primeiros caracteres do ticker), e `GetListedCashDividends`, paginado, o
histórico de dividendos e JCP de todas as classes (ON, PN, PNA, UNT...).

A B3 informa a data-com (último dia com direito) e o valor bruto por ação na época, sem ajuste por
desdobramentos posteriores. A data ex considerada é o dia útil seguinte à data-com (sem contar feriados).
"""

import base64
import json
import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from app.providers.base import DividendEvent, SplitInfo, get_cached

log = logging.getLogger(__name__)

BASE_URL = "https://sistemaswebb3-listados.b3.com.br/listedCompaniesProxy/CompanyCall/"
PAGE_SIZE = 120
"""A API devolve página vazia acima de 120 registros."""
CACHE_HOURS = 12
MAX_PAGES = 20
DATE_TOLERANCE_DAYS = 5
"""Distância máxima entre a data ex da B3 e a do Yahoo para tratar como o mesmo provento."""

KINDS = {
    "DIVIDENDO": "dividendo",
    "JRS CAP PROPRIO": "jcp",
    "RENDIMENTO": "rendimento",
    "AMORTIZACAO": "amortizacao",
}
SHARE_CLASSES = {"3": "ON", "4": "PN", "5": "PNA", "6": "PNB", "7": "PNC", "8": "PND", "11": "UNT"}
SATURDAY = 5


@dataclass(frozen=True)
class CashDividend:
    share_class: str
    record_date: date
    amount: float
    kind: str

    @property
    def ex_date(self) -> date:
        return next_weekday(self.record_date)


def next_weekday(day: date) -> date:
    """Dia útil seguinte (segunda a sexta), sem considerar feriados."""
    nxt = day + timedelta(days=1)
    while nxt.weekday() >= SATURDAY:
        nxt += timedelta(days=1)
    return nxt


def share_class(ticker: str) -> str | None:
    """Classe que a B3 usa para o ticker: CPFE3 → ON, ISAE4 → PN, TAEE11 → UNT."""
    return SHARE_CLASSES.get(ticker[4:])


def call_url(method: str, params: dict[str, object]) -> str:
    """URL da API: parâmetros em JSON compacto, codificado em base64."""
    payload = json.dumps(params, separators=(",", ":")).encode()
    return BASE_URL + method + "/" + base64.b64encode(payload).decode()


def _number(text: str) -> float | None:
    """Número no formato brasileiro ("1.234,56"); vazio ou inválido vira None."""
    try:
        return float(text.replace(".", "").replace(",", "."))
    except (AttributeError, ValueError):
        return None


def _parse_date(text: str) -> date | None:
    try:
        return datetime.strptime(text, "%d/%m/%Y").date()
    except (TypeError, ValueError):
        return None


def parse_trading_name(payload: bytes) -> str | None:
    """Nome de pregão da empresa ("CPFL ENERGIA"), que identifica a empresa na consulta de proventos."""
    data = json.loads(payload)
    company = data[0] if isinstance(data, list) and data else {}
    return str(company.get("tradingName") or "").strip() or None


def _cash_dividend(row: dict) -> CashDividend | None:
    kind = KINDS.get(str(row.get("corporateAction", "")).strip())
    record = _parse_date(str(row.get("lastDatePriorEx", "")))
    value = _number(str(row.get("valueCash", "")))
    per = _number(str(row.get("quotedPerShares", "1"))) or 1.0
    if kind is None or record is None or not value or value <= 0:
        return None
    return CashDividend(str(row.get("typeStock", "")).strip(), record, value / per, kind)


def parse_cash_dividends(payload: bytes) -> tuple[list[CashDividend], int]:
    """Proventos de uma página e o total de páginas. Linhas de tipo desconhecido ou sem valor são ignoradas."""
    data = json.loads(payload)
    rows = [d for r in data.get("results") or [] if (d := _cash_dividend(r)) is not None]
    return rows, int((data.get("page") or {}).get("totalPages") or 0)


def adjust_for_splits(amount: float, ex_date: date, splits: list[SplitInfo]) -> float:
    """Converte o valor por ação da época para a base de ações de hoje, como o Yahoo faz: divide pelos
    desdobramentos (e bonificações) a partir da data ex."""
    for s in splits:
        if s.date >= ex_date and s.ratio > 0:
            amount /= s.ratio
    return amount


def missing_events(
    b3: list[CashDividend], ticker: str, yahoo_dates: list[date], splits: list[SplitInfo], since: date
) -> list[DividendEvent]:
    """Proventos da classe do ticker que o Yahoo não tem.

    Um provento da B3 conta como já existente quando o Yahoo tem qualquer provento a até
    `DATE_TOLERANCE_DAYS` da data ex: o Yahoo soma os proventos do mesmo dia num valor só (dividendo + JCP)
    e às vezes diverge no valor, então comparar valores criaria duplicatas. Linhas repetidas da B3
    (mesma data, tipo e valor) entram uma vez só.
    """
    cls = share_class(ticker)
    tolerance = timedelta(days=DATE_TOLERANCE_DAYS)
    out: dict[tuple[date, str, float], DividendEvent] = {}
    for d in b3:
        ex = d.ex_date
        covered = any(abs(ex - y) <= tolerance for y in yahoo_dates)
        if d.share_class != cls or ex < since or covered:
            continue
        amount = round(adjust_for_splits(d.amount, ex, splits), 8)
        out[(ex, d.kind, amount)] = DividendEvent(ex, amount, d.kind)
    return sorted(out.values(), key=lambda e: (e.ex_date, e.kind))


async def fetch_cash_dividends(ticker: str) -> list[CashDividend]:
    """Todos os proventos em dinheiro da empresa do ticker, de todas as classes. Empresa não encontrada
    devolve lista vazia."""
    company = await get_cached(
        call_url("GetListedSupplementCompany", {"issuingCompany": ticker[:4], "language": "pt-br"}),
        CACHE_HOURS,
        ".json",
    )
    name = parse_trading_name(company.read_bytes())
    if name is None:
        log.warning("empresa de %s não encontrada na B3", ticker)
        return []
    out: list[CashDividend] = []
    page, pages = 1, 1
    while page <= min(pages, MAX_PAGES):
        params = {"language": "pt-br", "pageNumber": page, "pageSize": PAGE_SIZE, "tradingName": name}
        path = await get_cached(call_url("GetListedCashDividends", params), CACHE_HOURS, ".json")
        rows, pages = parse_cash_dividends(path.read_bytes())
        out.extend(rows)
        page += 1
    return out

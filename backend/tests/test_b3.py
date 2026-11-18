"""Proventos da B3: parse da API de empresas listadas e preenchimento das lacunas do Yahoo."""

import base64
import json
from datetime import date

import httpx
import respx

from app.providers import b3, base
from app.providers.base import SplitInfo

SUPPLEMENT = [
    {
        "tradingName": "CPFL ENERGIA",
        "code": "CPFE",
        "codeCVM": "18660",
        "cashDividends": [{"assetIssued": "BRCPFEACNOR0", "rate": "3,73153620400", "label": "DIVIDENDO"}],
    }
]


def _row(type_stock: str, action: str, record: str, value: str, per: str = "1") -> dict[str, str]:
    """Linha no formato real de GetListedCashDividends."""
    return {
        "typeStock": type_stock,
        "dateApproval": record,
        "valueCash": value,
        "ratio": "1",
        "corporateAction": action,
        "lastDatePriorEx": record,
        "dateClosingPricePriorExDate": record,
        "closingPricePriorExDate": "39,09",
        "quotedPerShares": per,
        "corporateActionPrice": "7,148060",
        "lastDateTimePriorEx": "2025-04-29T00:00:00",
    }


def _page(rows: list[dict[str, str]], number: int, pages: int) -> dict:
    return {"page": {"pageNumber": number, "pageSize": 120, "totalRecords": 3, "totalPages": pages}, "results": rows}


def test_url_leva_parametros_em_base64():
    url = b3.call_url("GetListedSupplementCompany", {"issuingCompany": "CPFE", "language": "pt-br"})
    encoded = url.rsplit("/", 1)[1]
    assert url.startswith(b3.BASE_URL + "GetListedSupplementCompany/")
    assert json.loads(base64.b64decode(encoded)) == {"issuingCompany": "CPFE", "language": "pt-br"}


def test_classe_pelo_ticker():
    assert b3.share_class("CPFE3") == "ON"
    assert b3.share_class("ISAE4") == "PN"
    assert b3.share_class("USIM5") == "PNA"
    assert b3.share_class("TAEE11") == "UNT"
    assert b3.share_class("XPTO9") is None


def test_nome_de_pregao():
    assert b3.parse_trading_name(json.dumps(SUPPLEMENT).encode()) == "CPFL ENERGIA"
    assert b3.parse_trading_name(b"[]") is None
    assert b3.parse_trading_name(json.dumps([{"tradingName": "   "}]).encode()) is None


def test_parse_proventos_em_dinheiro():
    rows = [
        _row("ON", "DIVIDENDO", "29/04/2025", "2,79417675"),
        _row("ON", "JRS CAP PROPRIO", "11/03/2025", "0,786945"),
        _row("PN", "RENDIMENTO", "22/02/2024", "1.000,00", per="1000"),
        _row("ON", "BONIFICACAO", "29/04/2016", "2,5"),
        _row("ON", "DIVIDENDO", "", "1,0"),
        _row("ON", "DIVIDENDO", "29/04/2024", "0"),
    ]
    found, pages = b3.parse_cash_dividends(json.dumps(_page(rows, 1, 2)).encode())
    assert pages == 2
    assert found == [
        b3.CashDividend("ON", date(2025, 4, 29), 2.79417675, "dividendo"),
        b3.CashDividend("ON", date(2025, 3, 11), 0.786945, "jcp"),
        b3.CashDividend("PN", date(2024, 2, 22), 1.0, "rendimento"),
    ]


def test_data_ex_e_o_dia_util_seguinte_a_data_com():
    assert b3.CashDividend("ON", date(2025, 4, 29), 1.0, "dividendo").ex_date == date(2025, 4, 30)
    assert b3.CashDividend("ON", date(2023, 12, 29), 1.0, "dividendo").ex_date == date(2024, 1, 1)
    assert b3.CashDividend("ON", date(2008, 12, 26), 1.0, "jcp").ex_date == date(2008, 12, 29)


def test_ajuste_por_desdobramento_posterior():
    splits = [SplitInfo(date(2008, 4, 28), 2.0), SplitInfo(date(2005, 9, 1), 4.0)]
    assert b3.adjust_for_splits(0.2, date(2008, 4, 7), splits) == 0.1
    assert b3.adjust_for_splits(0.8, date(2008, 12, 29), splits) == 0.8


def test_so_preenche_o_que_falta_no_yahoo():
    """O Yahoo soma dividendo e JCP do mesmo dia e às vezes diverge no valor: data próxima basta para não duplicar."""
    found = [
        b3.CashDividend("ON", date(2026, 4, 29), 3.73, "dividendo"),
        b3.CashDividend("ON", date(2025, 4, 29), 2.79, "dividendo"),
        b3.CashDividend("ON", date(2025, 4, 29), 2.79, "dividendo"),
        b3.CashDividend("PN", date(2025, 4, 29), 2.79, "dividendo"),
        b3.CashDividend("ON", date(2024, 4, 26), 2.75, "jcp"),
        b3.CashDividend("ON", date(2004, 4, 26), 9.0, "dividendo"),
    ]
    yahoo = [date(2026, 4, 30)]
    splits = [SplitInfo(date(2025, 1, 2), 2.0)]
    events = b3.missing_events(found, "CPFE3", yahoo, splits, since=date(2006, 1, 1))
    assert [(e.ex_date, e.amount, e.kind) for e in events] == [
        (date(2024, 4, 29), 1.375, "jcp"),
        (date(2025, 4, 30), 2.79, "dividendo"),
    ]


def test_unit_recebe_o_provento_da_unit():
    found = [b3.CashDividend("UNT", date(2025, 8, 18), 0.87, "jcp"), b3.CashDividend("ON", date(2025, 8, 18), 0.29, "jcp")]
    events = b3.missing_events(found, "TAEE11", [], [], since=date(2006, 1, 1))
    assert [(e.amount, e.kind) for e in events] == [(0.87, "jcp")]


@respx.mock
async def test_baixa_todas_as_paginas(monkeypatch, tmp_path):
    monkeypatch.setattr(base.get_settings(), "cache_dir", tmp_path)
    respx.get(b3.call_url("GetListedSupplementCompany", {"issuingCompany": "CPFE", "language": "pt-br"})).mock(
        return_value=httpx.Response(200, json=SUPPLEMENT)
    )
    pages = {
        1: _page([_row("ON", "DIVIDENDO", "29/04/2025", "2,79417675")], 1, 2),
        2: _page([_row("ON", "DIVIDENDO", "26/04/2024", "2,753976596")], 2, 2),
    }
    for number, body in pages.items():
        params = {"language": "pt-br", "pageNumber": number, "pageSize": b3.PAGE_SIZE, "tradingName": "CPFL ENERGIA"}
        respx.get(b3.call_url("GetListedCashDividends", params)).mock(return_value=httpx.Response(200, json=body))
    found = await b3.fetch_cash_dividends("CPFE3")
    assert [d.record_date for d in found] == [date(2025, 4, 29), date(2024, 4, 26)]


@respx.mock
async def test_empresa_desconhecida_nao_tem_proventos(monkeypatch, tmp_path):
    monkeypatch.setattr(base.get_settings(), "cache_dir", tmp_path)
    respx.get(b3.call_url("GetListedSupplementCompany", {"issuingCompany": "XPTO", "language": "pt-br"})).mock(
        return_value=httpx.Response(200, json=[])
    )
    assert await b3.fetch_cash_dividends("XPTO3") == []

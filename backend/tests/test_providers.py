"""Parsers das fontes, com amostras no formato real de cada arquivo."""

import io
import json
import zipfile
from datetime import date

import httpx
import pandas as pd
import pytest
import respx

from app.providers import base, bcb, cvm, market, tesouro

CVM_HEADER = "CNPJ_CIA;DT_REFER;VERSAO;DENOM_CIA;CD_CVM;GRUPO_DFP;MOEDA;ESCALA_MOEDA;ORDEM_EXERC;DT_INI_EXERC;DT_FIM_EXERC;CD_CONTA;DS_CONTA;VL_CONTA;ST_CONTA_FIXA"
CNPJ = "07.859.971/0001-30"


def _line(code: str, ds: str, val: float, ordem: str = "ÚLTIMO", versao: int = 2) -> str:
    return (
        f"{CNPJ};2024-12-31;{versao};EMPRESA SA;12345;DF Consolidado;REAL;MIL;{ordem};2024-01-01;2024-12-31;{code};{ds};{val};S"
    )


def _dfp_zip() -> bytes:
    dre = [
        CVM_HEADER,
        _line("3.01", "Receita de Venda de Bens e/ou Serviços", 3000000),
        _line("3.05", "Resultado Antes do Resultado Financeiro e dos Tributos", 1600000),
        _line("3.11", "Lucro/Prejuízo Consolidado do Período", 1200000),
        _line("3.11.01", "Atribuído a Sócios da Empresa Controladora", 1100000),
        _line("3.11.01", "Atribuído a Sócios da Empresa Controladora", 999, ordem="PENÚLTIMO"),
        _line("3.11.01", "Atribuído a Sócios da Empresa Controladora", 1, versao=1),
    ]
    bpa = [
        CVM_HEADER,
        _line("1.01", "Ativo Circulante", 4000000),
        _line("1.01.01", "Caixa e Equivalentes de Caixa", 500000),
        _line("1.01.02", "Aplicações Financeiras", 1500000),
        _line("1.02.03", "Imobilizado", 9000000),
    ]
    bpp = [
        CVM_HEADER,
        _line("2.01", "Passivo Circulante", 2500000),
        _line("2.01.04", "Empréstimos e Financiamentos", 1000000),
        _line("2.02.01", "Empréstimos e Financiamentos", 6000000),
        _line("2.03", "Patrimônio Líquido Consolidado", 6500000),
        _line("2.03.09", "Participação dos Acionistas Não Controladores", 500000),
    ]
    dfc = [
        CVM_HEADER,
        _line("6.01", "Caixa Líquido Atividades Operacionais", 1700000),
        _line("6.02", "Caixa Líquido Atividades de Investimento", -200000),
        _line("6.03", "Caixa Líquido Atividades de Financiamento", -900000),
        _line("6.03.04", "Dividendos e juros sobre capital próprio pagos", -800000),
    ]
    dva = [CVM_HEADER, _line("7.04.01", "Depreciação, Amortização e Exaustão", 100000)]
    idx = (
        "CNPJ_CIA;DT_REFER;VERSAO;DENOM_CIA;CD_CVM;CATEG_DOC;ID_DOC;DT_RECEB;LINK_DOC\n"
        f"{CNPJ};2024-12-31;2;EMPRESA SA;12345;DFP;1;2025-02-20;x"
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, rows in [("DRE", dre), ("BPA", bpa), ("BPP", bpp), ("DFC_MI", dfc), ("DVA", dva)]:
            z.writestr(f"dfp_cia_aberta_{name}_con_2024.csv", "\n".join(rows).encode("latin-1"))
        z.writestr("dfp_cia_aberta_2024.csv", idx.encode("latin-1"))
    return buf.getvalue()


def test_cvm_dfp_extrai_contas_em_reais():
    """Valores em reais, da versão mais nova do documento; lucro atribuído à controladora e patrimônio sem minoritários."""
    out = cvm.parse_dfp_zip(_dfp_zip(), {"07859971000130"}, 2024)
    st = out["07859971000130"]
    v = st.values
    assert v["net_income"] == 1_100_000_000
    assert v["equity"] == 6_000_000_000
    assert v["gross_debt"] == 7_000_000_000
    assert v["cash"] == 2_000_000_000
    assert v["depreciation"] == 100_000_000
    assert v["dividends_paid"] == -800_000_000
    assert (v["current_assets"], v["current_liabilities"]) == (4_000_000_000, 2_500_000_000)
    assert (v["short_term_debt"], v["fixed_assets"]) == (1_000_000_000, 9_000_000_000)
    assert st.published_at == date(2025, 2, 20)


def test_cvm_fca_mapeia_ticker():
    csv = (
        "CNPJ_Companhia;Data_Referencia;Versao;ID_Documento;Nome_Empresarial;Valor_Mobiliario;Codigo_Negociacao\n"
        f"{CNPJ};2025-01-01;1;1;EMPRESA SA;Units;TAEE11\n{CNPJ};2025-01-01;1;1;EMPRESA SA;Ações Ordinárias;TAEE3\n"
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("fca_cia_aberta_valor_mobiliario_2025.csv", csv.encode("latin-1"))
    m = cvm.parse_fca_tickers(buf.getvalue())
    assert m["TAEE11"] == "07859971000130"


def test_bcb_sgs():
    payload = json.dumps([{"data": "04/11/2026", "valor": "13.75"}]).encode()
    assert bcb.parse_sgs(payload) == [(date(2026, 11, 4), 0.1375)]


@respx.mock
async def test_bcb_fetch_usa_intervalo_de_datas():
    """/ultimos/{n} só aceita n <= 20; a coleta pede por intervalo de datas."""
    route = respx.get("https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados").mock(
        return_value=httpx.Response(200, json=[{"data": "17/11/2026", "valor": "15,00"}])
    )
    points = await bcb.fetch_series("selic_meta", days=400, today=date(2026, 11, 17))
    assert points == [(date(2026, 11, 17), 0.15)]
    params = route.calls.last.request.url.params
    assert params["dataInicial"] == "13/10/2025"
    assert params["dataFinal"] == "17/11/2026"


@respx.mock
async def test_get_bytes_nao_repete_erro_4xx():
    route = respx.get("https://exemplo.test/x").mock(return_value=httpx.Response(400))
    with pytest.raises(httpx.HTTPStatusError):
        await base.get_bytes("https://exemplo.test/x")
    assert route.call_count == 1


@respx.mock
async def test_get_bytes_repete_erro_temporario(monkeypatch):
    monkeypatch.setattr(base.get_bytes.retry, "sleep", _no_sleep)  # type: ignore[attr-defined]
    route = respx.get("https://exemplo.test/y").mock(side_effect=[httpx.Response(503), httpx.Response(200, content=b"ok")])
    assert await base.get_bytes("https://exemplo.test/y") == b"ok"
    assert route.call_count == 2


async def _no_sleep(_: float) -> None:
    return None


def test_tesouro_csv():
    csv = (
        "Tipo Titulo;Data Vencimento;Data Base;Taxa Compra Manha;Taxa Venda Manha;PU Compra Manha;PU Venda Manha;PU Base Manha\n"
        "Tesouro IPCA+;15/05/2035;13/11/2026;7,12;7,24;2201,55;2190,10;2190,00\n"
        "Tesouro Selic;01/03/2031;13/11/2026;0,08;0,09;17123,45;17100,00;17100,00\n"
    )
    bonds = tesouro.parse_csv(csv.encode("latin-1"))
    b = bonds[0]
    assert b.name == "Tesouro IPCA+"
    assert b.maturity == date(2035, 5, 15)
    assert abs(b.buy_rate - 0.0712) < 1e-9
    assert b.buy_price == 2201.55


def test_brapi_quote():
    q = market.parse_brapi(
        {
            "results": [
                {
                    "symbol": "ITUB4",
                    "regularMarketPrice": 36.5,
                    "regularMarketVolume": 1e7,
                    "marketCap": 3.5e11,
                    "longName": "Itaú Unibanco",
                }
            ]
        },
        "ITUB4",
    )
    assert q
    assert q.price == 36.5
    assert q.market_cap == 3.5e11


def test_yahoo_history():
    idx = pd.to_datetime(["2025-01-02", "2025-01-03"])
    df = pd.DataFrame(
        {"Close": [10.0, 11.0], "Volume": [100, 200], "Dividends": [0.0, 0.5], "Stock Splits": [0.0, 2.0]}, index=idx
    )
    prices, divs, splits = market.history_to_points(df)
    assert len(prices) == 2
    assert divs[0].amount == 0.5
    assert splits[0].ratio == 2.0


def _itr_line(code: str, val: float, refer: str, start: str, versao: int = 1, ds: str = "conta") -> str:
    return f"{CNPJ};{refer};{versao};EMPRESA SA;12345;DF Consolidado;REAL;MIL;ÚLTIMO;{start};{refer};{code};{ds};{val};S"


def _itr_zip() -> bytes:
    """1º trimestre só com a linha acumulada; 2º com a acumulada e a dos 3 meses; o 2º tem uma reapresentação
    (versão 2) que precisa prevalecer, sem apagar o 1º, que só tem versão 1."""
    dre = [
        CVM_HEADER,
        _itr_line("3.01", 1000, "2026-03-31", "2026-01-01"),
        _itr_line("3.11", 300, "2026-03-31", "2026-01-01"),
        _itr_line("3.11.01", 0, "2026-03-31", "2026-01-01"),
        _itr_line("3.01", 2100, "2026-06-30", "2026-01-01", versao=2),
        _itr_line("3.01", 1100, "2026-06-30", "2026-04-01", versao=2),
        _itr_line("3.11.01", 350, "2026-06-30", "2026-04-01", versao=2),
        _itr_line("3.11.01", 999, "2026-06-30", "2026-04-01", versao=1),
    ]
    bpp = [CVM_HEADER, _itr_line("2.03", 6000, "2026-06-30", "2026-01-01", versao=2, ds="Patrimônio Líquido Consolidado")]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("itr_cia_aberta_DRE_con_2026.csv", "\n".join(dre).encode("latin-1"))
        z.writestr("itr_cia_aberta_BPP_con_2026.csv", "\n".join(bpp).encode("latin-1"))
    return buf.getvalue()


def test_cvm_itr_extrai_so_os_3_meses_de_cada_trimestre():
    quarters = {q.quarter: q for q in cvm.parse_itr_zip(_itr_zip(), {"07859971000130"}, 2026)}
    assert set(quarters) == {1, 2}
    assert quarters[1].values["revenue"] == 1_000_000
    assert quarters[1].values["net_income"] == 300_000
    assert quarters[2].values["revenue"] == 1_100_000
    assert quarters[2].values["net_income"] == 350_000
    assert quarters[2].values["equity"] == 6_000_000
    assert quarters[2].period_end == date(2026, 6, 30)


def test_quarto_trimestre_e_o_ano_menos_os_tres_primeiros():
    anual = {"net_income": 1000.0, "revenue": 4000.0, "equity": 600.0}
    tri = [{"net_income": 200.0, "revenue": 900.0}, {"net_income": 250.0, "revenue": 1000.0}, {"net_income": 300.0}]
    assert cvm.fourth_quarter(anual, tri) == {"net_income": 250.0, "equity": 600.0}

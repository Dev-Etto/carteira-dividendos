import io
import zipfile
from datetime import date

from app.providers.cvm_etf import name_key, parse_index_funds

HEADER = "CNPJ_Classe;Denominacao_Social;Situacao;Patrimonio_Liquido;Data_Patrimonio_Liquido"


def _zip(rows: list[str], name: str = "registro_classe.csv") -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(name, "\n".join([HEADER, *rows]).encode("latin-1"))
    return buf.getvalue()


def test_fundos_de_indice_ativos_por_nome():
    content = _zip(
        [
            "10.406.511/0001-61;ISHARES IBOVESPA CLASSE DE ÍNDICE - RESPONSABILIDADE LIMITADA;Em Funcionamento Normal;18485873683.21;2026-11-13",
            "52.116.337/0001-62;NU RENDA IBOV SMART DIVIDENDOS CLASSE DE  ÍNDICE - RESP;Em Funcionamento Normal;;",
            "69.494.876/0001-38;TREND ETF DIVIDENDOS B3 FUNDO DE ÍNDICE;Fase Pré-Operacional;;",
            "02.097.252/0001-06;SAFRA MULTIDIVIDENDOS PB FIF EM AÇÕES;Em Funcionamento Normal;131453772.15;2026-11-12",
        ]
    )
    funds = parse_index_funds(content)
    assert len(funds) == 2
    bova = funds[name_key("ISHARES IBOVESPA CLASSE DE ÍNDICE - RESPONSABILIDADE LIMITADA")]
    assert (bova.cnpj, bova.equity, bova.equity_date) == ("10406511000161", 18485873683.21, date(2026, 11, 13))
    nu = funds[name_key("Nu Renda Ibov Smart Dividendos Classe de Índice - Resp")]
    assert (nu.equity, nu.equity_date) == (None, None)


def test_zip_sem_cadastro():
    assert parse_index_funds(_zip([], name="outro.csv")) == {}

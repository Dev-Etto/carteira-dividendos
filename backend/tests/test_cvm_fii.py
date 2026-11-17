import io
import zipfile
from datetime import date

import pytest

from app.providers import cvm_fii

CNPJ_PAPEL = "16.706.958/0001-32"
CNPJ_TIJOLO = "11.728.688/0001-47"
CNPJ_INCORPORADO = "07.583.627/0001-61"


def _csv(header: str, rows: list[str]) -> bytes:
    return "\n".join([header, *rows]).encode("latin-1")


def _zip(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, content in files.items():
            z.writestr(name, content)
    return buf.getvalue()


GERAL = (
    "Tipo_Fundo_Classe;CNPJ_Fundo_Classe;Data_Referencia;Versao;Nome_Fundo_Classe;Data_Funcionamento;"
    "Codigo_ISIN;Segmento_Atuacao;Mercado_Negociacao_Bolsa"
)
COMPLEMENTO = (
    "CNPJ_Fundo_Classe;Data_Referencia;Versao;Total_Numero_Cotistas;Patrimonio_Liquido;Cotas_Emitidas;"
    "Valor_Patrimonial_Cotas;Percentual_Despesas_Taxa_Administracao"
)
ATIVO_PASSIVO = "CNPJ_Fundo_Classe;Data_Referencia;Versao;Disponibilidades;CRI;Imoveis_Renda_Acabados;FII"


def mensal() -> bytes:
    return _zip(
        {
            "inf_mensal_fii_geral_2026.csv": _csv(
                GERAL,
                [
                    f"Classe;{CNPJ_PAPEL};2026-09-01;1;KINEA RENDIMENTOS;2012-10-15;BRKNCRCTF000;Multicategoria;S",
                    f"Classe;{CNPJ_PAPEL};2026-10-01;1;KINEA RENDIMENTOS;2012-10-15;BRKNCRCTF000;Multicategoria;S",
                    f"Classe;{CNPJ_PAPEL};2026-10-01;2;KINEA RENDIMENTOS II;2012-10-15;BRKNCRCTF000;Multicategoria;S",
                    f"Classe;{CNPJ_INCORPORADO};2026-07-01;1;PENINSULA;2009-01-01;BRKNCRCTF000;Shoppings;S",
                    f"Classe;{CNPJ_TIJOLO};2026-10-01;1;PÁTRIA LOG;2010-05-03;BRHGLGCTF004;Logística;N",
                    "Classe;99.999.999/0001-99;2026-10-01;1;SEM ISIN;2010-01-01;;Outros;S",
                ],
            ),
            "inf_mensal_fii_complemento_2026.csv": _csv(
                COMPLEMENTO,
                [
                    f"{CNPJ_PAPEL};2026-09-01;1;590000;12000000000;123000000;101.5;0.00075",
                    f"{CNPJ_PAPEL};2026-10-01;1;1;1;1;1;1",
                    f"{CNPJ_PAPEL};2026-10-01;2;601937;12593203888.12;123238948;102.18;0.000762",
                    f"{CNPJ_INCORPORADO};2026-07-01;1;9000;800000000;8000000;100;0.001",
                    f"{CNPJ_TIJOLO};2026-10-01;1;633787;7656899371.48;46398492;165.02;0.000465",
                ],
            ),
            "inf_mensal_fii_ativo_passivo_2026.csv": _csv(
                ATIVO_PASSIVO,
                [
                    f"{CNPJ_PAPEL};2026-10-01;2;100;700;0;200",
                    f"{CNPJ_TIJOLO};2026-10-01;1;20;0;970;10",
                ],
            ),
        }
    )


IMOVEL = "CNPJ_Fundo_Classe;Data_Referencia;Versao;Classe;Nome_Imovel;Area;Percentual_Vacancia;Percentual_Receitas_FII"


def trimestral(imoveis: list[str], ativos: list[str] | None = None) -> bytes:
    return _zip(
        {
            "inf_trimestral_fii_geral_2026.csv": _csv(
                "CNPJ_Fundo_Classe;Data_Referencia;Versao",
                [f"{CNPJ_TIJOLO};2026-06-30;1", f"{CNPJ_TIJOLO};2026-09-30;1", f"{CNPJ_PAPEL};2026-09-30;1"],
            ),
            "inf_trimestral_fii_aquisicao_imovel_2026.csv": _csv(
                "CNPJ_Fundo_Classe;Data_Referencia;Versao;Nome_Imovel", [f"{CNPJ_TIJOLO};2026-09-30;1;Novo galpão"]
            ),
            "inf_trimestral_fii_imovel_2026.csv": _csv(IMOVEL, imoveis),
            "inf_trimestral_fii_ativo_2026.csv": _csv(
                "CNPJ_Fundo_Classe;Data_Referencia;Versao;Tipo;Valor",
                ativos or [f"{CNPJ_PAPEL};2026-09-30;1;CRI/CRA;460000000", f"{CNPJ_PAPEL};2026-09-30;1;FII;900000000"],
            ),
        }
    )


def imovel(
    area: float, vacancia: float, receita: float, classe: str = "Imóveis para renda acabados", ref: str = "2026-09-30"
) -> str:
    return f"{CNPJ_TIJOLO};{ref};1;{classe};Galpão;{area};{vacancia};{receita}"


@pytest.mark.parametrize(
    ("isin", "ticker"),
    [("BRMXRFCTF008", "MXRF11"), ("brhglgctf004", "HGLG11"), ("BRPETRACNPR6", None), ("", None), (None, None)],
)
def test_ticker_pelo_isin(isin, ticker):
    assert cvm_fii.ticker_from_isin(isin) == ticker


def test_mensal_fica_com_a_ultima_versao_e_junta_as_tabelas():
    papel = cvm_fii.parse_monthly(mensal(), ["kncr11"])["KNCR11"]
    assert [r.ref_date for r in papel] == [date(2026, 9, 1), date(2026, 10, 1)]
    ultimo = papel[-1]
    assert ultimo.name == "KINEA RENDIMENTOS II"
    assert ultimo.holders == 601937
    assert ultimo.equity == pytest.approx(12593203888.12)
    assert ultimo.nav_per_share == pytest.approx(102.18)
    assert ultimo.admin_fee == pytest.approx(0.000762)
    assert ultimo.started_on == date(2012, 10, 15)
    assert ultimo.listed is True
    assert (ultimo.paper, ultimo.brick, ultimo.fof, ultimo.cash) == pytest.approx((0.7, 0.0, 0.2, 0.1))


def test_mensal_ignora_fundo_incorporado_com_o_mesmo_isin():
    papel = cvm_fii.parse_monthly(mensal(), ["KNCR11"])["KNCR11"]
    assert {r.cnpj for r in papel} == {"16706958000132"}


def test_mensal_filtra_tickers_e_le_negociacao_fora_de_bolsa():
    out = cvm_fii.parse_monthly(mensal(), ["HGLG11", "XXXX11"])
    assert set(out) == {"HGLG11"}
    tijolo = out["HGLG11"][-1]
    assert tijolo.listed is False
    assert tijolo.brick == pytest.approx(0.97)
    assert tijolo.paper == 0.0


def test_mensal_sem_composicao_fica_zerado():
    sem_balanco = cvm_fii.parse_monthly(mensal(), ["KNCR11"])["KNCR11"][0]
    assert (sem_balanco.paper, sem_balanco.brick, sem_balanco.fof, sem_balanco.cash) == (0.0, 0.0, 0.0, 0.0)


def test_trimestral_usa_o_trimestre_mais_recente_e_pondera_vacancia_pela_area():
    content = trimestral(
        [
            imovel(1000, 0.0, 0.3),
            imovel(3000, 0.2, 0.5),
            imovel(500, 0.0, 0.2, classe="Imóveis para venda acabados"),
            imovel(9999, 0.9, 0.9, ref="2026-06-30"),
        ]
    )
    q = cvm_fii.parse_quarterly(content, [CNPJ_TIJOLO])["11728688000147"]
    assert q.ref_date == date(2026, 9, 30)
    assert q.properties == 2
    assert q.vacancy == pytest.approx(0.15)
    assert q.largest_property_share == pytest.approx(0.5)


def test_trimestral_descarta_vacancia_contraditoria():
    content = trimestral([imovel(1000, 1, 0.3), imovel(3000, 0.1, 0.5)])
    assert cvm_fii.parse_quarterly(content, [CNPJ_TIJOLO])["11728688000147"].vacancy == pytest.approx(0.1)


def test_trimestral_sem_area_consistente_suficiente_fica_sem_vacancia():
    content = trimestral([imovel(3000, 1, 0.3), imovel(1000, 0.0, 0.5)])
    assert cvm_fii.parse_quarterly(content, [CNPJ_TIJOLO])["11728688000147"].vacancy is None


@pytest.mark.parametrize("receitas", [(0.7, 0.6), (1.4, 0.1), (-0.1, 0.5)])
def test_trimestral_receita_inconsistente_fica_sem_concentracao(receitas):
    content = trimestral([imovel(1000, 0, receitas[0]), imovel(1000, 0, receitas[1])])
    assert cvm_fii.parse_quarterly(content, [CNPJ_TIJOLO])["11728688000147"].largest_property_share is None


def test_trimestral_maior_credito_ignora_cotas_de_fii():
    q = cvm_fii.parse_quarterly(trimestral([]), [CNPJ_PAPEL])["16706958000132"]
    assert q.largest_credit_value == 460_000_000
    assert q.properties is None
    assert q.vacancy is None


def test_trimestral_sem_credito():
    content = trimestral([imovel(1000, 0, 0.5)], ativos=[f"{CNPJ_TIJOLO};2026-09-30;1;FII;10"])
    assert cvm_fii.parse_quarterly(content, [CNPJ_TIJOLO])["11728688000147"].largest_credit_value is None


def test_zip_sem_geral_nao_quebra():
    vazio = _zip({"outro.csv": b"x"})
    assert cvm_fii.parse_monthly(vazio, ["KNCR11"]) == {}
    assert cvm_fii.parse_quarterly(vazio, [CNPJ_PAPEL]) == {}

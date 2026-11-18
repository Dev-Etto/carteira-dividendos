import pytest

from app.engine.acoes import graham_value
from app.engine.metodos.graham import Graham, max_pe, multiples, profit_growth
from app.engine.types import YearFundamentals
from tests.test_motor_acoes import transmissora


def defensiva(**kw):
    """Transmissora fictícia com balanço completo, lucro crescendo e preço baixo."""
    funds = {
        y: YearFundamentals(
            year=y,
            revenue=3e9,
            net_income=1.0e9 * 1.05 ** (y - 2020),
            equity=8e9,
            gross_debt=5e9,
            cash=2e9,
            current_assets=4e9,
            current_liabilities=2e9,
        )
        for y in range(2020, 2026)
    }
    return transmissora(**({"fundamentals": funds, "price": 10.0, "ntnb_real": 0.07} | kw))


def by_id(ev):
    return {r.id: r for r in ev.rules}


def test_defensiva_barata_e_compra():
    ev = Graham().evaluate_one(defensiva(), {})
    assert ev.verdict == "comprar"
    assert all(r.status == "ok" for r in ev.rules)
    assert ev.ceiling_price == pytest.approx(graham_value(defensiva()))


def test_pl_maximo_ligado_ao_juro_real():
    assert max_pe(defensiva(ntnb_real=0.05), {"graham_pl_ligado_juros": 1, "graham_pl_max": 15})[0] == pytest.approx(20)
    assert max_pe(defensiva(ntnb_real=0.05), {"graham_pl_ligado_juros": 0, "graham_pl_max": 15})[0] == 15
    assert max_pe(defensiva(ntnb_real=None), {"graham_pl_ligado_juros": 1, "graham_pl_max": 15})[0] == 15


def test_cara_manda_aguardar_sem_baixar_a_nota():
    ev = Graham().evaluate_one(defensiva(price=60.0), {})
    assert by_id(ev)["graham-preco"].status == "fail"
    assert ev.verdict == "aguardar"
    assert ev.score == 100


def test_prejuizo_em_um_ano_e_eliminatorio():
    s = defensiva()
    s.fundamentals[2023].net_income = -1e8
    ev = Graham().evaluate_one(s, {})
    assert by_id(ev)["graham-lucro"].status == "fail"
    assert ev.verdict == "evitar"


def test_liquidez_corrente_baixa_reprova_e_banco_nao_passa_por_ela():
    s = defensiva()
    s.fundamentals[2025].current_assets = 1e9
    assert by_id(Graham().evaluate_one(s, {}))["graham-liquidez-corrente"].status == "fail"
    assert "graham-liquidez-corrente" not in by_id(Graham().evaluate_one(defensiva(sector="bancos"), {}))


def test_crescimento_do_lucro():
    rate, start, end = profit_growth(defensiva())
    assert rate == pytest.approx(0.05, abs=1e-6)
    assert (start, end) == (2020, 2025)
    assert profit_growth(defensiva(fundamentals={2025: YearFundamentals(year=2025, net_income=1e9)})) is None


def test_multiplos_usam_lucro_medio_de_3_anos():
    pe, pb = multiples(defensiva())
    avg = sum(1.0e9 * 1.05**k for k in (3, 4, 5)) / 3
    assert pe == pytest.approx(10.0 * 1e9 / avg)
    assert pb == pytest.approx(10.0 * 1e9 / 8e9)
    assert multiples(defensiva(shares_outstanding=None)) is None


def test_empresa_pequena_e_sem_balanco():
    small = defensiva()
    small.fundamentals[2025].revenue = 1e8
    assert by_id(Graham().evaluate_one(small, {}))["graham-tamanho"].status == "fail"
    ev = Graham().evaluate_one(transmissora(fundamentals={}), {})
    assert ev.verdict == "neutro"

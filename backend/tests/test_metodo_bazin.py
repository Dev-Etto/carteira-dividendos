import pytest

from app.engine.config import DEFAULT_RULES, rule_errors
from app.engine.metodos.bazin import Bazin, bazin_ceiling
from app.engine.types import YearFundamentals
from tests.test_motor_acoes import transmissora


def status(ev, rule_id):
    return next(r.status for r in ev.rules if r.id == rule_id)


def test_pagadora_barata_e_compra():
    ev = Bazin().evaluate_one(transmissora(price=34.0, dividends_ttm=4.4), {})
    assert ev.verdict == "comprar"
    assert ev.ceiling_price == pytest.approx(4.4 / 0.06)
    assert status(ev, "bazin-yield") == "ok"
    assert status(ev, "bazin-divida") == "ok"


def test_yield_abaixo_de_6_por_cento_manda_aguardar():
    ev = Bazin().evaluate_one(transmissora(price=100.0, dividends_ttm=4.4), {})
    assert status(ev, "bazin-yield") == "fail"
    assert status(ev, "bazin-venda") == "ok"
    assert ev.verdict == "aguardar"
    assert ev.score == 100


def test_yield_abaixo_de_4_por_cento_so_avisa():
    ev = Bazin().evaluate_one(transmissora(price=200.0, dividends_ttm=4.4), {})
    venda = next(r for r in ev.rules if r.id == "bazin-venda")
    assert (venda.status, venda.weight) == ("warn", 0)


def test_ano_sem_proventos_e_eliminatorio():
    divs = dict.fromkeys(range(2012, 2026), 3.0) | {2024: 0.0}
    ev = Bazin().evaluate_one(transmissora(dividends_by_year=divs), {})
    assert status(ev, "bazin-regularidade") == "fail"
    assert ev.verdict == "evitar"


def test_divida_acima_do_patrimonio_reprova():
    funds = {2025: YearFundamentals(year=2025, equity=1e9, gross_debt=3e9, cash=0.5e9)}
    ev = Bazin().evaluate_one(transmissora(fundamentals=funds), {})
    divida = next(r for r in ev.rules if r.id == "bazin-divida")
    assert divida.status == "fail"
    assert divida.value == pytest.approx(2.5)


def test_banco_nao_passa_pela_regra_de_divida():
    ev = Bazin().evaluate_one(transmissora(sector="bancos"), {})
    assert "bazin-divida" not in {r.id for r in ev.rules}


def test_limites_editaveis():
    ev = Bazin().evaluate_one(transmissora(price=66.0, dividends_ttm=4.4), {"bazin_yield_alvo": 0.07})
    assert status(ev, "bazin-yield") == "fail"
    assert bazin_ceiling(transmissora(dividends_ttm=None), 0.06) is None


def test_sem_preco_fica_sem_veredito():
    ev = Bazin().evaluate_one(transmissora(price=None), {})
    assert ev.verdict == "neutro"


def test_venda_acima_do_alvo_e_inconsistente():
    assert rule_errors({**DEFAULT_RULES, "bazin_yield_venda": 0.08})


def test_yield_ligado_ao_juro_real():
    snap = transmissora(price=34.0, dividends_ttm=2.55, ntnb_real=0.08)
    fixo = Bazin().evaluate_one(snap, {})
    ligado = Bazin().evaluate_one(snap, {"bazin_yield_ligado_juros": 1})
    assert status(fixo, "bazin-yield") == "ok"
    assert status(ligado, "bazin-yield") == "fail"
    assert ligado.ceiling_price == pytest.approx(2.55 / 0.08)

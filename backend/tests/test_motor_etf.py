from dataclasses import replace

import pytest

from app.engine import etf
from app.engine.config import DEFAULT_RULES
from app.engine.etf import evaluate_etf
from app.engine.types import EtfSnapshot

C = DEFAULT_RULES


def divo(**kw) -> EtfSnapshot:
    base = EtfSnapshot(
        ticker="DIVO11",
        name="It Now IDIV",
        price=100.0,
        avg_daily_volume_brl=8_000_000,
        equity=2_800_000_000,
        admin_fee=0.005,
        dividends_ttm=6.0,
    )
    return replace(base, **kw)


def regra(ev, rule_id):
    return next(r for r in ev.rules if r.id == rule_id)


def test_etf_bom_fica_neutro_com_checklist_completo():
    ev = evaluate_etf(divo())
    assert ev.verdict == "neutro"
    assert ev.score == 100
    assert ev.summary.startswith("4 de 4 critérios ok")
    assert ev.dividend_yield == pytest.approx(0.06)
    assert ev.ceiling_price is None


def test_liquidez_baixa_leva_a_evitar():
    ev = evaluate_etf(divo(avg_daily_volume_brl=500_000))
    assert regra(ev, "etf-liquidez").status == "fail"
    assert ev.verdict == "evitar"


def test_etf_que_reinveste_e_alerta_nao_reprovacao():
    r = etf.rule_distribui(divo(dividends_ttm=0.0))
    assert (r.status, r.value_display) == ("warn", "reinveste")


@pytest.mark.parametrize(
    ("rule", "campo", "valores"),
    [
        (etf.rule_liquidez, "avg_daily_volume_brl", (5_000_000, 2_000_000, 900_000)),
        (etf.rule_patrimonio, "equity", (500e6, 200e6, 50e6)),
        (etf.rule_taxa, "admin_fee", (0.005, 0.008, 0.012)),
    ],
)
def test_faixas_ok_warn_fail(rule, campo, valores):
    assert [rule(divo(**{campo: v}), C).status for v in valores] == ["ok", "warn", "fail"]


def test_sem_dados():
    ev = evaluate_etf(EtfSnapshot(ticker="NOVO11", name="Novo"))
    assert all(r.status == "na" for r in ev.rules)
    assert ev.verdict == "neutro"
    assert "insuficientes" in ev.summary


def test_taxa_sem_dado_pede_para_informar():
    assert "Informe a taxa" in etf.rule_taxa(divo(admin_fee=None), C).explanation

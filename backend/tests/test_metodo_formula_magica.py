import pytest

from app.engine.metodos.formula_magica import FormulaMagica, metrics, positions, ranking
from app.engine.types import YearFundamentals
from tests.test_motor_acoes import transmissora


def empresa(ticker, ebit, price=10.0, sector="ciclico", **kw):
    """Empresa fictícia: 1 bi de ações, dívida líquida de 1 bi e capital de 5 bi."""
    f = YearFundamentals(
        year=2025,
        ebit=ebit,
        gross_debt=2e9,
        cash=1e9,
        current_assets=4e9,
        current_liabilities=2e9,
        short_term_debt=0.5e9,
        fixed_assets=3.5e9,
    )
    return transmissora(ticker=ticker, sector=sector, price=price, fundamentals={2025: f}, **kw)


def test_metricas_de_greenblatt():
    m = metrics(empresa("AAAA3", ebit=1.1e9))
    assert m.earnings_yield == pytest.approx(1.1e9 / (10e9 + 1e9))
    assert m.return_on_capital == pytest.approx(1.1e9 / ((4e9 - 1e9) - (2e9 - 0.5e9) + 3.5e9))
    assert metrics(empresa("AAAA3", ebit=1e9, shares_outstanding=None)) is None


def test_ranking_soma_as_posicoes():
    assert positions({"A": 3.0, "B": 5.0, "C": 1.0}) == {"B": 1, "A": 2, "C": 3}
    snaps = [empresa("BOA3", 2e9, price=5.0), empresa("MEIO3", 1e9), empresa("RUIM3", 0.2e9, price=20.0)]
    assert ranking({s.ticker: metrics(s) for s in snaps}) == ["BOA3", "MEIO3", "RUIM3"]


def test_primeiro_terco_compra_e_resto_fica_neutro():
    snaps = [empresa(f"EMP{i}3", ebit=(10 - i) * 1e8) for i in range(6)]
    out = FormulaMagica().evaluate(snaps, {})
    assert [out[s.ticker].verdict for s in snaps] == ["comprar"] * 2 + ["neutro"] * 4
    assert out["EMP03"].score == 100
    assert out["EMP53"].score == 0
    assert "ignora dividendos" in out["EMP03"].summary
    assert all(v.verdict != "evitar" for v in out.values())


def test_setores_excluidos_e_iliquidas_ficam_fora_do_ranking():
    snaps = [
        empresa("BANC4", 5e9, sector="bancos"),
        empresa("LUZZ3", 5e9, sector="energia"),
        empresa("POUC3", 5e9, avg_daily_volume_brl=1e4),
        empresa("BOA3", 1e9),
    ]
    out = FormulaMagica().evaluate(snaps, {})
    assert out["BOA3"].extras["total"] == 1
    assert out["BOA3"].verdict == "comprar"
    assert out["BANC4"].summary.startswith("Setor fora")
    assert out["POUC3"].verdict == "neutro"


def test_sem_balanco_fica_sem_dado():
    out = FormulaMagica().evaluate([transmissora(sector="ciclico", fundamentals={})], {})
    ev = out["TRNS3"]
    assert ev.verdict == "neutro"
    assert ev.rules[0].status == "na"


def test_fracao_editavel():
    snaps = [empresa(f"EMP{i}3", ebit=(10 - i) * 1e8) for i in range(6)]
    out = FormulaMagica().evaluate(snaps, {"fm_fracao_comprar": 0.5})
    assert sum(v.verdict == "comprar" for v in out.values()) == 3

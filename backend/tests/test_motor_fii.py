from dataclasses import replace
from datetime import date

import pytest

from app.engine import fii
from app.engine.config import DEFAULT_RULES
from app.engine.fii import evaluate_fii
from app.engine.types import FiiSnapshot

HOJE = date(2026, 11, 17)
C = DEFAULT_RULES


def papel(**kw) -> FiiSnapshot:
    """FII de papel saudável: grande, líquido, antigo, rendendo um pouco acima do CDI líquido."""
    base = FiiSnapshot(
        ticker="KNCR11",
        name="Kinea Rendimentos",
        kind="papel",
        today=HOJE,
        price=100.0,
        avg_daily_volume_brl=20_000_000,
        equity=12_000_000_000,
        nav_per_share=100.0,
        holders=600_000,
        listed=True,
        started_on=date(2012, 10, 15),
        admin_fee_month=0.00075,
        dividends_ttm=12.5,
        dividends_prev_ttm=12.0,
        cdi=0.1365,
        ntnb_real=0.075,
        largest_credit_share=0.04,
    )
    return replace(base, **kw)


def tijolo(**kw) -> FiiSnapshot:
    base = replace(
        papel(),
        ticker="HGLG11",
        name="Pátria Log",
        kind="tijolo",
        price=160.0,
        nav_per_share=165.0,
        dividends_ttm=14.0,
        dividends_prev_ttm=13.8,
        largest_credit_share=None,
        largest_property_share=0.08,
        properties=36,
        vacancy=0.05,
    )
    return replace(base, **kw)


def regra(ev, rule_id):
    return next(r for r in ev.rules if r.id == rule_id)


def test_papel_saudavel_e_comprar():
    ev = evaluate_fii(papel())
    assert ev.verdict == "comprar"
    assert ev.score == 100
    assert ev.ceiling_price == pytest.approx(108.0)
    assert ev.margin_pct == pytest.approx((108 - 100) / 108)
    assert ev.dividend_yield == pytest.approx(0.125)
    assert ev.extras["tipo"] == "papel"
    assert {r.id for r in ev.rules} >= {"fii-concentracao-credito"}
    assert "fii-vacancia" not in {r.id for r in ev.rules}


def test_tijolo_tem_regras_de_imoveis():
    ev = evaluate_fii(tijolo())
    ids = {r.id for r in ev.rules}
    assert {"fii-concentracao-imovel", "fii-imoveis", "fii-vacancia"} <= ids
    assert "fii-concentracao-credito" not in ids
    assert ev.verdict == "comprar"


def test_fof_sem_regras_de_carteira():
    ids = {r.id for r in evaluate_fii(tijolo(kind="fof")).rules}
    assert not ids & {"fii-concentracao-imovel", "fii-imoveis", "fii-vacancia", "fii-concentracao-credito"}


@pytest.mark.parametrize(
    ("campo", "valor", "rule_id"),
    [
        ("equity", 300_000_000, "fii-patrimonio"),
        ("avg_daily_volume_brl", 500_000, "fii-liquidez"),
        ("started_on", date(2024, 1, 1), "fii-historico"),
    ],
)
def test_eliminatorias_levam_a_evitar(campo, valor, rule_id):
    ev = evaluate_fii(papel(**{campo: valor}))
    assert regra(ev, rule_id).status == "fail"
    assert ev.verdict == "evitar"


def test_caro_pelo_pvp_aguarda():
    ev = evaluate_fii(papel(price=115.0, dividends_ttm=14.4))
    assert regra(ev, "fii-preco").status == "fail"
    assert ev.verdict == "aguardar"


@pytest.mark.parametrize(
    ("kind", "pvp", "status"),
    [
        ("papel", 0.85, "ok"),
        ("papel", 0.80, "warn"),
        ("papel", 0.74, "fail"),
        ("tijolo", 0.72, "warn"),
        ("tijolo", 0.69, "fail"),
    ],
)
def test_desconto_por_tipo(kind, pvp, status):
    snap = tijolo(kind=kind, price=100.0 * pvp, nav_per_share=100.0)
    assert regra(evaluate_fii(snap), "fii-desconto").status == status


@pytest.mark.parametrize(("kind", "pvp", "status"), [("papel", 1.08, "ok"), ("papel", 1.09, "fail"), ("tijolo", 1.12, "ok")])
def test_limite_de_preco_por_tipo(kind, pvp, status):
    snap = tijolo(kind=kind, price=100.0 * pvp, nav_per_share=100.0)
    assert regra(evaluate_fii(snap), "fii-preco").status == status


@pytest.mark.parametrize(
    ("dy", "status"),
    [(0.12, "ok"), (0.19, "warn"), (0.11, "warn"), (0.09, "fail")],
)
def test_spread_papel_contra_cdi_liquido(dy, status):
    cdi_liquido = 0.1365 * 0.85
    assert cdi_liquido == pytest.approx(0.116025)
    ev = evaluate_fii(papel(dividends_ttm=dy * 100))
    assert regra(ev, "fii-rendimento").status == status


@pytest.mark.parametrize(("dy", "status"), [(0.09, "ok"), (0.08, "warn"), (0.07, "fail")])
def test_spread_tijolo_contra_ntnb(dy, status):
    ev = evaluate_fii(tijolo(price=100.0, nav_per_share=100.0, dividends_ttm=dy * 100))
    assert regra(ev, "fii-rendimento").status == status


@pytest.mark.parametrize(("ttm", "prev", "status"), [(12.0, 12.0, "ok"), (10.0, 12.0, "warn"), (8.0, 12.0, "fail")])
def test_estabilidade(ttm, prev, status):
    assert regra(evaluate_fii(papel(dividends_ttm=ttm, dividends_prev_ttm=prev)), "fii-estabilidade").status == status


def test_isencao_exige_bolsa_e_cotistas():
    assert regra(evaluate_fii(papel(holders=80)), "fii-isencao").status == "fail"
    assert regra(evaluate_fii(papel(listed=False)), "fii-isencao").status == "fail"
    assert regra(evaluate_fii(papel()), "fii-isencao").status == "ok"


@pytest.mark.parametrize(
    ("rule", "campo", "valores"),
    [
        (fii.rule_taxa_adm, "admin_fee_month", (0.009 / 12, 0.014 / 12, 0.02 / 12)),
        (fii.rule_credito, "largest_credit_share", (0.06, 0.09, 0.11)),
        (fii.rule_concentracao_imovel, "largest_property_share", (0.25, 0.30, 0.45)),
        (fii.rule_imoveis, "properties", (8, 5, 3)),
        (fii.rule_vacancia, "vacancy", (0.10, 0.15, 0.25)),
    ],
)
def test_faixas_ok_warn_fail(rule, campo, valores):
    statuses = [rule(tijolo(**{campo: v}), C).status for v in valores]
    assert statuses == ["ok", "warn", "fail"]


def test_sem_informe_fica_sem_dado_e_neutro():
    vazio = FiiSnapshot(ticker="NOVO11", name="Novo", kind="tijolo", today=HOJE)
    ev = evaluate_fii(vazio)
    assert all(r.status == "na" for r in ev.rules)
    assert ev.verdict == "neutro"
    assert ev.ceiling_price is None


def test_limites_sobrescritos():
    ev = evaluate_fii(papel(equity=400_000_000), {"fii_pl_min": 300_000_000})
    assert regra(ev, "fii-patrimonio").status == "ok"


@pytest.mark.parametrize(
    ("paper", "brick", "fof", "kind"),
    [
        (0.66, 0.15, 0.12, "papel"),
        (0.0, 0.97, 0.01, "tijolo"),
        (0.01, 0.8, 0.18, "tijolo"),
        (0.05, 0.05, 0.85, "fof"),
        (0.45, 0.45, 0.0, "hibrido"),
        (0.0, 0.0, 0.0, "hibrido"),
    ],
)
def test_classifica_pela_composicao(paper, brick, fof, kind):
    assert fii.classify(paper, brick, fof) == kind

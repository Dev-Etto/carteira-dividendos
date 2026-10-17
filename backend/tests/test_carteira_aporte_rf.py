from datetime import date
from decimal import Decimal

import pytest

from app.engine.aporte import Candidate, build_plan, split_by_class
from app.engine.carteira import SplitEvent, Tx, compute_position, entitled_income, quantity_on
from app.engine.perfil import profile_from_answers
from app.engine.renda_fixa import (
    check_reserve_eligibility,
    exempt_equivalent,
    ir_rate,
    net_annual_rate,
    taxed_equivalent,
)

D = Decimal


def test_preco_medio_inclui_taxas_e_venda_nao_altera():
    txs = [
        Tx(date(2026, 1, 5), "compra", D(10), D(20), D(1)),
        Tx(date(2026, 2, 5), "compra", D(10), D(30), D(1)),
        Tx(date(2026, 3, 5), "venda", D(5), D(40), D(0)),
    ]
    p = compute_position(txs)
    assert p.quantity == 15
    custo_com_taxas = D(200 + 1 + 300 + 1)
    assert p.avg_price == (custo_com_taxas / 20).quantize(D("0.0001"))
    assert p.avg_price == D("25.1000")
    assert p.realized_profit == D(5 * 40) - D(5) * D("25.1")


def test_desdobramento_preserva_custo():
    txs = [Tx(date(2025, 1, 2), "compra", D(100), D(50))]
    p = compute_position(txs, [SplitEvent(date(2025, 6, 1), D(2))])
    assert p.quantity == 200
    assert p.avg_price == D(25)
    assert p.total_cost == D(5000)


def test_grupamento():
    txs = [Tx(date(2025, 1, 2), "compra", D(1000), D(1))]
    p = compute_position(txs, [SplitEvent(date(2025, 6, 1), D("0.1"))])
    assert p.quantity == 100
    assert p.avg_price == D(10)


def test_venda_maior_que_posicao_falha():
    with pytest.raises(ValueError, match="maior que a posição"):
        compute_position([Tx(date(2025, 1, 2), "compra", D(1), D(10)), Tx(date(2025, 1, 3), "venda", D(2), D(10))])


def test_quantidade_na_data_com():
    txs = [Tx(date(2025, 1, 2), "compra", D(10), D(10)), Tx(date(2025, 3, 2), "compra", D(5), D(10))]
    assert quantity_on(txs, [], date(2025, 2, 1)) == 10
    assert quantity_on(txs, [], date(2025, 3, 2)) == 15


def test_provento_so_conta_quem_tinha_na_data_com():
    """Data ex 10/03: tem direito quem tinha a ação no fim de 09/03."""
    divs = [(date(2025, 3, 10), 1.0)]
    comprou_antes = [Tx(date(2025, 3, 9), "compra", D(100), D(10))]
    comprou_na_data_ex = [Tx(date(2025, 3, 10), "compra", D(100), D(10))]
    assert entitled_income(comprou_antes, [], divs) == 100
    assert entitled_income(comprou_na_data_ex, [], divs) == 0


def test_provento_vendido_antes_nao_conta():
    txs = [Tx(date(2025, 1, 2), "compra", D(100), D(10)), Tx(date(2025, 3, 1), "venda", D(100), D(12))]
    assert entitled_income(txs, [], [(date(2025, 3, 10), 1.0)]) == 0


def test_provento_ajustado_por_desdobramento_posterior():
    """100 ações na data-com e desdobramento 1:2 depois: o Yahoo informa o provento já dividido por 2."""
    txs = [Tx(date(2025, 1, 2), "compra", D(100), D(10))]
    splits = [SplitEvent(date(2025, 6, 1), D(2))]
    assert entitled_income(txs, splits, [(date(2025, 3, 10), 0.5)]) == 100


@pytest.mark.parametrize(("days", "rate"), [(100, 0.225), (180, 0.225), (181, 0.20), (400, 0.175), (800, 0.15)])
def test_ir_regressivo(days, rate):
    assert ir_rate(days) == rate


def test_equivalencia_isento_tributado():
    """CDB de 14% bruto por mais de 2 anos rende 11,9% líquido; uma LCI precisa pagar 11,9%."""
    assert abs(exempt_equivalent(0.14, 800) - 0.119) < 1e-9
    assert abs(taxed_equivalent(0.119, 800) - 0.14) < 1e-9
    assert net_annual_rate(0.12, "lci", 100) == 0.12


def test_reserva_so_aceita_liquidez_diaria():
    assert check_reserve_eligibility("tesouro", "selic", True, 0, True).ok
    assert not check_reserve_eligibility("cdb", "cdi", False, 110, True).ok
    assert not check_reserve_eligibility("cdb", "pre", True, 13, True).ok
    assert not check_reserve_eligibility("cdb", "cdi", True, 95, True).ok
    assert check_reserve_eligibility("cdb", "cdi", True, 100, True).ok


def test_perfil_por_pontos():
    assert profile_from_answers({"a": 0, "b": 1, "c": 1}) == "conservador"
    assert profile_from_answers({"a": 1, "b": 1, "c": 2, "d": 1, "e": 1}) == "moderado"
    assert profile_from_answers({"a": 2, "b": 2, "c": 2, "d": 1, "e": 2}) == "arrojado"


TARGETS = {"renda_fixa": 30.0, "fiis": 30.0, "acoes": 35.0, "etfs": 5.0}


def cands():
    return [
        Candidate("TAEE11", "Taesa", 35.0, 85, 0.20, "energia"),
        Candidate("BBSE3", "BB Seguridade", 33.0, 80, 0.15, "seguros"),
        Candidate("ITUB4", "Itaú", 36.0, 78, 0.12, "bancos"),
    ]


def test_aporte_completa_reserva_primeiro():
    plan = build_plan(
        amount=1000, reserve_current=2000, reserve_target=10000, class_current={}, targets=TARGETS, stock_candidates=cands()
    )
    assert len(plan.lines) == 1
    assert plan.lines[0].asset_class == "reserva"
    assert plan.lines[0].amount == 1000


def test_aporte_divide_por_deficit_e_nao_estoura_valor():
    plan = build_plan(
        amount=3000,
        reserve_current=10000,
        reserve_target=10000,
        class_current={"renda_fixa": 0, "acoes": 0, "fiis": 0, "etfs": 0},
        targets=TARGETS,
        stock_candidates=cands(),
    )
    assert abs(sum(ln.amount for ln in plan.lines) - 3000) < 0.01
    stocks = [ln for ln in plan.lines if ln.asset_class == "acoes"]
    assert stocks, plan
    assert all(ln.quantity and ln.quantity >= 1 for ln in stocks)
    nota_fiis_sem_motor = any("FIIs" in n for n in plan.notes)
    assert nota_fiis_sem_motor


def test_aporte_pequeno_diversifica_sem_estourar_limite():
    plan = build_plan(
        amount=300,
        reserve_current=10000,
        reserve_target=10000,
        class_current={"renda_fixa": 0, "acoes": 0, "fiis": 0, "etfs": 0},
        targets={"acoes": 100.0, "renda_fixa": 0, "fiis": 0, "etfs": 0},
        stock_candidates=cands(),
    )
    stocks = [ln for ln in plan.lines if ln.asset_class == "acoes"]
    um_ativo_por_setor = 3
    limite_por_ativo_no_inicio = 300 * 0.20
    assert len({ln.ticker for ln in stocks}) == len(stocks) == um_ativo_por_setor
    assert all(ln.amount <= limite_por_ativo_no_inicio for ln in stocks)


def test_aporte_muito_pequeno_concentra_no_melhor_ativo_novo():
    plan = build_plan(
        amount=40,
        reserve_current=10000,
        reserve_target=10000,
        class_current={"renda_fixa": 0, "acoes": 0, "fiis": 0, "etfs": 0},
        targets={"acoes": 100.0, "renda_fixa": 0, "fiis": 0, "etfs": 0},
        stock_candidates=cands(),
    )
    stocks = [ln for ln in plan.lines if ln.asset_class == "acoes"]
    assert len(stocks) == 1
    assert stocks[0].ticker == "TAEE11"


def test_split_por_classe_sem_deficit_usa_pesos():
    out = split_by_class(100, {"a": 50, "b": 50}, {"a": 50, "b": 50}, 100)
    assert out == {"a": 50.0, "b": 50.0}


def test_caixa_explica_de_onde_vem_o_dinheiro():
    """Sem ações com veredito "comprar", a verba de ações e a de FIIs ficam em caixa, cada uma explicada."""
    plan = build_plan(
        amount=1000,
        reserve_current=0,
        reserve_target=0,
        class_current={"renda_fixa": 0, "acoes": 0, "fiis": 0, "etfs": 0},
        targets={"renda_fixa": 0, "acoes": 50, "fiis": 50, "etfs": 0},
        stock_candidates=[],
    )
    [caixa] = [ln for ln in plan.lines if ln.asset_class == "caixa"]
    assert caixa.amount == 1000
    assert "ações sem veredito 'comprar' hoje: R$ 500,00" in caixa.reason
    assert "FIIs aguardando o motor da próxima fase: R$ 500,00" in caixa.reason
    assert "sobra que não fecha uma cota" not in caixa.reason


def test_caixa_com_sobra_de_arredondamento():
    plan = build_plan(
        amount=100,
        reserve_current=0,
        reserve_target=0,
        class_current={"acoes": 0},
        targets={"acoes": 100},
        stock_candidates=[Candidate("TAEE11", "Taesa", 30.0, 90, 0.2, "energia")],
    )
    [caixa] = [ln for ln in plan.lines if ln.asset_class == "caixa"]
    assert caixa.reason == "sobra que não fecha uma cota: R$ 10,00. Entra no próximo aporte."

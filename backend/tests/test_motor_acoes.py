import math
from typing import Any

import pytest

from app.engine import acoes
from app.engine.acoes import ceiling_price, consecutive_paying_years, evaluate_stock, percentile_of
from app.engine.config import DEFAULT_RULES, merged_rules, rule_errors
from app.engine.types import StockSnapshot, YearFundamentals


def transmissora(**kw: Any) -> StockSnapshot:
    """Empresa fictícia no perfil de uma boa transmissora de energia."""
    divs = {y: 3.0 + 0.1 * (y - 2012) for y in range(2012, 2026)}
    funds = {
        y: YearFundamentals(
            year=y,
            revenue=3e9,
            ebit=1.6e9 + (y - 2020) * 1e7,
            depreciation=1e8,
            net_income=1.1e9,
            equity=6e9,
            gross_debt=7e9,
            cash=2e9,
            operating_cash_flow=1.7e9,
            investing_cash_flow=-0.2e9,
            dividends_paid=-0.8e9,
        )
        for y in range(2020, 2026)
    }
    base = {
        "ticker": "TRNS3",
        "name": "Transmissora Exemplo",
        "sector": "energia",
        "segment": "transmissao",
        "price": 34.0,
        "avg_daily_volume_brl": 40e6,
        "shares_outstanding": 1e9,
        "dividends_by_year": divs,
        "dividends_ttm": 4.4,
        "avg_price_by_year": dict.fromkeys(range(2012, 2026), 36.0),
        "fundamentals": funds,
        "sector_metrics": {"concessao_anos": 18},
        "pe_history": [40.0 - i * 0.1 for i in range(60)],
        "pb_history": [],
        "current_year": 2026,
    }
    base.update(kw)
    return StockSnapshot(**base)  # type: ignore[arg-type]


def rule(ev, rid):  # type: ignore[no-untyped-def]
    return next(r for r in ev.rules if r.id == rid)


def test_boa_empresa_barata_recebe_comprar():
    ev = evaluate_stock(transmissora())
    assert ev.verdict == "comprar", ev.summary
    assert ev.score >= 70
    media_proventos_2021_2025 = 4.1
    yield_alvo = 0.06
    assert abs(ev.ceiling_price - media_proventos_2021_2025 / yield_alvo) < 0.01
    assert rule(ev, "historico-proventos").status == "ok"
    assert rule(ev, "segmento-energia").status == "ok"
    assert rule(ev, "concessao").status == "ok"


def test_mesma_empresa_cara_recebe_aguardar():
    ev = evaluate_stock(transmissora(price=80.0))
    assert rule(ev, "preco-teto").status == "fail"
    assert ev.verdict == "aguardar"


def test_liquidez_baixa_elimina():
    ev = evaluate_stock(transmissora(avg_daily_volume_brl=300_000))
    assert rule(ev, "liquidez").status == "fail"
    assert ev.verdict == "evitar"
    assert "eliminatória" in ev.summary


def test_historico_curto_elimina():
    divs = {2022: 1.0, 2023: 1.0, 2024: 1.0, 2025: 1.0}
    ev = evaluate_stock(transmissora(dividends_by_year=divs))
    assert consecutive_paying_years(transmissora(dividends_by_year=divs)) == 4
    assert rule(ev, "historico-proventos").status == "fail"
    assert ev.verdict == "evitar"


def test_sem_dados_fica_neutro_e_nao_inventa():
    snap = StockSnapshot(ticker="NOVO3", name="Sem dados", sector="bancos")
    ev = evaluate_stock(snap)
    assert ev.verdict == "neutro"
    assert all(r.status in ("na", "ok", "warn", "fail") for r in ev.rules)
    assert rule(ev, "preco-teto").status == "na"


def test_bancos_nao_usam_divida_ebitda_e_usam_basileia():
    ev = evaluate_stock(transmissora(sector="bancos", segment=None, sector_metrics={"basileia": 14.5}))
    ids = {r.id for r in ev.rules}
    assert "endividamento" not in ids
    assert "cobertura-caixa" not in ids
    assert rule(ev, "basileia").status == "ok"
    assert rule(ev, "inadimplencia").status == "na"


def test_payout_acima_de_100_reprova():
    funds = transmissora().fundamentals
    for f in funds.values():
        f.dividends_paid = -1.5e9
    ev = evaluate_stock(transmissora(fundamentals=funds))
    assert rule(ev, "payout-5a").status == "fail"


def test_dy_anormal_alerta_provento_extraordinario():
    ev = evaluate_stock(transmissora(dividends_ttm=12.0))
    assert rule(ev, "dy-anormal").status == "fail"


def test_divida_alta_em_setor_alavancado():
    funds = transmissora().fundamentals
    funds[2025].gross_debt = 9e9
    funds[2025].cash = 0.5e9
    ev = evaluate_stock(transmissora(fundamentals=funds))
    r = rule(ev, "endividamento")
    divida_liquida, ebitda, limite_setor_regulado = 8.5e9, 1.75e9, 4.0
    assert divida_liquida / ebitda > limite_setor_regulado
    assert r.status == "fail"


def test_regras_configuraveis_mudam_o_teto():
    ev = evaluate_stock(transmissora(), {"yield_alvo": 0.08})
    assert abs(ev.ceiling_price - 4.1 / 0.08) < 0.01


def test_teto_precisa_de_3_anos():
    assert ceiling_price(transmissora(dividends_by_year={2025: 1.0}), 0.06) is None


def test_percentil():
    assert percentile_of(5, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]) == 50.0


def test_explicacoes_em_portugues_e_sem_campos_vazios():
    ev = evaluate_stock(transmissora())
    for r in ev.rules:
        assert r.explanation
        assert r.label
        assert r.threshold


C = DEFAULT_RULES


@pytest.mark.parametrize(
    ("assess", "args", "status"),
    [
        (acoes._avalia_setor, ("perene", "Perene"), "warn"),
        (acoes._avalia_setor, ("ciclico", "Cíclico"), "fail"),
        (acoes._avalia_historico, (7, C), "warn"),
        (acoes._avalia_historico, (2, C), "fail"),
        (acoes._avalia_consistencia, ([2023],), "warn"),
        (acoes._avalia_consistencia, ([2022, 2024],), "fail"),
        (acoes._avalia_lucro, ([2023], 5), "warn"),
        (acoes._avalia_lucro, ([2022, 2023], 5), "fail"),
        (acoes._avalia_roe, (0.15, C), "ok"),
        (acoes._avalia_roe, (0.10, C), "warn"),
        (acoes._avalia_roe, (0.0999, C), "fail"),
        (acoes._avalia_endividamento, (2.0, 2.0, 3.0), "warn"),
        (acoes._avalia_endividamento, (3.0, 2.0, 3.0), "warn"),
        (acoes._avalia_endividamento, (3.01, 2.0, 3.0), "fail"),
        (acoes._avalia_payout, (0.40, C), "ok"),
        (acoes._avalia_payout, (0.39, C), "warn"),
        (acoes._avalia_payout, (1.0, C), "warn"),
        (acoes._avalia_payout, (1.01, C), "fail"),
        (acoes._avalia_liquidez, (5e6, C), "ok"),
        (acoes._avalia_liquidez, (1e6, C), "warn"),
        (acoes._avalia_liquidez, (9.9e5, C), "fail"),
        (acoes._avalia_preco_teto, (10.0, 10.5, 0.05, C), "warn"),
        (acoes._avalia_preco_teto, (11.0, 10.0, -0.1, C), "fail"),
        (acoes._avalia_dy_anormal, (1.5, C), "warn"),
        (acoes._avalia_dy_anormal, (2.0, C), "warn"),
        (acoes._avalia_dy_anormal, (2.01, C), "fail"),
        (acoes._avalia_barato_si, (30, "P/L", C), "ok"),
        (acoes._avalia_barato_si, (70, "P/L", C), "warn"),
        (acoes._avalia_barato_si, (71, "P/L", C), "fail"),
        (acoes._avalia_cobertura, (1.2, C), "ok"),
        (acoes._avalia_cobertura, (0.9, C), "warn"),
        (acoes._avalia_cobertura, (0.89, C), "fail"),
    ],
)
def test_faixas_de_cada_regra(assess, args, status):
    got, explanation = assess(*args)
    assert got == status
    assert explanation


@pytest.mark.parametrize(
    ("ok", "warn", "status"), [(True, True, "ok"), (True, False, "ok"), (False, True, "warn"), (False, False, "fail")]
)
def test_grade(ok, warn, status):
    assert acoes.grade(ok, warn) == status


@pytest.mark.parametrize(
    ("start", "end", "growth"), [(100.0, 150.0, 0.5), (-100.0, -50.0, 0.5), (0.0, 10.0, math.inf), (0.0, 0.0, 0)]
)
def test_crescimento_da_divida(start, end, growth):
    assert acoes._debt_growth(start, end) == growth


def _setorial(sector: str, metrics: dict[str, float], segment: str | None = None) -> dict[str, str]:
    snap = StockSnapshot(ticker="X", name="X", sector=sector, segment=segment, sector_metrics=metrics)
    return {r.id: r.status for r in acoes.setoriais(snap, C)}


def test_regras_setoriais_por_setor():
    assert _setorial("telecom", {}) == {}
    assert _setorial("bancos", {}) == {"basileia": "na", "inadimplencia": "na"}
    assert _setorial("bancos", {"basileia": 13, "inadimplencia": 3.0, "inadimplencia_sistema": 3.0}) == {
        "basileia": "ok",
        "inadimplencia": "ok",
    }
    assert _setorial("bancos", {"basileia": 11, "inadimplencia": 4.0, "inadimplencia_sistema": 3.0}) == {
        "basileia": "warn",
        "inadimplencia": "warn",
    }
    assert _setorial("bancos", {"basileia": 10.9, "inadimplencia": 4.1, "inadimplencia_sistema": 3.0}) == {
        "basileia": "fail",
        "inadimplencia": "fail",
    }
    assert _setorial("seguros", {}) == {"indice-combinado": "na"}
    assert _setorial("seguros", {"indice_combinado": 84.9}) == {"indice-combinado": "ok"}
    assert _setorial("seguros", {"indice_combinado": 95}) == {"indice-combinado": "warn"}
    assert _setorial("seguros", {"indice_combinado": 95.1}) == {"indice-combinado": "fail"}
    assert _setorial("energia", {}, None) == {"segmento-energia": "na", "concessao": "na"}
    assert _setorial("energia", {"concessao_anos": 10}, "geracao") == {"segmento-energia": "warn", "concessao": "warn"}
    assert _setorial("saneamento", {"concessao_anos": 11}) == {"concessao": "ok"}
    assert _setorial("saneamento", {"concessao_anos": 4}) == {"concessao": "fail"}


def test_limites_padrao_sao_consistentes():
    assert rule_errors(merged_rules(None)) == []


def test_limites_inconsistentes():
    errors = rule_errors(merged_rules({"roe_min": 0.2, "yield_alvo": 0, "liquidez_min": -1}))
    assert "roe_min (0.2) não pode ser maior que roe_ok (0.15)" in errors
    assert "yield_alvo precisa ser maior que zero" in errors
    assert "liquidez_min não pode ser negativo" in errors


def test_yield_alvo_ligado_ao_juro_real():
    assert acoes.linked_yield(0.06, 0, 0.08) == 0.06
    assert acoes.linked_yield(0.06, 1, 0.08) == 0.08
    assert acoes.linked_yield(0.06, 1, 0.04) == 0.06
    assert acoes.linked_yield(0.06, 1, None) == 0.06
    fixo = evaluate_stock(transmissora(ntnb_real=0.08))
    ligado = evaluate_stock(transmissora(ntnb_real=0.08), {"yield_ligado_juros": 1})
    assert ligado.ceiling_price == pytest.approx(fixo.ceiling_price * 0.06 / 0.08)
    assert ligado.extras["yield_alvo_exigente"] >= ligado.extras["yield_alvo"]

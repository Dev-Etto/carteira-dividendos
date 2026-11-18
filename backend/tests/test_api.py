"""Testes ponta a ponta da API com banco temporário (sem rede)."""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.models import Asset, Dividend, Fundamental, PriceDaily
from app.db.session import SessionLocal
from app.engine.metodos.base import MethodInfo, MetodoPorAtivo
from app.engine.metodos.registro import SELECTION_METHODS
from app.engine.types import Evaluation
from app.main import app
from app.services.evaluation import evaluate_all


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        db = SessionLocal()
        a = db.scalar(select(Asset).where(Asset.ticker == "TAEE11"))
        a.last_price, a.shares_outstanding = 34.0, 1e9
        today = date.today()
        for i in range(120):
            db.add(PriceDaily(asset_id=a.id, date=today - timedelta(days=i), close=34.0, volume=1_500_000, source="t"))
        for y in range(today.year - 13, today.year):
            db.add(Dividend(asset_id=a.id, ex_date=date(y, 6, 1), amount=3.9 + 0.05 * (y - today.year + 13), source="t"))
        db.add(Dividend(asset_id=a.id, ex_date=today - timedelta(days=30), amount=4.2, source="t"))
        for y in range(today.year - 6, today.year):
            db.add(
                Fundamental(
                    asset_id=a.id,
                    year=y,
                    revenue=3e9,
                    ebit=1.6e9,
                    depreciation=1e8,
                    net_income=1.1e9,
                    equity=6e9,
                    gross_debt=7e9,
                    cash=2e9,
                    operating_cash_flow=1.7e9,
                    investing_cash_flow=-2e8,
                    dividends_paid=-8e8,
                )
            )
        db.commit()
        evaluate_all(db)
        db.close()
        yield c


def test_health(client):
    assert client.get("/api/health").json()["status"] == "ok"


def test_universo_carregado_e_avaliado(client):
    rows = client.get("/api/ativos", params={"classe": "acao"}).json()
    assert len(rows) >= 30
    taee = next(r for r in rows if r["ticker"] == "TAEE11")
    assert taee["verdict"] in ("comprar", "aguardar")
    assert taee["ceiling_price"] > 0


def test_ficha_explica_regras(client):
    d = client.get("/api/ativos/TAEE11").json()
    assert d["rules"]
    assert all(r["explanation"] for r in d["rules"])
    assert d["risks"]
    assert d["data_sources"]["Avaliação"]
    h = client.get("/api/ativos/TAEE11/historico").json()
    assert h["prices"]
    assert h["dividends_by_year"]


def test_onboarding_e_perfil(client):
    qs = client.get("/api/perfil/questionario").json()
    answers = {q["id"]: 1 for q in qs}
    r = client.put(
        "/api/perfil",
        json={
            "answers": answers,
            "income_stability": "instavel",
            "monthly_expenses": "3000",
            "monthly_contribution": "1000",
            "passive_income_goal": "2000",
        },
    )
    assert r.status_code == 200, r.text
    p = r.json()
    assert p["risk_profile"] == "moderado"
    assert p["emergency_months"] == 12
    assert float(p["emergency_target"]) == 36000
    alloc = client.get("/api/alocacao").json()
    assert abs(sum(i["weight_pct"] for i in alloc) - 100) < 0.01


def test_painel_aponta_reserva(client):
    d = client.get("/api/painel").json()
    assert d["next_step"]["href"] in ("/config", "/renda-fixa")


def test_renda_fixa_e_reserva(client):
    r = client.post(
        "/api/renda-fixa",
        json={
            "name": "Tesouro Selic 2031",
            "issuer": "Tesouro Nacional",
            "kind": "tesouro",
            "indexer": "selic",
            "rate": 0,
            "start_date": "2026-11-01",
            "daily_liquidity": True,
            "amount": "36000",
            "is_emergency_reserve": True,
        },
    )
    assert r.status_code == 201
    assert r.json()["reserve_ok"]
    cmp = client.post("/api/renda-fixa/comparar", json={"kind": "lci", "indexer": "cdi", "rate": 92, "days": 400}).json()
    assert cmp["tax_exempt"]
    assert cmp["equivalent_rate"] > cmp["net_annual"]


def test_aporte_e_operacoes(client):
    plan = client.post("/api/aporte/plano", json={"amount": 2000}).json()
    assert abs(sum(ln["amount"] for ln in plan["lines"]) - 2000) < 0.01
    r = client.post(
        "/api/transacoes",
        json={
            "ticker": "TAEE11",
            "date": date.today().isoformat(),
            "kind": "compra",
            "quantity": "10",
            "price": "34",
            "fees": "0",
        },
    )
    assert r.status_code == 201, r.text
    bad = client.post(
        "/api/transacoes",
        json={"ticker": "TAEE11", "date": date.today().isoformat(), "kind": "venda", "quantity": "50", "price": "34"},
    )
    assert bad.status_code == 422
    cart = client.get("/api/carteira").json()
    pos = cart["positions"][0]
    assert pos["ticker"] == "TAEE11"
    assert pos["quantity"] == 10
    assert pos["avg_price"] == 34
    assert cart["reserve_value"] == 36000


def test_regras_editaveis_reavaliam(client):
    before = client.get("/api/ativos/TAEE11").json()["ceiling_price"]
    r = client.put("/api/regras", json={"yield_alvo": 0.08})
    assert r.status_code == 200
    after = client.get("/api/ativos/TAEE11").json()["ceiling_price"]
    assert after < before
    client.put("/api/regras", json={"yield_alvo": 0.06})


def test_proventos_12m_so_contam_com_direito(client):
    """TAEE11 foi comprada hoje (test_aporte_e_operacoes); o último provento foi há 30 dias."""
    pos = next(p for p in client.get("/api/carteira").json()["positions"] if p["ticker"] == "TAEE11")
    assert pos["income_12m"] == 0
    assert pos["yield_on_cost"] == 0


SELIC_RESERVA = {
    "name": "Tesouro Selic",
    "issuer": "Tesouro Nacional",
    "kind": "tesouro",
    "indexer": "selic",
    "rate": 0,
    "start_date": date.today().isoformat(),
    "daily_liquidity": True,
    "amount": "500",
    "is_emergency_reserve": True,
}


def test_registrar_aporte_com_compras_e_aplicacoes(client):
    hoje = date.today().isoformat()
    compra = {"ticker": "taee11", "quantity": "5", "price": "33.5", "fees": "0"}
    reserva_antes = client.get("/api/carteira").json()["reserve_value"]
    r = client.post("/api/aporte/registrar", json={"date": hoje, "purchases": [compra], "holdings": [SELIC_RESERVA]})
    assert r.status_code == 201, r.text
    body = r.json()
    [tx] = body["transactions"]
    assert tx["ticker"] == "TAEE11"
    assert tx["kind"] == "compra"
    assert tx["origin"] == "aporte"
    [holding] = body["holdings"]
    assert holding["reserve_ok"] is True
    assert client.get("/api/carteira").json()["reserve_value"] == reserva_antes + 500


def test_registrar_aporte_valida_e_nao_grava_pela_metade(client):
    antes_tx = len(client.get("/api/transacoes").json())
    antes_rf = len(client.get("/api/renda-fixa").json())
    futuro = (date.today() + timedelta(days=1)).isoformat()
    hoje = date.today().isoformat()
    compra = {"ticker": "TAEE11", "quantity": "1", "price": "34"}
    assert client.post("/api/aporte/registrar", json={"date": futuro, "purchases": [compra]}).status_code == 422
    vazio = client.post("/api/aporte/registrar", json={"date": hoje})
    assert vazio.status_code == 422
    assert "Nada para registrar" in vazio.text
    r = client.post(
        "/api/aporte/registrar",
        json={"date": hoje, "purchases": [compra, {**compra, "ticker": "XPTO3"}], "holdings": [SELIC_RESERVA]},
    )
    assert r.status_code == 404
    assert "XPTO3" in r.json()["detail"]
    assert len(client.get("/api/transacoes").json()) == antes_tx
    assert len(client.get("/api/renda-fixa").json()) == antes_rf


def test_plano_traz_aplicacao_pronta_para_linhas_de_renda_fixa(client):
    plan = client.post("/api/aporte/plano", json={"amount": 100_000}).json()
    selic = [ln for ln in plan["lines"] if ln["asset_class"] in ("reserva", "caixa")]
    stocks = [ln for ln in plan["lines"] if ln["ticker"]]
    assert all(ln["holding"] is None for ln in stocks)
    assert all(ln["holding"]["indexer"] == "selic" for ln in selic)
    assert all(float(ln["holding"]["amount"]) == round(ln["amount"], 2) for ln in selic)


def test_novo_ativo_dispara_sync_so_dele(client, monkeypatch):
    chamadas = []
    monkeypatch.setattr("app.services.assets.start_background_sync", lambda only, tickers: chamadas.append((only, tickers)))
    r = client.post("/api/ativos", json={"ticker": "grnd3", "name": "Grendene", "sector": "perene"})
    assert r.status_code == 201, r.text
    assert chamadas == [({"cvm", "mercado", "avaliacoes"}, {"GRND3"})]
    assert client.post("/api/ativos", json={"ticker": "GRND3", "name": "Grendene", "sector": "perene"}).status_code == 409


def test_refazer_perfil_pode_manter_a_divisao(client):
    personalizada = [
        {"asset_class": "renda_fixa", "weight_pct": 40},
        {"asset_class": "acoes", "weight_pct": 40},
        {"asset_class": "fiis", "weight_pct": 20},
        {"asset_class": "etfs", "weight_pct": 0},
    ]
    assert client.put("/api/alocacao", json=personalizada).status_code == 200
    perfil = client.get("/api/perfil").json()
    assert perfil["answers"]
    corpo = {
        "answers": perfil["answers"],
        "income_stability": perfil["income_stability"],
        "monthly_expenses": perfil["monthly_expenses"],
        "monthly_contribution": perfil["monthly_contribution"],
        "passive_income_goal": perfil["passive_income_goal"],
    }
    assert client.put("/api/perfil", json={**corpo, "keep_allocation": True}).status_code == 200
    assert {i["asset_class"]: i["weight_pct"] for i in client.get("/api/alocacao").json()}["fiis"] == 20
    assert client.put("/api/perfil", json=corpo).status_code == 200
    assert {i["asset_class"]: i["weight_pct"] for i in client.get("/api/alocacao").json()}["fiis"] == 30


def test_regras_inconsistentes_sao_recusadas(client):
    r = client.put("/api/regras", json={"nota_evitar": 80, "nota_comprar": 70})
    assert r.status_code == 422
    assert "nota_evitar" in r.json()["detail"]
    assert client.put("/api/regras", json={"yield_alvo": 0}).status_code == 422
    assert client.put("/api/regras", json={"roe_min": -0.1}).status_code == 422
    regras = {i["key"]: i["value"] for i in client.get("/api/regras").json()}
    assert regras["nota_evitar"] == 50


def test_sync_status_e_etapa_invalida(client):
    st = client.get("/api/sync/status").json()
    assert st["running"] is False
    assert isinstance(st["runs"], list)
    r = client.post("/api/sync", params={"etapas": "macro,banana"})
    assert r.status_code == 422
    assert "banana" in r.json()["detail"]


def test_lista_os_fiis_do_universo(client):
    fiis = client.get("/api/ativos", params={"classe": "fii"}).json()
    tickers = {f["ticker"] for f in fiis}
    assert {"KNCR11", "HGLG11"} <= tickers
    assert {f["asset_class"] for f in fiis} == {"fii"}


def test_ficha_de_fii_sem_dados_mostra_fontes_da_cvm(client):
    ficha = client.get("/api/ativos/HGLG11").json()
    assert ficha["asset_class"] == "fii"
    assert ficha["verdict"] == "neutro"
    assert {"Informe mensal", "Informe trimestral"} <= set(ficha["data_sources"])
    assert "Balanços" not in ficha["data_sources"]
    assert any("vacância" in r for r in ficha["risks"])
    assert client.get("/api/ativos/HGLG11/historico").json()["nav"] == []


def test_novo_fii_dispara_etapa_de_fiis(client, monkeypatch):
    chamadas = []
    monkeypatch.setattr("app.services.assets.start_background_sync", lambda only, tickers: chamadas.append((only, tickers)))
    r = client.post("/api/ativos", json={"ticker": "rbrp11", "name": "RBR Properties", "asset_class": "fii"})
    assert r.status_code == 201, r.text
    assert r.json()["sector"] == "hibrido"
    assert chamadas == [({"fiis", "mercado", "avaliacoes"}, {"RBRP11"})]


def test_acao_nova_exige_setor(client):
    r = client.post("/api/ativos", json={"ticker": "wege3", "name": "WEG"})
    assert r.status_code == 422
    assert "setor" in r.text


def test_etf_favorito_e_taxa(client):
    assert client.get("/api/ativos/BOVA11").json()["favorite"] is False
    r = client.patch("/api/ativos/bova11", json={"favorite": True, "admin_fee": 0.001, "distributes": False})
    assert r.status_code == 200, r.text
    ficha = r.json()
    assert ficha["favorite"] is True
    assert ficha["extras"]["taxa_adm_ano"] == 0.001
    assert ficha["data_sources"]["Taxa de administração"] == "informada por você"
    assert ficha["extras"]["distribui"] is False
    assert {r["id"]: r["value_display"] for r in ficha["rules"]}["etf-distribui"] == "reinveste"
    assert any("índice" in risco for risco in ficha["risks"])
    assert {e["ticker"] for e in client.get("/api/ativos", params={"classe": "etf"}).json() if e["favorite"]} == {"BOVA11"}
    apagada = client.patch("/api/ativos/BOVA11", json={"admin_fee": None}).json()
    assert (apagada["favorite"], apagada["extras"]["taxa_adm_ano"]) == (True, None)


def test_favorito_so_vale_para_etf(client):
    r = client.patch("/api/ativos/TAEE11", json={"favorite": True})
    assert r.status_code == 422
    assert "ETFs" in r.json()["detail"]


def test_taxa_absurda_e_recusada(client):
    assert client.patch("/api/ativos/BOVA11", json={"admin_fee": 5}).status_code == 422


def test_novo_etf_dispara_etapa_de_etfs(client, monkeypatch):
    chamadas = []
    monkeypatch.setattr("app.services.assets.start_background_sync", lambda only, tickers: chamadas.append((only, tickers)))
    r = client.post("/api/ativos", json={"ticker": "hash11", "name": "Hashdex Nasdaq Crypto", "asset_class": "etf"})
    assert r.status_code == 201, r.text
    assert r.json()["sector"] == "etf"
    assert chamadas == [({"etfs", "mercado", "avaliacoes"}, {"HASH11"})]


class SempreEvitar(MetodoPorAtivo):
    """Metodologia falsa, só para provar que o app lida com mais de uma sem conhecer nenhuma."""

    info = MethodInfo(key="teste", label="Método de teste", author="testes", summary="Reprova tudo.", focus="valor")

    def evaluate_one(self, snapshot, rules):
        return Evaluation(ticker=snapshot.ticker, score=10, verdict="evitar", summary="Reprovada.", rules=[], engine_version="t")


@pytest.fixture
def dois_metodos(client, monkeypatch):
    monkeypatch.setitem(SELECTION_METHODS, "teste", SempreEvitar())
    with SessionLocal() as db:
        evaluate_all(db)
    yield
    client.put("/api/perfil/metodos", json={"selection_method": "barsi", "allocation_method": "perfil"})


def test_lista_metodologias(client):
    metodos = client.get("/api/metodos").json()
    assert metodos["selection"][0]["key"] == "barsi"
    assert [m["key"] for m in metodos["allocation"]] == ["perfil"]
    assert metodos["selection"][0]["author"] == "Luiz Barsi Filho"


def test_metodologia_desconhecida_e_recusada(client):
    r = client.put("/api/perfil/metodos", json={"selection_method": "nada", "allocation_method": "perfil"})
    assert r.status_code == 422
    assert "desconhecida" in r.json()["detail"]


def test_escolher_metodologia_muda_o_veredito_mostrado(client, dois_metodos):
    antes = client.get("/api/ativos/TAEE11").json()
    assert antes["method"] == "barsi"
    assert [m["key"] for m in antes["other_methods"]] == ["bazin", "teste"]
    perfil = client.put("/api/perfil/metodos", json={"selection_method": "teste", "allocation_method": "perfil"}).json()
    assert perfil["selection_method"] == "teste"
    depois = client.get("/api/ativos/TAEE11").json()
    assert (depois["method"], depois["method_label"], depois["verdict"], depois["score"]) == (
        "teste",
        "Método de teste",
        "evitar",
        10,
    )
    assert [m["key"] for m in depois["other_methods"]] == ["barsi", "bazin"]
    linha = next(a for a in client.get("/api/ativos", params={"classe": "acao"}).json() if a["ticker"] == "TAEE11")
    assert linha["verdict"] == "evitar"
    fii = client.get("/api/ativos/HGLG11").json()
    assert (fii["method"], fii["other_methods"]) == ("fii", [])

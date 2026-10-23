"""CLI de sincronização, indexadores de renda fixa e cotação da brapi."""

from datetime import datetime

import httpx
import pytest
import respx
from typer.testing import CliRunner

from app.core.config import get_settings
from app.db.models import SyncRun
from app.engine.renda_fixa import annual_gross_rate, ir_rate
from app.jobs import sync as cli_sync
from app.providers import market

runner = CliRunner()


def test_cli_recusa_etapa_desconhecida():
    r = runner.invoke(cli_sync.cli, ["--etapas", "macro,banana"])
    assert r.exit_code != 0
    assert "banana" in r.output


def test_cli_mostra_so_as_etapas_desta_execucao(monkeypatch):
    async def fake_run(db, only):  # type: ignore[no-untyped-def]
        assert only == {"macro"}
        db.add(SyncRun(source="macro", started_at=datetime.now(), status="ok", rows=3))
        db.commit()
        return True

    monkeypatch.setattr(cli_sync, "run_full_sync", fake_run)
    r = runner.invoke(cli_sync.cli, ["--etapas", "macro"])
    assert r.exit_code == 0, r.output
    assert r.output.count("linhas") == 1
    assert "macro" in r.output


def test_cli_avisa_sync_em_andamento(monkeypatch):
    async def ocupado(db, only):  # type: ignore[no-untyped-def]
        return False

    monkeypatch.setattr(cli_sync, "run_full_sync", ocupado)
    r = runner.invoke(cli_sync.cli, [])
    assert r.exit_code == 1
    assert "em andamento" in r.output


@pytest.mark.parametrize(
    ("indexer", "rate", "expected"),
    [
        ("cdi", 110, 0.11),
        ("selic", 0.001, 0.101),
        ("ipca", 0.06, 1.05 * 1.06 - 1),
        ("pre", 0.12, 0.12),
    ],
)
def test_taxa_bruta_por_indexador(indexer, rate, expected):
    """CDI de 10%, IPCA de 5% e Selic de 10%: 110% do CDI rende 11% ao ano."""
    assert annual_gross_rate(indexer, rate, cdi=0.10, ipca=0.05, selic=0.10) == pytest.approx(expected)


def test_indexador_desconhecido():
    with pytest.raises(ValueError, match="indexador"):
        annual_gross_rate("dolar", 1, 0.1, 0.05, 0.1)


@pytest.mark.parametrize(("days", "rate"), [(180, 0.225), (181, 0.20), (360, 0.20), (720, 0.175), (721, 0.15)])
def test_ir_regressivo_nos_limites(days, rate):
    assert ir_rate(days) == rate


@pytest.fixture
def brapi_token(monkeypatch):
    monkeypatch.setattr(get_settings(), "brapi_token", "t0k3n")


async def test_brapi_sem_token_nao_chama(monkeypatch):
    monkeypatch.setattr(get_settings(), "brapi_token", "")
    with respx.mock(assert_all_called=False) as m:
        route = m.get(url__regex=r"https://brapi\.dev/.*")
        assert await market.brapi_quote("TAEE11") is None
        assert not route.called


@respx.mock
async def test_brapi_cotacao(brapi_token):
    route = respx.get("https://brapi.dev/api/quote/TAEE11").mock(
        return_value=httpx.Response(
            200, json={"results": [{"regularMarketPrice": 34.5, "marketCap": 3.45e10, "longName": "Taesa"}]}
        )
    )
    q = await market.brapi_quote("TAEE11")
    assert q is not None
    assert q.price == 34.5
    assert q.name == "Taesa"
    assert route.calls.last.request.url.params["token"] == "t0k3n"


@respx.mock
async def test_brapi_erro_vira_none(brapi_token):
    respx.get("https://brapi.dev/api/quote/TAEE11").mock(return_value=httpx.Response(401))
    assert await market.brapi_quote("TAEE11") is None

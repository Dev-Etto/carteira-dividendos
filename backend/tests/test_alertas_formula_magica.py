from datetime import date, timedelta
from decimal import Decimal

from app.db.models import Evaluation, Profile
from app.services.portfolio import PortfolioState, PositionView, portfolio_alerts

HOJE = date(2026, 11, 19)


def posicao(asset_id: int, ticker: str, first_buy: date) -> PositionView:
    return PositionView(
        asset_id=asset_id,
        ticker=ticker,
        name=ticker,
        asset_class="acoes",
        allocation_class="acoes",
        sector="ciclico",
        quantity=10,
        avg_price=10.0,
        total_cost=100.0,
        price=10.0,
        value=100.0,
        profit=0.0,
        profit_pct=0.0,
        weight_pct=50.0,
        income_12m=0.0,
        yield_on_cost=None,
        first_buy=first_buy,
    )


def avaliacao(verdict: str, posicao: int | None) -> Evaluation:
    return Evaluation(method="formula-magica", verdict=verdict, score=50, extras={"posicao": posicao, "total": 30}, rules=[])


def estado() -> PortfolioState:
    return PortfolioState(
        positions=[posicao(1, "MULT3", HOJE - timedelta(days=30)), posicao(2, "LREN3", HOJE - timedelta(days=400))],
        holdings=[],
        class_values={"acoes": 200.0},
        reserve=0.0,
    )


def alertas(metodo: str) -> list[str]:
    perfil = Profile(selection_method=metodo, onboarded=False, monthly_expenses=Decimal(0), emergency_months=6)
    avaliacoes = {1: avaliacao("neutro", 15), 2: avaliacao("comprar", 3)}
    return portfolio_alerts(estado(), perfil, avaliacoes, HOJE)


def test_avisa_quem_saiu_do_primeiro_terco_e_quem_completou_um_ano():
    avisos = [a for a in alertas("formula-magica") if "Fórmula Mágica" in a]
    assert avisos == [
        "MULT3 está em 15º de 30 na Fórmula Mágica, fora do primeiro terço. O livro troca a ação na revisão anual.",
        "LREN3 completou 1 ano na carteira: pela Fórmula Mágica, é hora de revisar se ela continua entre as primeiras.",
    ]


def test_outras_metodologias_nao_recebem_esses_avisos():
    assert not [a for a in alertas("barsi") if "Fórmula Mágica" in a]

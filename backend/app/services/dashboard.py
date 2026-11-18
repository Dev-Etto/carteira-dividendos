"""Painel inicial: resumo da carteira, próximo passo recomendado e oportunidades do dia."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Profile, SyncRun
from app.engine import fmt
from app.schemas.api import DashboardOut, NextStep
from app.services.assets import buy_opportunities
from app.services.evaluation import latest_evaluations
from app.services.filings import portfolio_filings
from app.services.macro import latest_macro
from app.services.portfolio import PortfolioState, class_slices, load_portfolio, portfolio_alerts
from app.services.profile import get_profile, profile_out, reserve_target, targets

TOP_OPPORTUNITIES = 5


def _has_evaluated_market(db: Session) -> bool:
    query = select(func.count(SyncRun.id)).where(SyncRun.source == "avaliacoes", SyncRun.status == "ok")
    return bool(db.scalar(query))


def next_step(db: Session, profile: Profile, state: PortfolioState) -> NextStep:
    """O passo seguinte segue a ordem do método: perfil → dados → reserva → primeiro aporte → aportes mensais."""
    if not profile.onboarded:
        return NextStep(
            title="Defina seu perfil",
            description="Responda 5 perguntas para o app sugerir a divisão da sua carteira.",
            href="/onboarding",
        )
    if not _has_evaluated_market(db):
        return NextStep(
            title="Baixe os dados do mercado", description="Rode a primeira atualização para avaliar as ações.", href="/config"
        )
    missing = reserve_target(profile) - state.reserve
    if missing > 0:
        return NextStep(
            title="Monte sua reserva de emergência",
            description=f"Faltam {fmt.brl(missing)}. Ela vem antes de qualquer ação ou FII.",
            href="/renda-fixa",
        )
    if not state.positions:
        return NextStep(
            title="Faça seu primeiro aporte", description="O assistente mostra onde colocar o dinheiro e por quê.", href="/aporte"
        )
    return NextStep(title="Aporte do mês", description="Informe o valor e veja o plano de compras.", href="/aporte")


def build_dashboard(db: Session) -> DashboardOut:
    profile = get_profile(db)
    state = load_portfolio(db)
    evaluations = latest_evaluations(db, [p.asset_id for p in state.positions])
    return DashboardOut(
        profile=profile_out(profile),
        total_invested=state.total_invested,
        cash_to_invest=state.cash_to_invest,
        reserve_value=state.reserve,
        reserve_target=reserve_target(profile),
        income_12m=state.income_12m,
        passive_income_goal=float(profile.passive_income_goal),
        classes=class_slices(state, targets(db)),
        next_step=next_step(db, profile, state),
        alerts=portfolio_alerts(state, profile, evaluations),
        top_opportunities=buy_opportunities(db, TOP_OPPORTUNITIES),
        macro=latest_macro(db),
        last_sync=db.scalar(select(func.max(SyncRun.finished_at)).where(SyncRun.status == "ok")),
        filings=portfolio_filings(db, [p.asset_id for p in state.positions]),
    )

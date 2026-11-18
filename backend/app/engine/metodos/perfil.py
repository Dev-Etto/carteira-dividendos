"""Divisão pelo perfil de risco do questionário (conservador, moderado ou arrojado)."""

from app.engine.metodos.base import MethodInfo, MetodoDivisao
from app.engine.perfil import ALLOCATIONS


class PerfilDeRisco(MetodoDivisao):
    info = MethodInfo(
        key="perfil",
        label="Perfil de risco",
        author="questionário do app",
        summary="Renda fixa, ações, FIIs e ETFs na proporção sugerida para o seu perfil de risco.",
        focus="divisao",
    )

    def targets(self, risk_profile: str) -> dict[str, float]:
        return dict(ALLOCATIONS.get(risk_profile, ALLOCATIONS["moderado"]))

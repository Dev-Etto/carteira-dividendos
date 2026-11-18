"""Divisão pelo perfil de risco do questionário (conservador, moderado ou arrojado)."""

from app.engine.metodos.base import MethodInfo, MetodoDivisao
from app.engine.perfil import ALLOCATIONS

CLASS_OF = {"acao": "acoes", "fii": "fiis", "etf": "etfs"}


class PerfilDeRisco(MetodoDivisao):
    info = MethodInfo(
        key="perfil",
        label="Perfil de risco",
        author="questionário do app",
        summary="Renda fixa, ações, FIIs e ETFs na proporção sugerida para o seu perfil de risco.",
        focus="divisao",
    )
    classes = ("renda_fixa", "acoes", "fiis", "etfs")

    def targets(self, risk_profile: str) -> dict[str, float]:
        return dict(ALLOCATIONS.get(risk_profile, ALLOCATIONS["moderado"]))

    def class_of(self, asset_class: str, region: str) -> str:
        return CLASS_OF.get(asset_class, asset_class)

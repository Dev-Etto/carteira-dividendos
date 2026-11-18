"""Método Barsi: setores perenes (BEST), longo histórico de proventos e compra abaixo do preço-teto.
As regras ficam em `app/engine/acoes.py`; aqui só a adaptação ao contrato de seleção."""

from app.engine.acoes import evaluate_stock
from app.engine.metodos.base import MethodInfo, MetodoPorAtivo, Rules
from app.engine.types import Evaluation, StockSnapshot


class Barsi(MetodoPorAtivo):
    info = MethodInfo(
        key="barsi",
        label="Barsi",
        author="Luiz Barsi Filho",
        summary="Empresas de setores perenes (BEST) que pagam proventos há muitos anos, compradas abaixo do preço-teto.",
        focus="renda",
    )

    def evaluate_one(self, snapshot: StockSnapshot, rules: Rules) -> Evaluation:
        return evaluate_stock(snapshot, dict(rules))

"""Contratos das metodologias (padrão Strategy).

Uma metodologia de SELEÇÃO avalia ações: recebe o lote inteiro de snapshots, para que métodos de
ranking (que comparam as ações entre si) caibam no mesmo contrato dos métodos de regras (que avaliam
cada ação sozinha). Uma metodologia de DIVISÃO diz em quais classes a carteira se divide e o alvo de
cada uma. Para criar uma metodologia nova, implemente o contrato e registre a instância em
`registro.py`; nada mais no app precisa mudar.
"""

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from app.engine.types import Evaluation, StockSnapshot

Rules = Mapping[str, float]


@dataclass(frozen=True)
class MethodInfo:
    """O que a tela mostra sobre a metodologia. focus: renda | valor | valorizacao | divisao."""

    key: str
    label: str
    author: str
    summary: str
    focus: str


class MetodoSelecao(ABC):
    info: MethodInfo

    @abstractmethod
    def evaluate(self, snapshots: Sequence[StockSnapshot], rules: Rules) -> dict[str, Evaluation]:
        """Avaliação de cada ação do lote, indexada pelo ticker."""


class MetodoPorAtivo(MetodoSelecao):
    """Base dos métodos que avaliam cada ação sozinha (regras com nota): só `evaluate_one` muda."""

    @abstractmethod
    def evaluate_one(self, snapshot: StockSnapshot, rules: Rules) -> Evaluation: ...

    def evaluate(self, snapshots: Sequence[StockSnapshot], rules: Rules) -> dict[str, Evaluation]:
        return {s.ticker: self.evaluate_one(s, rules) for s in snapshots}


class MetodoDivisao(ABC):
    info: MethodInfo

    @abstractmethod
    def targets(self, risk_profile: str) -> dict[str, float]:
        """Peso-alvo de cada classe, em %, somando 100."""

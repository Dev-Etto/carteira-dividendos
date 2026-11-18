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
    """Divisão da carteira. Além dos alvos, a metodologia diz quais classes existem, em qual delas
    cada ativo entra e a faixa permitida para cada uma, para que perfil, carteira e aporte não precisem
    conhecer nenhuma metodologia."""

    info: MethodInfo
    classes: tuple[str, ...]
    min_weight: float = 0.0
    max_weight: float = 100.0

    @abstractmethod
    def targets(self, risk_profile: str) -> dict[str, float]:
        """Peso-alvo de cada classe, em %, somando 100."""

    @abstractmethod
    def class_of(self, asset_class: str, region: str) -> str:
        """Classe da divisão em que entra um ativo (acao, fii ou etf) da região (nacional ou internacional)."""

    def errors(self, weights: Mapping[str, float]) -> list[str]:
        """O que impede salvar a divisão: classes erradas, soma diferente de 100 ou peso fora da faixa."""
        out_of_range = any(not self.min_weight <= w <= self.max_weight for w in weights.values())
        checks = [
            (set(weights) != set(self.classes), f"Classes esperadas: {', '.join(self.classes)}"),
            (abs(sum(weights.values()) - 100) > 0.01, "Os pesos precisam somar 100%"),
            (
                out_of_range,
                f"Cada classe precisa ficar entre {self.min_weight:g}% e {self.max_weight:g}% no {self.info.label}",
            ),
        ]
        return [message for broken, message in checks if broken]

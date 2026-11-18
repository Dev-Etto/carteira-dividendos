"""Registro das metodologias disponíveis (padrão Registry). A ordem aqui é a ordem das telas."""

from app.engine.metodos.arca import Arca
from app.engine.metodos.barsi import Barsi
from app.engine.metodos.base import MetodoDivisao, MetodoSelecao
from app.engine.metodos.bazin import Bazin
from app.engine.metodos.formula_magica import FormulaMagica
from app.engine.metodos.graham import Graham
from app.engine.metodos.perfil import PerfilDeRisco

SELECTION_METHODS: dict[str, MetodoSelecao] = {m.info.key: m for m in (Barsi(), Bazin(), Graham(), FormulaMagica())}
ALLOCATION_METHODS: dict[str, MetodoDivisao] = {m.info.key: m for m in (PerfilDeRisco(), Arca())}

DEFAULT_SELECTION = "barsi"
DEFAULT_ALLOCATION = "perfil"


def selection_method(key: str) -> MetodoSelecao:
    """Metodologia de seleção pela chave; uma chave desconhecida (método removido) cai no padrão."""
    return SELECTION_METHODS.get(key, SELECTION_METHODS[DEFAULT_SELECTION])


def allocation_method(key: str) -> MetodoDivisao:
    return ALLOCATION_METHODS.get(key, ALLOCATION_METHODS[DEFAULT_ALLOCATION])

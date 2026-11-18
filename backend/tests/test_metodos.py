from datetime import date

from app.engine.acoes import evaluate_stock
from app.engine.metodos.barsi import Barsi
from app.engine.metodos.perfil import PerfilDeRisco
from app.engine.metodos.registro import DEFAULT_ALLOCATION, DEFAULT_SELECTION, allocation_method, selection_method
from app.engine.perfil import ALLOCATIONS
from app.engine.types import StockSnapshot


def snapshot(ticker: str) -> StockSnapshot:
    return StockSnapshot(
        ticker=ticker, name=ticker, sector="energia", price=30.0, dividends_by_year={2024: 2.0}, current_year=date.today().year
    )


def test_barsi_avalia_o_lote_igual_ao_motor():
    lote = [snapshot("TAEE11"), snapshot("CMIG4")]
    resultado = Barsi().evaluate(lote, {})
    assert set(resultado) == {"TAEE11", "CMIG4"}
    assert resultado["TAEE11"].model_dump() == evaluate_stock(lote[0], {}).model_dump()


def test_divisao_pelo_perfil_de_risco():
    assert PerfilDeRisco().targets("arrojado") == ALLOCATIONS["arrojado"]
    assert PerfilDeRisco().targets("desconhecido") == ALLOCATIONS["moderado"]
    assert sum(PerfilDeRisco().targets("moderado").values()) == 100


def test_chave_desconhecida_cai_no_padrao():
    assert selection_method("removido").info.key == DEFAULT_SELECTION
    assert allocation_method("removido").info.key == DEFAULT_ALLOCATION

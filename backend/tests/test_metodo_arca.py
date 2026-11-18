from app.engine.aporte import Candidate, build_plan
from app.engine.metodos.arca import Arca
from app.engine.metodos.perfil import PerfilDeRisco


def test_quatro_classes_de_25_por_cento():
    assert Arca().targets("arrojado") == {"acoes": 25.0, "fiis": 25.0, "renda_fixa": 25.0, "internacional": 25.0}


def test_etf_nacional_conta_em_acoes_e_internacional_na_quarta_classe():
    arca = Arca()
    assert arca.class_of("etf", "nacional") == "acoes"
    assert arca.class_of("etf", "internacional") == "internacional"
    assert (arca.class_of("acao", "nacional"), arca.class_of("fii", "nacional")) == ("acoes", "fiis")
    assert PerfilDeRisco().class_of("etf", "internacional") == "etfs"


def test_faixa_de_10_a_40_por_cento():
    arca = Arca()
    assert arca.errors(arca.targets("moderado")) == []
    assert arca.errors({"acoes": 45.0, "fiis": 25.0, "renda_fixa": 20.0, "internacional": 10.0}) == [
        "Cada classe precisa ficar entre 10% e 40% no ARCA"
    ]
    assert "Os pesos precisam somar 100%" in arca.errors({"acoes": 30.0, "fiis": 30.0, "renda_fixa": 30.0, "internacional": 30.0})
    assert arca.errors({"acoes": 50.0, "fiis": 50.0})[0].startswith("Classes esperadas")
    assert PerfilDeRisco().errors({"renda_fixa": 0.0, "acoes": 100.0, "fiis": 0.0, "etfs": 0.0}) == []


def test_aporte_da_classe_internacional_vai_para_os_etfs_internacionais():
    plan = build_plan(
        amount=1000,
        reserve_current=0,
        reserve_target=0,
        class_current=dict.fromkeys(Arca().classes, 0.0),
        targets=Arca().targets("moderado"),
        stock_candidates=[],
        international_candidates=[Candidate("IVVB11", "iShares S&P 500", 100.0, 100, 0.0, "etf")],
    )
    linhas = [ln for ln in plan.lines if ln.asset_class == "internacional"]
    assert [(ln.ticker, ln.quantity) for ln in linhas] == [("IVVB11", 2)]


def test_sem_etf_internacional_favorito_deixa_nota():
    plan = build_plan(
        amount=1000,
        reserve_current=0,
        reserve_target=0,
        class_current=dict.fromkeys(Arca().classes, 0.0),
        targets=Arca().targets("moderado"),
        stock_candidates=[],
    )
    assert any("Nenhum ETF internacional favorito apto" in n for n in plan.notes)

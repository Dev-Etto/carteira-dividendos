"""Verificador das regras de estilo da casa (tools/style_rules)."""

import textwrap

import pytest

from tools.style_rules import check_source, main


def codes(source: str) -> list[str]:
    return [v.code for v in check_source("x.py", textwrap.dedent(source))]


def test_codigo_limpo_passa():
    source = '''
        """Docstring de módulo é permitida."""

        def f(x: int) -> str:
            """Docstring de função também."""
            if x < 0:
                return "negativo"
            return "par" if x % 2 == 0 else "ímpar"
        '''
    assert codes(source) == []


@pytest.mark.parametrize(
    "source",
    [
        "x = 1  # explica x\n",
        "# título de seção\nx = 1\n",
        "x = 1  # noqa\n",
        "x = 1  # noqa: E501 — porque sim\n",
    ],
)
def test_comentario_proibido(source):
    assert codes(source) == ["STY001"]


@pytest.mark.parametrize(
    "source",
    ["x = f()  # noqa: BLE001\n", "x = f()  # type: ignore[attr-defined]\n", "def f(): ...  # pragma: no cover\n"],
)
def test_diretivas_de_ferramenta_sao_permitidas(source):
    assert codes(source) == []


@pytest.mark.parametrize(
    "source",
    [
        "if a:\n    x = 1\nelse:\n    x = 2\n",
        "if a:\n    x = 1\nelif b:\n    x = 2\n",
        "for i in r:\n    pass\nelse:\n    pass\n",
        "while a:\n    pass\nelse:\n    pass\n",
        "try:\n    pass\nexcept E:\n    pass\nelse:\n    pass\n",
    ],
)
def test_else_e_elif_proibidos(source):
    assert codes(source) == ["STY002"]


def test_if_dentro_de_if():
    source = """
        if a:
            for i in r:
                if b:
                    pass
        """
    assert codes(source) == ["STY003"]


def test_if_em_funcao_interna_nao_conta_como_aninhado():
    source = """
        if a:
            def g():
                if b:
                    return 1
                return 2
        """
    assert codes(source) == []


def test_ternario_aninhado():
    assert codes("x = 1 if a else (2 if b else 3)\n") == ["STY004"]


def test_main_lista_violacoes(tmp_path, capsys):
    bad = tmp_path / "bad.py"
    bad.write_text("if a:\n    pass\nelse:\n    pass\n")
    good = tmp_path / "good.py"
    good.write_text("x = 1\n")
    assert main([str(good)]) == 0
    assert main([str(tmp_path)]) == 1
    assert "bad.py:1:1: STY002" in capsys.readouterr().out

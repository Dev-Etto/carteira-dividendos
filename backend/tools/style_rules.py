"""Regras de estilo da casa que o ruff não cobre.

STY001  comentário de linha (docstrings são permitidas; diretivas de ferramenta também)
STY002  else / elif (inclusive else de for, while e try)
STY003  if dentro de if
STY004  ternário aninhado

Uso: python -m tools.style_rules app tests
"""

import ast
import io
import re
import sys
import tokenize
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

DIRECTIVE = re.compile(r"#\s*(noqa: [A-Z]+[0-9]+(, [A-Z]+[0-9]+)*|type: ignore\[[a-z-]+(, [a-z-]+)*\]|pragma: no cover)$")
SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)


@dataclass(frozen=True)
class Violation:
    path: str
    line: int
    col: int
    code: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}:{self.col + 1}: {self.code} {self.message}"


def comment_violations(path: str, source: str) -> Iterator[Violation]:
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        if tok.type == tokenize.COMMENT and not DIRECTIVE.search(tok.string):
            yield Violation(path, tok.start[0], tok.start[1], "STY001", "comentário proibido: deixe o código se explicar")


def _orelse_owner(node: ast.AST) -> str | None:
    if isinstance(node, ast.If) and node.orelse:
        return "elif" if len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If) else "else"
    if isinstance(node, (ast.For, ast.AsyncFor, ast.While, ast.Try, ast.TryStar)) and node.orelse:
        return "else"
    return None


class _Visitor(ast.NodeVisitor):
    def __init__(self, path: str) -> None:
        self.path = path
        self.found: list[Violation] = []
        self.if_depth = 0
        self.ternary_depth = 0

    def _report(self, node: ast.expr | ast.stmt, code: str, message: str) -> None:
        self.found.append(Violation(self.path, node.lineno, node.col_offset, code, message))

    def _check_orelse(self, node: ast.AST) -> None:
        keyword = _orelse_owner(node)
        if keyword and isinstance(node, ast.stmt):
            self._report(node, "STY002", f"{keyword} proibido: use guard clause, retorno antecipado ou um mapa")

    def generic_visit(self, node: ast.AST) -> None:
        self._check_orelse(node)
        if not isinstance(node, SCOPES):
            super().generic_visit(node)
            return
        saved = (self.if_depth, self.ternary_depth)
        self.if_depth, self.ternary_depth = 0, 0
        super().generic_visit(node)
        self.if_depth, self.ternary_depth = saved

    def visit_If(self, node: ast.If) -> None:
        self._check_orelse(node)
        if self.if_depth:
            self._report(node, "STY003", "if dentro de if: extraia uma função ou combine as condições")
        self.visit(node.test)
        self.if_depth += 1
        for child in node.body:
            self.visit(child)
        self.if_depth -= 1
        for child in node.orelse:
            self.visit(child)

    def visit_IfExp(self, node: ast.IfExp) -> None:
        if self.ternary_depth:
            self._report(node, "STY004", "ternário aninhado: use uma função ou um mapa")
        self.ternary_depth += 1
        super().generic_visit(node)
        self.ternary_depth -= 1


def ast_violations(path: str, source: str) -> list[Violation]:
    visitor = _Visitor(path)
    visitor.visit(ast.parse(source, filename=path))
    return visitor.found


def check_source(path: str, source: str) -> list[Violation]:
    found = [*comment_violations(path, source), *ast_violations(path, source)]
    return sorted(found, key=lambda v: (v.line, v.col, v.code))


def python_files(targets: list[str]) -> Iterator[Path]:
    missing = [t for t in targets if not Path(t).exists()]
    if missing:
        raise SystemExit(f"caminho não encontrado: {', '.join(missing)}")
    for target in map(Path, targets):
        yield from sorted(target.rglob("*.py")) if target.is_dir() else [target]


def main(argv: list[str]) -> int:
    found = [v for f in python_files(argv or ["app", "tests", "tools"]) for v in check_source(str(f), f.read_text("utf-8"))]
    sys.stdout.writelines(f"{v}\n" for v in found)
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

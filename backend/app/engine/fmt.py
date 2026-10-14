"""Formatação pt-BR para as explicações do motor."""


def _br(n: float, decimals: int) -> str:
    s = f"{n:,.{decimals}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def pct(v: float | None, decimals: int = 1) -> str:
    return "—" if v is None else f"{_br(v * 100, decimals)}%"


def num(v: float | None, decimals: int = 2) -> str:
    return "—" if v is None else _br(v, decimals)


def brl(v: float | None, decimals: int = 2) -> str:
    if v is None:
        return "—"
    if abs(v) >= 1_000_000_000:
        return f"R$ {_br(v / 1_000_000_000, 1)} bi"
    if abs(v) >= 1_000_000:
        return f"R$ {_br(v / 1_000_000, 1)} mi"
    return f"R$ {_br(v, decimals)}"


def years(n: int) -> str:
    return f"{n} ano" if n == 1 else f"{n} anos"

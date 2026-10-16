"""Posições, preço médio e resultado — regras de negócio da carteira (puro)."""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal


@dataclass
class Tx:
    """Operação de compra ou venda. kind: "compra" | "venda"."""

    date: date
    kind: str
    quantity: Decimal
    price: Decimal
    fees: Decimal = Decimal(0)


@dataclass
class SplitEvent:
    """Desdobramento ou grupamento. ratio 2 = desdobramento 1:2; ratio 0.1 = grupamento 10:1."""

    date: date
    ratio: Decimal


@dataclass
class PositionCalc:
    quantity: Decimal
    total_cost: Decimal
    avg_price: Decimal
    realized_profit: Decimal


def compute_position(txs: list[Tx], splits: list[SplitEvent] | None = None) -> PositionCalc:
    """Preço médio = custo total das compras (com taxas) ÷ quantidade.
    Vendas reduzem quantidade e custo proporcionalmente; o preço médio não muda.
    Desdobramento/grupamento multiplica a quantidade e preserva o custo total.
    Um desdobramento vale antes das operações do mesmo dia."""
    events: list[tuple[date, int, Tx | SplitEvent]] = [(t.date, 1, t) for t in txs]
    events += [(s.date, 0, s) for s in (splits or [])]
    events.sort(key=lambda e: (e[0], e[1]))

    qty = Decimal(0)
    cost = Decimal(0)
    realized = Decimal(0)
    for _, _, ev in events:
        if isinstance(ev, SplitEvent):
            qty = qty * ev.ratio if qty > 0 else qty
            continue
        if ev.kind == "compra":
            qty += ev.quantity
            cost += ev.quantity * ev.price + ev.fees
            continue
        if ev.quantity > qty:
            raise ValueError(f"Venda de {ev.quantity} maior que a posição de {qty} em {ev.date}")
        avg = cost / qty if qty else Decimal(0)
        realized += ev.quantity * ev.price - ev.fees - ev.quantity * avg
        cost -= ev.quantity * avg
        qty -= ev.quantity
    avg = (cost / qty).quantize(Decimal("0.0001"), ROUND_HALF_UP) if qty else Decimal(0)
    return PositionCalc(quantity=qty, total_cost=cost, avg_price=avg, realized_profit=realized)


def quantity_on(txs: list[Tx], splits: list[SplitEvent], day: date) -> Decimal:
    """Quantidade em carteira ao fim de um dia (usada para saber o direito na data-com)."""
    return compute_position([t for t in txs if t.date <= day], [s for s in splits if s.date <= day]).quantity


def entitled_income(txs: list[Tx], splits: list[SplitEvent], dividends: list[tuple[date, float]]) -> Decimal:
    """Proventos a que a posição teve direito.

    `dividends` traz (data ex, valor por ação). A data ex é o primeiro dia sem direito, então conta a
    quantidade no fim do dia anterior (data-com). O valor por ação vem ajustado pelos desdobramentos
    posteriores, por isso a quantidade daquela data é convertida para a base de ações de hoje."""
    total = Decimal(0)
    for ex_date, amount in dividends:
        qty = quantity_on(txs, splits, ex_date - timedelta(days=1))
        if qty <= 0:
            continue
        for s in splits:
            if s.date >= ex_date:
                qty *= s.ratio
        total += qty * Decimal(str(amount))
    return total

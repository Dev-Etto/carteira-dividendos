"""Fórmula Mágica (Joel Greenblatt, *The Little Book That Beats the Market*, 2005): ordenar as ações
por earnings yield e por retorno sobre o capital, somar as duas posições e comprar as primeiras.

    earnings yield = EBIT ÷ valor da firma (valor de mercado + dívida líquida)
    retorno sobre o capital = EBIT ÷ (capital de giro líquido + imobilizado líquido)
    capital de giro líquido = (ativo circulante − caixa) − (passivo circulante − empréstimos de curto prazo)

Fontes: AAII (aaii.com/journal/article/the-magic-formula-approach-to-stockpicking) e o site oficial
(magicformulainvesting.com/Home/HowItWorks). Como no livro, ficam de fora bancos, seguradoras e as
empresas de energia e saneamento. O "caixa excedente" do livro não tem definição exata; o app usa o
caixa total. O método busca valorização e ignora dividendos, e o livro manda girar a carteira a cada
ano: o app só avisa, nunca sugere vender. Não há "evitar": quem fica fora do primeiro terço é "neutro".
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass

from app.engine import fmt
from app.engine.acoes import current_dy, rule_liquidez
from app.engine.config import merged_rules
from app.engine.metodos.base import MethodInfo, MetodoSelecao, Rules
from app.engine.types import Evaluation, RuleResult, RuleStatus, StockSnapshot, YearFundamentals

ENGINE_VERSION = "formula-magica-1.0"
EXCLUDED_SECTORS = {"bancos", "seguros", "energia", "saneamento"}
AVISO = "A Fórmula Mágica busca valorização e ignora dividendos."


@dataclass(frozen=True)
class Metrics:
    earnings_yield: float
    return_on_capital: float
    year: int


def _latest(s: StockSnapshot) -> YearFundamentals | None:
    years = [y for y in s.fundamentals if y < s.current_year]
    return s.fundamentals[max(years)] if years else None


def metrics(s: StockSnapshot) -> Metrics | None:
    """Earnings yield e retorno sobre o capital do último balanço; None se faltar algum número ou se o
    valor da firma ou o capital não forem positivos."""
    f = _latest(s)
    if f is None or not s.price or not s.shares_outstanding:
        return None
    needed = (f.ebit, f.gross_debt, f.current_assets, f.current_liabilities, f.fixed_assets)
    if any(v is None for v in needed):
        return None
    ebit, debt = f.ebit or 0.0, f.gross_debt or 0.0
    cash, short_debt = f.cash or 0.0, f.short_term_debt or 0.0
    working_capital = ((f.current_assets or 0.0) - cash) - ((f.current_liabilities or 0.0) - short_debt)
    capital = working_capital + (f.fixed_assets or 0.0)
    firm_value = s.price * s.shares_outstanding + debt - cash
    if firm_value <= 0 or capital <= 0:
        return None
    return Metrics(earnings_yield=ebit / firm_value, return_on_capital=ebit / capital, year=f.year)


def positions(values: dict[str, float]) -> dict[str, int]:
    """Posição de cada ticker (1 = maior valor)."""
    ordered = sorted(values, key=lambda t: -values[t])
    return {t: i + 1 for i, t in enumerate(ordered)}


def ranking(scored: dict[str, Metrics]) -> list[str]:
    """Tickers do melhor para o pior pela soma das posições; no empate, o maior retorno sobre o capital."""
    ey = positions({t: m.earnings_yield for t, m in scored.items()})
    roc = positions({t: m.return_on_capital for t, m in scored.items()})
    return sorted(scored, key=lambda t: (ey[t] + roc[t], roc[t]))


def _info_rule(
    rule_id: str, label: str, status: RuleStatus, value: float | None, shown: str, threshold: str, explanation: str
) -> RuleResult:
    return RuleResult(
        id=rule_id,
        label=label,
        status=status,
        value=value,
        value_display=shown,
        threshold=threshold,
        explanation=explanation,
        learn_more="formula-magica",
        weight=0,
        group="preco" if rule_id == "fm-ranking" else "qualidade",
    )


def _band(position: int, total: int) -> RuleStatus:
    """ok no primeiro terço, warn no segundo e fail no último."""
    third = position / total
    if third <= 1 / 3:
        return "ok"
    if third <= 2 / 3:
        return "warn"
    return "fail"


class FormulaMagica(MetodoSelecao):
    info = MethodInfo(
        key="formula-magica",
        label="Fórmula Mágica",
        author="Joel Greenblatt",
        summary="Ranking das ações mais baratas (earnings yield) e mais rentáveis (retorno sobre o capital). Busca valorização e ignora dividendos.",
        focus="valorizacao",
    )

    def evaluate(self, snapshots: Sequence[StockSnapshot], rules: Rules) -> dict[str, Evaluation]:
        c = merged_rules(dict(rules))
        liquidity = {s.ticker: rule_liquidez(s, c) for s in snapshots}
        eligible = [s for s in snapshots if s.sector not in EXCLUDED_SECTORS and liquidity[s.ticker].status != "fail"]
        scored = {s.ticker: m for s in eligible if (m := metrics(s)) is not None}
        order = ranking(scored)
        buy_count = math.ceil(len(order) * c["fm_fracao_comprar"])
        place = {t: i + 1 for i, t in enumerate(order)}
        ey = positions({t: m.earnings_yield for t, m in scored.items()})
        roc = positions({t: m.return_on_capital for t, m in scored.items()})
        context = _Context(place, ey, roc, buy_count, len(order), liquidity)
        return {s.ticker: context.evaluation(s, scored.get(s.ticker)) for s in snapshots}


@dataclass(frozen=True)
class _Context:
    """O ranking já calculado, para montar a avaliação de cada ação."""

    place: dict[str, int]
    ey: dict[str, int]
    roc: dict[str, int]
    buy_count: int
    total: int
    liquidity: dict[str, RuleResult]

    def _neutral(self, s: StockSnapshot, summary: str, rules: list[RuleResult]) -> Evaluation:
        return Evaluation(
            ticker=s.ticker,
            score=0,
            verdict="neutro",
            summary=f"{summary} {AVISO}",
            rules=rules,
            dividend_yield=current_dy(s),
            extras={"posicao": None, "total": self.total},
            engine_version=ENGINE_VERSION,
        )

    def evaluation(self, s: StockSnapshot, m: Metrics | None) -> Evaluation:
        liquidity = self.liquidity[s.ticker]
        if s.sector in EXCLUDED_SECTORS:
            setor = _info_rule(
                "fm-setor",
                "Setor",
                "fail",
                None,
                "fora do método",
                "sem bancos, seguradoras, energia e saneamento",
                "O livro deixa de fora bancos, seguradoras e empresas de energia e saneamento: o balanço delas não se compara ao das outras.",
            )
            return self._neutral(s, "Setor fora da Fórmula Mágica.", [setor, liquidity])
        if liquidity.status == "fail":
            return self._neutral(s, "Pouca liquidez para entrar no ranking.", [liquidity])
        if m is None:
            missing = _info_rule(
                "fm-ranking",
                "Posição no ranking",
                "na",
                None,
                "sem dado",
                "primeiro terço",
                "Precisa de preço, número de ações e do balanço com EBIT, dívida, circulante e imobilizado.",
            )
            return self._neutral(s, "Dados insuficientes para o ranking.", [missing, liquidity])
        return self._ranked(s, m, liquidity)

    def _ranked(self, s: StockSnapshot, m: Metrics, liquidity: RuleResult) -> Evaluation:
        place, total = self.place[s.ticker], self.total
        buy = place <= self.buy_count
        rules = [
            _info_rule(
                "fm-earnings-yield",
                "Earnings yield (EBIT ÷ valor da firma)",
                _band(self.ey[s.ticker], total),
                m.earnings_yield,
                f"{fmt.pct(m.earnings_yield)} · {self.ey[s.ticker]}º de {total}",
                "quanto maior, mais barata",
                f"O lucro operacional de {m.year} equivale a {fmt.pct(m.earnings_yield)} do valor da firma (ações + dívida líquida).",
            ),
            _info_rule(
                "fm-retorno-capital",
                "Retorno sobre o capital",
                _band(self.roc[s.ticker], total),
                m.return_on_capital,
                f"{fmt.pct(m.return_on_capital)} · {self.roc[s.ticker]}º de {total}",
                "quanto maior, mais rentável",
                f"Cada R$ 100 de capital de giro e imobilizado geraram {fmt.brl(100 * m.return_on_capital)} de lucro operacional em {m.year}.",
            ),
            _info_rule(
                "fm-ranking",
                "Posição no ranking",
                "ok" if buy else "fail",
                float(place),
                f"{place}º de {total}",
                f"entre as {self.buy_count} primeiras",
                f"Soma das duas posições: {place}º lugar entre {total} ações. O livro manda comprar as primeiras e trocar a cada ano.",
            ),
            liquidity,
        ]
        score = round(100 * (total - place) / (total - 1)) if total > 1 else 100
        verdict = "comprar" if buy else "neutro"
        summary = f"{place}º de {total} no ranking da Fórmula Mágica."
        return Evaluation(
            ticker=s.ticker,
            score=score,
            verdict=verdict,
            summary=f"{summary} {AVISO}",
            rules=rules,
            dividend_yield=current_dy(s),
            extras={"posicao": place, "total": total, "earnings_yield": m.earnings_yield, "retorno_capital": m.return_on_capital},
            engine_version=ENGINE_VERSION,
        )

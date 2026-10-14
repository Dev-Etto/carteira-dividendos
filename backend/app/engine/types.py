"""Tipos do motor de regras. O motor é puro: recebe um snapshot e devolve uma avaliação."""

from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel

RuleStatus = Literal["ok", "warn", "fail", "na"]
Verdict = Literal["comprar", "aguardar", "neutro", "evitar"]

STATUS_POINTS: dict[str, float] = {"ok": 1.0, "warn": 0.5, "fail": 0.0}


class RuleResult(BaseModel):
    """Resultado de uma regra. group: qualidade | preco | setorial | sustentabilidade."""

    id: str
    label: str
    status: RuleStatus
    value: float | None
    value_display: str
    threshold: str
    explanation: str
    learn_more: str
    weight: int
    eliminatory: bool = False
    group: str = "qualidade"


class Evaluation(BaseModel):
    ticker: str
    score: int
    verdict: Verdict
    summary: str
    ceiling_price: float | None = None
    margin_pct: float | None = None
    dividend_yield: float | None = None
    rules: list[RuleResult]
    extras: dict = {}
    engine_version: str


@dataclass
class YearFundamentals:
    year: int
    revenue: float | None = None
    ebit: float | None = None
    depreciation: float | None = None
    net_income: float | None = None
    equity: float | None = None
    gross_debt: float | None = None
    cash: float | None = None
    operating_cash_flow: float | None = None
    investing_cash_flow: float | None = None
    dividends_paid: float | None = None

    @property
    def ebitda(self) -> float | None:
        if self.ebit is None:
            return None
        return self.ebit + abs(self.depreciation or 0.0)

    @property
    def net_debt(self) -> float | None:
        if self.gross_debt is None:
            return None
        return self.gross_debt - (self.cash or 0.0)

    @property
    def free_cash_flow(self) -> float | None:
        """Caixa operacional + caixa de investimento (que vem negativo na DFC)."""
        if self.operating_cash_flow is None or self.investing_cash_flow is None:
            return None
        return self.operating_cash_flow + self.investing_cash_flow


@dataclass
class StockSnapshot:
    """Tudo o que o motor de ações precisa saber sobre um ativo, já carregado.

    sector: bancos | seguros | energia | saneamento | telecom | perene | ciclico.
    segment: no setor de energia, transmissao | distribuicao | geracao | integrada.
    avg_daily_volume_brl: média dos últimos 3 meses de preço × volume.
    dividends_by_year: proventos por ação somados por ano civil (anos completos).
    pe_history / pb_history: séries mensais de P/L e P/VP dos últimos 5 anos, para "barato vs si mesmo".
    """

    ticker: str
    name: str
    sector: str
    segment: str | None = None
    price: float | None = None
    avg_daily_volume_brl: float | None = None
    shares_outstanding: float | None = None
    dividends_by_year: dict[int, float] = field(default_factory=dict)
    dividends_ttm: float | None = None
    avg_price_by_year: dict[int, float] = field(default_factory=dict)
    fundamentals: dict[int, YearFundamentals] = field(default_factory=dict)
    sector_metrics: dict[str, float] = field(default_factory=dict)
    pe_history: list[float] = field(default_factory=list)
    pb_history: list[float] = field(default_factory=list)
    current_year: int = 2026

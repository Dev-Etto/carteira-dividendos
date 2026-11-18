"""Tipos do motor de regras. O motor é puro: recebe um snapshot e devolve uma avaliação."""

from dataclasses import dataclass, field
from datetime import date
from typing import Literal

from pydantic import BaseModel

RuleStatus = Literal["ok", "warn", "fail", "na"]
FiiKind = Literal["papel", "tijolo", "fof", "hibrido"]
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
    current_assets: float | None = None
    current_liabilities: float | None = None
    short_term_debt: float | None = None
    fixed_assets: float | None = None

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


@dataclass(frozen=True)
class QuarterFundamentals:
    """Resultado de um trimestre (só os 3 meses), do ITR ou, no 4º, da DFP menos os três primeiros."""

    year: int
    quarter: int
    revenue: float | None = None
    net_income: float | None = None

    @property
    def index(self) -> int:
        """Posição contínua do trimestre (ano × 4 + trimestre), para achar trimestres seguidos."""
        return self.year * 4 + self.quarter


@dataclass
class StockSnapshot:
    """Tudo o que o motor de ações precisa saber sobre um ativo, já carregado.

    sector: bancos | seguros | energia | saneamento | telecom | perene | ciclico.
    segment: no setor de energia, transmissao | distribuicao | geracao | integrada.
    avg_daily_volume_brl: média dos últimos 3 meses de preço × volume.
    dividends_by_year: proventos por ação somados por ano civil (anos completos).
    pe_history / pb_history: séries mensais de P/L e P/VP dos últimos 5 anos, para "barato vs si mesmo".
    ntnb_real: juro real da NTN-B (Tesouro IPCA+) mais longa, em fração; o Graham liga o P/L máximo a ele.
    quarters: resultados trimestrais em ordem cronológica.
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
    ntnb_real: float | None = None
    quarters: list[QuarterFundamentals] = field(default_factory=list)


@dataclass
class FiiSnapshot:
    """Tudo o que o motor de FIIs precisa saber sobre um fundo, já carregado.

    kind: papel | tijolo | fof | hibrido, pela composição da carteira no informe mensal da CVM.
    segment: segmento declarado à CVM (Logística, Shoppings...), só para exibição.
    equity: patrimônio líquido em R$. nav_per_share: valor patrimonial da cota.
    admin_fee_month: taxa de administração do mês em fração do patrimônio.
    dividends_ttm / dividends_prev_ttm: proventos por cota nos últimos 12 meses e nos 12 anteriores.
    cdi / ntnb_real: CDI ao ano e juro real da NTN-B (Tesouro IPCA+) mais longa, em fração.
    largest_credit_share: maior ativo de crédito ÷ patrimônio (papel).
    largest_property_share: maior imóvel ÷ receita do fundo (tijolo).
    vacancy: vacância física média ponderada pela área; None quando o dado do fundo é inconsistente.
    """

    ticker: str
    name: str
    kind: FiiKind
    today: date
    segment: str | None = None
    price: float | None = None
    avg_daily_volume_brl: float | None = None
    equity: float | None = None
    nav_per_share: float | None = None
    holders: int | None = None
    listed: bool | None = None
    started_on: date | None = None
    admin_fee_month: float | None = None
    dividends_ttm: float | None = None
    dividends_prev_ttm: float | None = None
    cdi: float | None = None
    ntnb_real: float | None = None
    largest_credit_share: float | None = None
    largest_property_share: float | None = None
    properties: int | None = None
    vacancy: float | None = None


@dataclass
class EtfSnapshot:
    """O que o checklist de ETFs precisa saber, já carregado.

    equity: patrimônio em R$ (cadastro da CVM). admin_fee: taxa de administração ao ano, em fração,
    informada pelo usuário (não há fonte gratuita estruturada). dividends_ttm: proventos por cota nos
    últimos 12 meses, quando a fonte de cotações os traz (o Yahoo costuma não trazer para ETFs).
    distributes: se o ETF repassa os proventos, informado pelo usuário; None quando não informado.
    """

    ticker: str
    name: str
    price: float | None = None
    avg_daily_volume_brl: float | None = None
    equity: float | None = None
    admin_fee: float | None = None
    dividends_ttm: float | None = None
    distributes: bool | None = None

"""Schemas Pydantic de entrada e saída da API, na ordem das telas: ativos, perfil, carteira, renda fixa, aporte, painel."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.engine.types import RuleResult


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class AssetRow(BaseModel):
    ticker: str
    name: str
    asset_class: str
    sector: str
    segment: str | None
    price: float | None
    price_at: datetime | None
    score: int | None
    verdict: str | None
    ceiling_price: float | None
    margin_pct: float | None
    dividend_yield: float | None
    avg_daily_volume_brl: float | None = None
    evaluated_on: date | None
    favorite: bool = False


class AssetDetail(AssetRow):
    summary: str | None
    rules: list[RuleResult]
    extras: dict
    economic_group: str | None
    data_sources: dict[str, str | None]
    risks: list[str]


class AssetCreate(BaseModel):
    """Ativo novo. Ação exige o setor; num FII o tipo (papel, tijolo...) vem do informe da CVM."""

    ticker: str = Field(min_length=4, max_length=12)
    name: str
    asset_class: Literal["acao", "fii", "etf"] = "acao"
    sector: Literal["bancos", "seguros", "energia", "saneamento", "telecom", "perene", "ciclico"] | None = None
    segment: str | None = None
    economic_group: str | None = None

    @model_validator(mode="after")
    def _stock_needs_sector(self) -> "AssetCreate":
        if self.asset_class == "acao" and self.sector is None:
            raise ValueError("Informe o setor da ação")
        return self


class AssetUpdate(BaseModel):
    """Ajustes do usuário num ETF. Só os campos enviados mudam; null apaga o valor informado.

    admin_fee: taxa de administração ao ano, em fração (0,005 = 0,5%).
    distributes: se o ETF repassa os proventos (true) ou reinveste (false)."""

    favorite: bool | None = None
    admin_fee: float | None = Field(default=None, ge=0, le=0.1)
    distributes: bool | None = None


class PricePointOut(BaseModel):
    date: date
    close: float


class DividendYearOut(BaseModel):
    year: int
    amount: float
    dividend_yield: float | None


class ScorePointOut(BaseModel):
    date: date
    score: int
    verdict: str


class AssetHistory(BaseModel):
    """nav: valor patrimonial da cota mês a mês (só FIIs), para comparar com o preço."""

    prices: list[PricePointOut]
    dividends_by_year: list[DividendYearOut]
    scores: list[ScorePointOut]
    nav: list[PricePointOut] = []


class QuestionOption(BaseModel):
    label: str
    points: int


class Question(BaseModel):
    id: str
    text: str
    options: list[QuestionOption]


class ProfileIn(BaseModel):
    answers: dict[str, int]
    income_stability: Literal["estavel", "variavel", "instavel"]
    monthly_expenses: Decimal = Field(ge=0)
    monthly_contribution: Decimal = Field(ge=0)
    passive_income_goal: Decimal = Field(ge=0)
    keep_allocation: bool = False


class ProfileOut(ORM):
    risk_profile: str
    risk_description: str = ""
    income_stability: str
    monthly_expenses: Decimal
    emergency_months: int
    emergency_target: Decimal = Decimal(0)
    monthly_contribution: Decimal
    passive_income_goal: Decimal
    onboarded: bool
    answers: dict[str, int] = Field(default_factory=dict)


class AllocationItem(BaseModel):
    asset_class: Literal["renda_fixa", "acoes", "fiis", "etfs"]
    weight_pct: float = Field(ge=0, le=100)


class RuleConfigItem(BaseModel):
    key: str
    value: float
    default: float


class TransactionIn(BaseModel):
    ticker: str
    date: date
    kind: Literal["compra", "venda"]
    quantity: Decimal = Field(gt=0)
    price: Decimal = Field(gt=0)
    fees: Decimal = Field(default=Decimal(0), ge=0)


class TransactionOut(ORM):
    id: int
    ticker: str
    date: date
    kind: str
    quantity: Decimal
    price: Decimal
    fees: Decimal
    origin: str


class PositionOut(BaseModel):
    ticker: str
    name: str
    asset_class: str
    sector: str
    quantity: float
    avg_price: float
    total_cost: float
    price: float | None
    value: float
    profit: float
    profit_pct: float | None
    weight_pct: float
    income_12m: float
    yield_on_cost: float | None
    verdict: str | None = None


class FixedIncomeIn(BaseModel):
    name: str
    issuer: str
    kind: Literal["tesouro", "cdb", "lci", "lca", "outro"]
    indexer: Literal["cdi", "ipca", "pre", "selic"]
    rate: float
    start_date: date
    maturity: date | None = None
    daily_liquidity: bool = False
    amount: Decimal = Field(gt=0)
    is_emergency_reserve: bool = False
    fgc_covered: bool = True


class FixedIncomeOut(ORM):
    id: int
    name: str
    issuer: str
    kind: str
    indexer: str
    rate: float
    start_date: date
    maturity: date | None
    daily_liquidity: bool
    amount: Decimal
    is_emergency_reserve: bool
    fgc_covered: bool
    reserve_ok: bool | None = None
    reserve_reason: str | None = None


class ClassSlice(BaseModel):
    asset_class: str
    value: float
    current_pct: float
    target_pct: float


class PortfolioOut(BaseModel):
    positions: list[PositionOut]
    fixed_income: list[FixedIncomeOut]
    classes: list[ClassSlice]
    sectors: dict[str, float]
    total_invested: float
    reserve_value: float
    reserve_target: float
    income_12m: float
    alerts: list[str]


class CompareIn(BaseModel):
    kind: Literal["tesouro", "cdb", "lci", "lca", "outro"]
    indexer: Literal["cdi", "ipca", "pre", "selic"]
    rate: float
    days: int = Field(gt=0)


class CompareOut(BaseModel):
    gross_annual: float
    net_annual: float
    ir_rate: float
    tax_exempt: bool
    equivalent_label: str
    equivalent_rate: float
    vs_cdi_net: float


class TreasuryOut(BaseModel):
    name: str
    maturity: date
    date: date
    buy_rate: float | None
    buy_price: float | None


class MacroOut(BaseModel):
    selic_meta: float | None
    cdi: float | None
    ipca_12m: float | None
    as_of: date | None


class PlanIn(BaseModel):
    amount: float = Field(gt=0)


class PlanLineOut(BaseModel):
    asset_class: str
    product: str
    ticker: str | None
    quantity: int | None
    unit_price: float | None
    amount: float
    reason: str
    holding: FixedIncomeIn | None = None


class PlanOut(BaseModel):
    amount: float
    lines: list[PlanLineOut]
    notes: list[str]
    leftover: float


class PlanPurchaseIn(BaseModel):
    ticker: str
    quantity: Decimal = Field(gt=0)
    price: Decimal = Field(gt=0)
    fees: Decimal = Field(default=Decimal(0), ge=0)


class RegisterPlanIn(BaseModel):
    """Compras de ações e aplicações de renda fixa feitas a partir do plano. Precisa de pelo menos uma."""

    date: date
    purchases: list[PlanPurchaseIn] = Field(default_factory=list)
    holdings: list[FixedIncomeIn] = Field(default_factory=list)

    @model_validator(mode="after")
    def _not_empty(self) -> "RegisterPlanIn":
        if not self.purchases and not self.holdings:
            raise ValueError("Nada para registrar: marque ao menos uma compra ou aplicação")
        return self


class RegisterPlanOut(BaseModel):
    transactions: list[TransactionOut]
    holdings: list[FixedIncomeOut]


class NextStep(BaseModel):
    title: str
    description: str
    href: str


class DashboardOut(BaseModel):
    profile: ProfileOut
    total_invested: float
    reserve_value: float
    reserve_target: float
    income_12m: float
    passive_income_goal: float
    classes: list[ClassSlice]
    next_step: NextStep
    alerts: list[str]
    top_opportunities: list[AssetRow]
    macro: MacroOut
    last_sync: datetime | None


class SyncRunOut(ORM):
    source: str
    status: Literal["running", "ok", "error"]
    rows: int
    error: str | None
    started_at: datetime
    finished_at: datetime | None


class SyncStatus(BaseModel):
    running: bool
    step: str | None
    runs: list[SyncRunOut]

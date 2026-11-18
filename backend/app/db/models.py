"""Modelo de dados (Fase 1).

Dados de mercado usam float (vêm de fontes externas e servem para análise).
Valores do usuário (operações, aplicações) usam Numeric/Decimal para não errar
preço médio e IR por arredondamento.
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    false,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

Money = Numeric(18, 6, asdecimal=True)


class Base(DeclarativeBase):
    pass


class Asset(Base):
    """Ativo do universo.

    asset_class: acao | fii | etf.
    sector: em ações, bancos | seguros | energia | saneamento | telecom | perene | ciclico;
        em FIIs, o tipo pela carteira: papel | tijolo | fof | hibrido.
    segment: em energia, transmissao | geracao | distribuicao | integrada; em FIIs, o segmento declarado à CVM.
    favorite: ETF escolhido pelo usuário para receber aportes.
    admin_fee: taxa de administração ao ano (fração) informada pelo usuário; usada nos ETFs.
    distributes: se o ETF repassa os proventos, informado pelo usuário (o Yahoo não traz proventos de ETFs).
    """

    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticker: Mapped[str] = mapped_column(String(12), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    asset_class: Mapped[str] = mapped_column(String(20))
    sector: Mapped[str] = mapped_column(String(40))
    segment: Mapped[str | None] = mapped_column(String(40))
    cnpj: Mapped[str | None] = mapped_column(String(20), index=True)
    economic_group: Mapped[str | None] = mapped_column(String(60))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    shares_outstanding: Mapped[float | None] = mapped_column(Float)
    last_price: Mapped[float | None] = mapped_column(Float)
    last_price_at: Mapped[datetime | None] = mapped_column(DateTime)
    price_source: Mapped[str | None] = mapped_column(String(20))
    favorite: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    admin_fee: Mapped[float | None] = mapped_column(Float)
    distributes: Mapped[bool | None] = mapped_column(Boolean)

    evaluations: Mapped[list["Evaluation"]] = relationship(back_populates="asset")


class PriceDaily(Base):
    __tablename__ = "prices_daily"
    __table_args__ = (UniqueConstraint("asset_id", "date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)
    date: Mapped[date] = mapped_column(Date)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float, default=0)
    source: Mapped[str] = mapped_column(String(20))


class Dividend(Base):
    """Provento por ação/cota. ex_date = data ex (primeiro dia sem direito; é a data que o Yahoo informa).

    kind: dividendo | jcp | rendimento | amortizacao.
    """

    __tablename__ = "dividends"
    __table_args__ = (UniqueConstraint("asset_id", "ex_date", "kind", "amount"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)
    ex_date: Mapped[date] = mapped_column(Date)
    pay_date: Mapped[date | None] = mapped_column(Date)
    amount: Mapped[float] = mapped_column(Float)
    kind: Mapped[str] = mapped_column(String(20), default="dividendo")
    source: Mapped[str] = mapped_column(String(20))


class Split(Base):
    """Desdobramento (ratio > 1) ou grupamento (ratio < 1)."""

    __tablename__ = "splits"
    __table_args__ = (UniqueConstraint("asset_id", "date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)
    date: Mapped[date] = mapped_column(Date)
    ratio: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(20))


class Fundamental(Base):
    """Números anuais da DFP (CVM), consolidados, em R$ (não em milhares).

    current_assets e current_liabilities: ativo e passivo circulante (contas 1.01 e 2.01);
    short_term_debt: empréstimos de curto prazo (2.01.04); fixed_assets: imobilizado líquido (1.02.03).
    """

    __tablename__ = "fundamentals"
    __table_args__ = (UniqueConstraint("asset_id", "year"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)
    year: Mapped[int] = mapped_column(Integer)
    revenue: Mapped[float | None] = mapped_column(Float)
    ebit: Mapped[float | None] = mapped_column(Float)
    depreciation: Mapped[float | None] = mapped_column(Float)
    net_income: Mapped[float | None] = mapped_column(Float)
    equity: Mapped[float | None] = mapped_column(Float)
    gross_debt: Mapped[float | None] = mapped_column(Float)
    cash: Mapped[float | None] = mapped_column(Float)
    operating_cash_flow: Mapped[float | None] = mapped_column(Float)
    investing_cash_flow: Mapped[float | None] = mapped_column(Float)
    dividends_paid: Mapped[float | None] = mapped_column(Float)
    current_assets: Mapped[float | None] = mapped_column(Float)
    current_liabilities: Mapped[float | None] = mapped_column(Float)
    short_term_debt: Mapped[float | None] = mapped_column(Float)
    fixed_assets: Mapped[float | None] = mapped_column(Float)
    published_at: Mapped[date | None] = mapped_column(Date)
    source: Mapped[str] = mapped_column(String(20), default="cvm")


class SectorMetric(Base):
    """Indicadores setoriais (Basileia, inadimplência, índice combinado, concessões).

    Na Fase 1 vêm de data/sector_metrics.csv, editável à mão.
    """

    __tablename__ = "sector_metrics"
    __table_args__ = (UniqueConstraint("asset_id", "key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)
    key: Mapped[str] = mapped_column(String(40))
    value: Mapped[float] = mapped_column(Float)
    reference: Mapped[str | None] = mapped_column(String(20))
    source: Mapped[str] = mapped_column(String(40), default="manual")
    updated_at: Mapped[date] = mapped_column(Date)


class FiiReport(Base):
    """Informe mensal de um FII na CVM. Valores em R$; taxa de administração e composição em fração.

    paper, brick, fof, cash: peso de crédito, imóveis, cotas de FII e caixa no ativo do fundo.
    """

    __tablename__ = "fii_reports"
    __table_args__ = (UniqueConstraint("asset_id", "ref_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)
    ref_date: Mapped[date] = mapped_column(Date)
    equity: Mapped[float | None] = mapped_column(Float)
    shares: Mapped[float | None] = mapped_column(Float)
    nav_per_share: Mapped[float | None] = mapped_column(Float)
    holders: Mapped[int | None] = mapped_column(Integer)
    admin_fee: Mapped[float | None] = mapped_column(Float)
    paper: Mapped[float] = mapped_column(Float, default=0)
    brick: Mapped[float] = mapped_column(Float, default=0)
    fof: Mapped[float] = mapped_column(Float, default=0)
    cash: Mapped[float] = mapped_column(Float, default=0)
    started_on: Mapped[date | None] = mapped_column(Date)
    listed: Mapped[bool] = mapped_column(Boolean, default=True)


class FiiQuarterlyReport(Base):
    """Informe trimestral de um FII na CVM: imóveis e maior ativo de crédito (R$).

    vacancy: vacância física ponderada pela área; None quando o informe é inconsistente.
    largest_property_share: maior participação de um imóvel na receita do fundo.
    """

    __tablename__ = "fii_quarterly_reports"
    __table_args__ = (UniqueConstraint("asset_id", "ref_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)
    ref_date: Mapped[date] = mapped_column(Date)
    properties: Mapped[int | None] = mapped_column(Integer)
    vacancy: Mapped[float | None] = mapped_column(Float)
    largest_property_share: Mapped[float | None] = mapped_column(Float)
    largest_credit_value: Mapped[float | None] = mapped_column(Float)


class EtfReport(Base):
    """Patrimônio de um ETF no cadastro de fundos da CVM, na data informada pela CVM."""

    __tablename__ = "etf_reports"
    __table_args__ = (UniqueConstraint("asset_id", "ref_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)
    ref_date: Mapped[date] = mapped_column(Date)
    equity: Mapped[float | None] = mapped_column(Float)


class MacroRate(Base):
    """Série do Banco Central em fração decimal. series: selic_meta | cdi | ipca_12m."""

    __tablename__ = "macro_rates"
    __table_args__ = (UniqueConstraint("series", "date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    series: Mapped[str] = mapped_column(String(20))
    date: Mapped[date] = mapped_column(Date)
    value: Mapped[float] = mapped_column(Float)


class TreasuryBond(Base):
    __tablename__ = "treasury_bonds"
    __table_args__ = (UniqueConstraint("name", "maturity", "date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(60))
    maturity: Mapped[date] = mapped_column(Date)
    date: Mapped[date] = mapped_column(Date, index=True)
    buy_rate: Mapped[float | None] = mapped_column(Float)
    sell_rate: Mapped[float | None] = mapped_column(Float)
    buy_price: Mapped[float | None] = mapped_column(Float)
    sell_price: Mapped[float | None] = mapped_column(Float)


class Evaluation(Base):
    """Avaliação de um ativo num dia por uma metodologia. method: a chave da metodologia de seleção
    (barsi, bazin…) nas ações; nos FIIs e ETFs, que têm um motor só, a própria classe (fii, etf)."""

    __tablename__ = "evaluations"
    __table_args__ = (UniqueConstraint("asset_id", "date", "method", name="uq_evaluations_asset_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)
    date: Mapped[date] = mapped_column(Date)
    method: Mapped[str] = mapped_column(String(20), default="barsi", server_default="barsi")
    score: Mapped[int] = mapped_column(Integer)
    verdict: Mapped[str] = mapped_column(String(12))
    ceiling_price: Mapped[float | None] = mapped_column(Float)
    margin_pct: Mapped[float | None] = mapped_column(Float)
    dividend_yield: Mapped[float | None] = mapped_column(Float)
    summary: Mapped[str] = mapped_column(Text, default="")
    rules: Mapped[list] = mapped_column(JSON)
    extras: Mapped[dict] = mapped_column(JSON, default=dict)
    engine_version: Mapped[str] = mapped_column(String(10))

    asset: Mapped[Asset] = relationship(back_populates="evaluations")


class Profile(Base):
    """Perfil do investidor. selection_method e allocation_method: as metodologias escolhidas para
    avaliar ações e para dividir a carteira (chaves de `app/engine/metodos/registro.py`)."""

    __tablename__ = "profile"

    id: Mapped[int] = mapped_column(primary_key=True)
    risk_profile: Mapped[str] = mapped_column(String(20), default="moderado")
    income_stability: Mapped[str] = mapped_column(String(20), default="estavel")
    monthly_expenses: Mapped[Decimal] = mapped_column(Money, default=Decimal(0))
    emergency_months: Mapped[int] = mapped_column(Integer, default=6)
    monthly_contribution: Mapped[Decimal] = mapped_column(Money, default=Decimal(0))
    passive_income_goal: Mapped[Decimal] = mapped_column(Money, default=Decimal(0))
    onboarded: Mapped[bool] = mapped_column(Boolean, default=False)
    answers: Mapped[dict] = mapped_column(JSON, default=dict)
    selection_method: Mapped[str] = mapped_column(String(20), default="barsi", server_default="barsi")
    allocation_method: Mapped[str] = mapped_column(String(20), default="perfil", server_default="perfil")


class AllocationTarget(Base):
    """Peso-alvo de uma classe, em %. asset_class: renda_fixa | acoes | fiis | etfs."""

    __tablename__ = "allocation_targets"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_class: Mapped[str] = mapped_column(String(20), unique=True)
    weight_pct: Mapped[float] = mapped_column(Float)


class RuleConfig(Base):
    __tablename__ = "rule_config"

    key: Mapped[str] = mapped_column(String(60), primary_key=True)
    value: Mapped[float] = mapped_column(Float)


class Transaction(Base):
    """Compra ou venda. kind: compra | venda. origin: manual | aporte."""

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)
    date: Mapped[date] = mapped_column(Date)
    kind: Mapped[str] = mapped_column(String(10))
    quantity: Mapped[Decimal] = mapped_column(Money)
    price: Mapped[Decimal] = mapped_column(Money)
    fees: Mapped[Decimal] = mapped_column(Money, default=Decimal(0))
    origin: Mapped[str] = mapped_column(String(10), default="manual")
    import_hash: Mapped[str | None] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    asset: Mapped[Asset] = relationship()


class FixedIncomeHolding(Base):
    """Aplicação de renda fixa.

    kind: tesouro | cdb | lci | lca | outro.
    indexer: cdi | ipca | pre | selic.
    rate: % do CDI quando o indexador é cdi; taxa ao ano (prefixado ou spread sobre o IPCA) nos demais.
    """

    __tablename__ = "fixed_income_holdings"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    issuer: Mapped[str] = mapped_column(String(120))
    kind: Mapped[str] = mapped_column(String(20))
    indexer: Mapped[str] = mapped_column(String(10))
    rate: Mapped[float] = mapped_column(Float)
    start_date: Mapped[date] = mapped_column(Date)
    maturity: Mapped[date | None] = mapped_column(Date)
    daily_liquidity: Mapped[bool] = mapped_column(Boolean, default=False)
    amount: Mapped[Decimal] = mapped_column(Money)
    is_emergency_reserve: Mapped[bool] = mapped_column(Boolean, default=False)
    fgc_covered: Mapped[bool] = mapped_column(Boolean, default=True)


class IncomeReceived(Base):
    __tablename__ = "income_received"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)
    date: Mapped[date] = mapped_column(Date)
    amount: Mapped[Decimal] = mapped_column(Money)
    kind: Mapped[str] = mapped_column(String(20))


class SyncRun(Base):
    """Uma etapa de uma atualização de dados. status: running | ok | error."""

    __tablename__ = "sync_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(30))
    started_at: Mapped[datetime] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(10), default="running")
    rows: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text)

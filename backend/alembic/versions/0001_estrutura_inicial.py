"""estrutura inicial

Revision ID: b817a33c76df
Revises:
Create Date: 2026-11-16 00:34:49.825704

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "allocation_targets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("asset_class", sa.String(length=20), nullable=False),
        sa.Column("weight_pct", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asset_class"),
    )
    op.create_table(
        "assets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticker", sa.String(length=12), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("asset_class", sa.String(length=20), nullable=False),
        sa.Column("sector", sa.String(length=40), nullable=False),
        sa.Column("segment", sa.String(length=40), nullable=True),
        sa.Column("cnpj", sa.String(length=20), nullable=True),
        sa.Column("economic_group", sa.String(length=60), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("shares_outstanding", sa.Float(), nullable=True),
        sa.Column("last_price", sa.Float(), nullable=True),
        sa.Column("last_price_at", sa.DateTime(), nullable=True),
        sa.Column("price_source", sa.String(length=20), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("assets", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_assets_cnpj"), ["cnpj"], unique=False)
        batch_op.create_index(batch_op.f("ix_assets_ticker"), ["ticker"], unique=True)

    op.create_table(
        "fixed_income_holdings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("issuer", sa.String(length=120), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("indexer", sa.String(length=10), nullable=False),
        sa.Column("rate", sa.Float(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("maturity", sa.Date(), nullable=True),
        sa.Column("daily_liquidity", sa.Boolean(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("is_emergency_reserve", sa.Boolean(), nullable=False),
        sa.Column("fgc_covered", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "macro_rates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("series", sa.String(length=20), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("series", "date"),
    )
    op.create_table(
        "profile",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("risk_profile", sa.String(length=20), nullable=False),
        sa.Column("income_stability", sa.String(length=20), nullable=False),
        sa.Column("monthly_expenses", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("emergency_months", sa.Integer(), nullable=False),
        sa.Column("monthly_contribution", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("passive_income_goal", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("onboarded", sa.Boolean(), nullable=False),
        sa.Column("answers", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "rule_config",
        sa.Column("key", sa.String(length=60), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )
    op.create_table(
        "sync_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=30), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(length=10), nullable=False),
        sa.Column("rows", sa.Integer(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "treasury_bonds",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=60), nullable=False),
        sa.Column("maturity", sa.Date(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("buy_rate", sa.Float(), nullable=True),
        sa.Column("sell_rate", sa.Float(), nullable=True),
        sa.Column("buy_price", sa.Float(), nullable=True),
        sa.Column("sell_price", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", "maturity", "date"),
    )
    with op.batch_alter_table("treasury_bonds", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_treasury_bonds_date"), ["date"], unique=False)

    op.create_table(
        "dividends",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("ex_date", sa.Date(), nullable=False),
        sa.Column("pay_date", sa.Date(), nullable=True),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.ForeignKeyConstraint(
            ["asset_id"],
            ["assets.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asset_id", "ex_date", "kind", "amount"),
    )
    with op.batch_alter_table("dividends", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_dividends_asset_id"), ["asset_id"], unique=False)

    op.create_table(
        "evaluations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("verdict", sa.String(length=12), nullable=False),
        sa.Column("ceiling_price", sa.Float(), nullable=True),
        sa.Column("margin_pct", sa.Float(), nullable=True),
        sa.Column("dividend_yield", sa.Float(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("rules", sa.JSON(), nullable=False),
        sa.Column("extras", sa.JSON(), nullable=False),
        sa.Column("engine_version", sa.String(length=10), nullable=False),
        sa.ForeignKeyConstraint(
            ["asset_id"],
            ["assets.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asset_id", "date"),
    )
    with op.batch_alter_table("evaluations", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_evaluations_asset_id"), ["asset_id"], unique=False)

    op.create_table(
        "fundamentals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("revenue", sa.Float(), nullable=True),
        sa.Column("ebit", sa.Float(), nullable=True),
        sa.Column("depreciation", sa.Float(), nullable=True),
        sa.Column("net_income", sa.Float(), nullable=True),
        sa.Column("equity", sa.Float(), nullable=True),
        sa.Column("gross_debt", sa.Float(), nullable=True),
        sa.Column("cash", sa.Float(), nullable=True),
        sa.Column("operating_cash_flow", sa.Float(), nullable=True),
        sa.Column("investing_cash_flow", sa.Float(), nullable=True),
        sa.Column("dividends_paid", sa.Float(), nullable=True),
        sa.Column("published_at", sa.Date(), nullable=True),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.ForeignKeyConstraint(
            ["asset_id"],
            ["assets.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asset_id", "year"),
    )
    with op.batch_alter_table("fundamentals", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_fundamentals_asset_id"), ["asset_id"], unique=False)

    op.create_table(
        "income_received",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.ForeignKeyConstraint(
            ["asset_id"],
            ["assets.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("income_received", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_income_received_asset_id"), ["asset_id"], unique=False)

    op.create_table(
        "prices_daily",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("close", sa.Float(), nullable=False),
        sa.Column("volume", sa.Float(), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.ForeignKeyConstraint(
            ["asset_id"],
            ["assets.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asset_id", "date"),
    )
    with op.batch_alter_table("prices_daily", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_prices_daily_asset_id"), ["asset_id"], unique=False)

    op.create_table(
        "sector_metrics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=40), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("reference", sa.String(length=20), nullable=True),
        sa.Column("source", sa.String(length=40), nullable=False),
        sa.Column("updated_at", sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(
            ["asset_id"],
            ["assets.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asset_id", "key"),
    )
    with op.batch_alter_table("sector_metrics", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_sector_metrics_asset_id"), ["asset_id"], unique=False)

    op.create_table(
        "splits",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("ratio", sa.Float(), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.ForeignKeyConstraint(
            ["asset_id"],
            ["assets.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asset_id", "date"),
    )
    with op.batch_alter_table("splits", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_splits_asset_id"), ["asset_id"], unique=False)

    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("kind", sa.String(length=10), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("price", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("fees", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("origin", sa.String(length=10), nullable=False),
        sa.Column("import_hash", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(
            ["asset_id"],
            ["assets.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("import_hash"),
    )
    with op.batch_alter_table("transactions", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_transactions_asset_id"), ["asset_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("transactions", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_transactions_asset_id"))

    op.drop_table("transactions")
    with op.batch_alter_table("splits", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_splits_asset_id"))

    op.drop_table("splits")
    with op.batch_alter_table("sector_metrics", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_sector_metrics_asset_id"))

    op.drop_table("sector_metrics")
    with op.batch_alter_table("prices_daily", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_prices_daily_asset_id"))

    op.drop_table("prices_daily")
    with op.batch_alter_table("income_received", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_income_received_asset_id"))

    op.drop_table("income_received")
    with op.batch_alter_table("fundamentals", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_fundamentals_asset_id"))

    op.drop_table("fundamentals")
    with op.batch_alter_table("evaluations", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_evaluations_asset_id"))

    op.drop_table("evaluations")
    with op.batch_alter_table("dividends", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_dividends_asset_id"))

    op.drop_table("dividends")
    with op.batch_alter_table("treasury_bonds", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_treasury_bonds_date"))

    op.drop_table("treasury_bonds")
    op.drop_table("sync_runs")
    op.drop_table("rule_config")
    op.drop_table("profile")
    op.drop_table("macro_rates")
    op.drop_table("fixed_income_holdings")
    with op.batch_alter_table("assets", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_assets_ticker"))
        batch_op.drop_index(batch_op.f("ix_assets_cnpj"))

    op.drop_table("assets")
    op.drop_table("allocation_targets")

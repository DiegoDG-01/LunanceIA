"""instrumentos, precios de cierre y tipo de cambio

Revision ID: 928de06f4ac9
Revises: 8397e1f3bc4b
Create Date: 2026-11-14 12:00:00.000000

Tablas globales (no pertenecen a un usuario) para acciones, ETFs y FIBRAs:
- `instruments`: catálogo de valores de BMV/BIVA, SIC y EE. UU. Solo los que tienen
  `tracked_since` reciben precios.
- `instrument_provider_symbols`: cómo llama cada proveedor a un valor y si lo tiene.
- `instrument_prices`: cierre diario sin ajustar, con el proveedor que lo dio.
- `fx_rates`: tipo de cambio diario (FIX de Banxico para USD/MXN).
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "928de06f4ac9"
down_revision: str | None = "8397e1f3bc4b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MARKET = sa.Enum("BMV", "SIC", "US", name="market")
INSTRUMENT_TYPE = sa.Enum("STOCK", "ETF", "FIBRA", "OTHER", name="instrumenttype")
SYMBOL_STATUS = sa.Enum("ACTIVE", "UNSUPPORTED", name="providersymbolstatus")


def upgrade() -> None:
    op.create_table(
        "instruments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("uuid", sa.CHAR(length=36), nullable=False),
        sa.Column("market", MARKET, nullable=False),
        sa.Column("symbol", sa.String(length=30), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("instrument_type", INSTRUMENT_TYPE, nullable=False),
        sa.Column("currency", sa.CHAR(length=3), nullable=False),
        sa.Column("isin", sa.String(length=12), nullable=True),
        sa.Column("exchange", sa.String(length=60), nullable=True),
        sa.Column("preferred_provider", sa.String(length=20), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("tracked_since", sa.Date(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("market", "symbol", name="uq_instrument_market_symbol"),
    )
    op.create_index(op.f("ix_instruments_uuid"), "instruments", ["uuid"], unique=True)
    op.create_index("idx_instrument_name", "instruments", ["name"])
    op.create_index("idx_instrument_tracked_since", "instruments", ["tracked_since"])

    op.create_table(
        "instrument_provider_symbols",
        sa.Column("instrument_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=20), nullable=False),
        sa.Column("provider_symbol", sa.String(length=40), nullable=False),
        sa.Column("status", SYMBOL_STATUS, nullable=False),
        sa.Column(
            "checked_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["instrument_id"], ["instruments.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("instrument_id", "provider"),
    )

    op.create_table(
        "instrument_prices",
        sa.Column("instrument_id", sa.Integer(), nullable=False),
        sa.Column("price_date", sa.Date(), nullable=False),
        sa.Column("close", sa.DECIMAL(precision=20, scale=6), nullable=False),
        sa.Column("traded_value", sa.DECIMAL(precision=20, scale=2), nullable=True),
        sa.Column("is_trading_day", sa.Boolean(), nullable=False),
        sa.Column("provider", sa.String(length=20), nullable=False),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["instrument_id"], ["instruments.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("instrument_id", "price_date"),
    )

    op.create_table(
        "fx_rates",
        sa.Column("base", sa.CHAR(length=3), nullable=False),
        sa.Column("quote", sa.CHAR(length=3), nullable=False),
        sa.Column("rate_date", sa.Date(), nullable=False),
        sa.Column("rate", sa.DECIMAL(precision=18, scale=8), nullable=False),
        sa.Column("provider", sa.String(length=20), nullable=False),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("base", "quote", "rate_date"),
    )


def downgrade() -> None:
    op.drop_table("fx_rates")
    op.drop_table("instrument_prices")
    op.drop_table("instrument_provider_symbols")
    op.drop_index("idx_instrument_tracked_since", table_name="instruments")
    op.drop_index("idx_instrument_name", table_name="instruments")
    op.drop_index(op.f("ix_instruments_uuid"), table_name="instruments")
    op.drop_table("instruments")

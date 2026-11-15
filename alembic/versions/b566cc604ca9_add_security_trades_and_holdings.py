"""operaciones sobre valores y tenencias

Revision ID: b566cc604ca9
Revises: 928de06f4ac9
Create Date: 2026-11-14 18:00:00.000000

- `security_trades`: compras, ventas, dividendos y splits de un valor en una cuenta.
  `cash_amount` es lo que entra o sale del disponible y `transaction_id` la transacción
  que lo movió (única: una transacción es de una sola operación).
- `security_holdings`: cantidad, costo promedio, ganancia realizada y dividendos de cada
  (cuenta, valor). Es una caché que se recalcula de las operaciones.

Los valores no se borran mientras tengan operaciones (`ON DELETE RESTRICT`).
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b566cc604ca9"
down_revision: str | None = "928de06f4ac9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TRADE_TYPE = sa.Enum("BUY", "SELL", "DIVIDEND", "SPLIT", name="tradetype")
HOLDING_STATUS = sa.Enum("OPEN", "CLOSED", name="holdingstatus")


def upgrade() -> None:
    op.create_table(
        "security_trades",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("uuid", sa.CHAR(length=36), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("instrument_id", sa.Integer(), nullable=False),
        sa.Column("trade_type", TRADE_TYPE, nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("quantity", sa.DECIMAL(precision=24, scale=8), nullable=False),
        sa.Column("price", sa.DECIMAL(precision=20, scale=6), nullable=False),
        sa.Column("fees", sa.DECIMAL(precision=15, scale=2), nullable=False),
        sa.Column("tax_withheld", sa.DECIMAL(precision=15, scale=2), nullable=False),
        sa.Column("gross_amount", sa.DECIMAL(precision=15, scale=2), nullable=True),
        sa.Column("cash_amount", sa.DECIMAL(precision=15, scale=2), nullable=False),
        sa.Column("split_from", sa.Integer(), nullable=True),
        sa.Column("split_to", sa.Integer(), nullable=True),
        sa.Column("transaction_id", sa.Integer(), nullable=True),
        sa.Column("notes", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["instrument_id"], ["instruments.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["transaction_id"], ["transactions.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("transaction_id"),
    )
    op.create_index(
        op.f("ix_security_trades_uuid"), "security_trades", ["uuid"], unique=True
    )
    op.create_index(
        op.f("ix_security_trades_user_id"), "security_trades", ["user_id"]
    )
    op.create_index(
        "idx_security_trade_account_instrument_date",
        "security_trades",
        ["account_id", "instrument_id", "trade_date"],
    )

    op.create_table(
        "security_holdings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("uuid", sa.CHAR(length=36), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("instrument_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.DECIMAL(precision=24, scale=8), nullable=False),
        sa.Column("avg_cost", sa.DECIMAL(precision=20, scale=6), nullable=False),
        sa.Column("cost_basis", sa.DECIMAL(precision=15, scale=2), nullable=False),
        sa.Column("realized_pnl", sa.DECIMAL(precision=15, scale=2), nullable=False),
        sa.Column("dividends", sa.DECIMAL(precision=15, scale=2), nullable=False),
        sa.Column("status", HOLDING_STATUS, nullable=False),
        sa.Column("opened_at", sa.Date(), nullable=True),
        sa.Column("closed_at", sa.Date(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["instrument_id"], ["instruments.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "account_id", "instrument_id", name="uq_holding_account_instrument"
        ),
    )
    op.create_index(
        op.f("ix_security_holdings_uuid"), "security_holdings", ["uuid"], unique=True
    )
    op.create_index(
        op.f("ix_security_holdings_user_id"), "security_holdings", ["user_id"]
    )
    op.create_index(
        op.f("ix_security_holdings_instrument_id"),
        "security_holdings",
        ["instrument_id"],
    )


def downgrade() -> None:
    op.drop_table("security_holdings")
    op.drop_table("security_trades")

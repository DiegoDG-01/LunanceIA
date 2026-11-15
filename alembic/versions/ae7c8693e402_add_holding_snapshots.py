"""fotos diarias de las tenencias

Revision ID: ae7c8693e402
Revises: b566cc604ca9
Create Date: 2026-11-14 21:00:00.000000

- `holding_snapshots`: cómo estaba cada tenencia al final de cada día de calendario
  (cantidad, último cierre conocido, valor, valor en pesos, costo y ganancias). Se
  reconstruye de las operaciones, los precios y el tipo de cambio.
- `security_holdings.snapshots_through`: hasta qué día están hechas las fotos.
- `security_holdings.snapshots_dirty_from`: desde qué día hay que rehacerlas porque cambió
  una operación, un precio o un tipo de cambio. Las tenencias que ya existen quedan sin
  fotos y la primera corrida las construye completas.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ae7c8693e402"
down_revision: str | None = "b566cc604ca9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "security_holdings", sa.Column("snapshots_through", sa.Date(), nullable=True)
    )
    op.add_column(
        "security_holdings", sa.Column("snapshots_dirty_from", sa.Date(), nullable=True)
    )
    op.create_index(
        op.f("ix_security_holdings_snapshots_dirty_from"),
        "security_holdings",
        ["snapshots_dirty_from"],
    )
    op.create_table(
        "holding_snapshots",
        sa.Column("holding_id", sa.Integer(), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("quantity", sa.DECIMAL(precision=24, scale=8), nullable=False),
        sa.Column("close", sa.DECIMAL(precision=20, scale=6), nullable=True),
        sa.Column("price_date", sa.Date(), nullable=True),
        sa.Column("fx_rate", sa.DECIMAL(precision=18, scale=8), nullable=True),
        sa.Column("market_value", sa.DECIMAL(precision=15, scale=2), nullable=True),
        sa.Column("market_value_mxn", sa.DECIMAL(precision=15, scale=2), nullable=True),
        sa.Column("cost_basis", sa.DECIMAL(precision=15, scale=2), nullable=False),
        sa.Column("realized_pnl", sa.DECIMAL(precision=15, scale=2), nullable=False),
        sa.Column("dividends", sa.DECIMAL(precision=15, scale=2), nullable=False),
        sa.Column("unrealized_pnl", sa.DECIMAL(precision=15, scale=2), nullable=True),
        sa.ForeignKeyConstraint(
            ["holding_id"], ["security_holdings.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("holding_id", "snapshot_date"),
    )


def downgrade() -> None:
    op.drop_table("holding_snapshots")
    op.drop_index(
        op.f("ix_security_holdings_snapshots_dirty_from"),
        table_name="security_holdings",
    )
    op.drop_column("security_holdings", "snapshots_dirty_from")
    op.drop_column("security_holdings", "snapshots_through")

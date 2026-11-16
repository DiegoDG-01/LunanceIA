"""moneda de los presupuestos

Revision ID: d52e8f3b1c20
Revises: c41d7e2a9b10
Create Date: 2026-11-15 18:00:00.000000

`budgets.currency`: la moneda del límite. Un presupuesto solo cuenta los gastos de cuentas
en su moneda; los que ya existen quedan en MXN, que es como se calculaban.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d52e8f3b1c20"
down_revision: str | None = "c41d7e2a9b10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "budgets",
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="MXN"),
    )


def downgrade() -> None:
    op.drop_column("budgets", "currency")

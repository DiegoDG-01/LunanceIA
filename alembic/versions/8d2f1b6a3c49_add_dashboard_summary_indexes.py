"""add dashboard summary indexes

Revision ID: 8d2f1b6a3c49
Revises: 4b6e7f8a9c01
Create Date: 2026-09-21 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8d2f1b6a3c49"
down_revision: str | None = "4b6e7f8a9c01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_transactions_user_type_date",
        "transactions",
        ["user_id", "type", "transaction_date"],
        unique=False,
    )
    op.create_index(
        "ix_budgets_user_active",
        "budgets",
        ["user_id", "is_active"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_budgets_user_active", table_name="budgets")
    op.drop_index("ix_transactions_user_type_date", table_name="transactions")

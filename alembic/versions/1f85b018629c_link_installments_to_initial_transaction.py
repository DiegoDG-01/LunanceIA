"""link installment purchases to their initial expense transaction

Revision ID: 1f85b018629c
Revises: a1c73f5b8e40
Create Date: 2026-08-18
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "1f85b018629c"
down_revision: Union[str, None] = "a1c73f5b8e40"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "installment_purchases",
        sa.Column("initial_transaction_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_installment_purchases_initial_transaction_id_transactions",
        "installment_purchases",
        "transactions",
        ["initial_transaction_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_installment_purchases_initial_transaction_id_transactions",
        "installment_purchases",
        type_="foreignkey",
    )
    op.drop_column("installment_purchases", "initial_transaction_id")

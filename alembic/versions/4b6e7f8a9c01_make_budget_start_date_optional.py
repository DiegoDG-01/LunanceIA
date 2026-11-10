"""make budget start date optional

Revision ID: 4b6e7f8a9c01
Revises: 1f85b018629c
Create Date: 2026-09-17 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4b6e7f8a9c01"
down_revision: str | None = "1f85b018629c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "budgets",
        "start_date",
        existing_type=sa.Date(),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "budgets",
        "start_date",
        existing_type=sa.Date(),
        nullable=False,
    )

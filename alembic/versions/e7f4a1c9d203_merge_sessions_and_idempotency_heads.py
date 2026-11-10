"""merge sessions and idempotency heads

Revision ID: e7f4a1c9d203
Revises: c3a91f7e2b10, d5e2b8c4a917
Create Date: 2026-11-10 10:08:05.709476

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e7f4a1c9d203"
down_revision: Union[str, None] = ("c3a91f7e2b10", "d5e2b8c4a917")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

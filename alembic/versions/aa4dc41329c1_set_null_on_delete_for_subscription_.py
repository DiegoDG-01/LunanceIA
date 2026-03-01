"""Set null on delete for subscription_charges transaction_id

Revision ID: aa4dc41329c1
Revises: 809e09ff210b
Create Date: 2026-02-03 19:29:53.413186

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'aa4dc41329c1'
down_revision: Union[str, None] = '809e09ff210b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint('subscription_charges_ibfk_2', 'subscription_charges', type_='foreignkey')
    op.create_foreign_key(
        'fk_subscription_charges_transaction_id',
        'subscription_charges',
        'transactions',
        ['transaction_id'],
        ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_subscription_charges_transaction_id', 'subscription_charges', type_='foreignkey')
    op.create_foreign_key(
        'subscription_charges_ibfk_2',
        'subscription_charges',
        'transactions',
        ['transaction_id'],
        ['id']
    )

"""add cap and overflow destination to investment positions

Revision ID: a1c73f5b8e40
Revises: e5f2a8c94d17
Create Date: 2026-08-16 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a1c73f5b8e40'
down_revision: Union[str, None] = 'e5f2a8c94d17'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Aditiva y nullable: los apartados existentes quedan sin tope, que es
    # exactamente el comportamiento que tienen hoy.
    op.add_column(
        'investment_positions',
        sa.Column('max_balance', sa.DECIMAL(precision=15, scale=2), nullable=True)
    )
    op.add_column(
        'investment_positions',
        sa.Column(
            'overflow_action',
            sa.Enum('TO_AVAILABLE', 'TO_POSITION', name='overflowaction'),
            nullable=True
        )
    )
    op.add_column(
        'investment_positions',
        sa.Column('overflow_position_id', sa.Integer(), nullable=True)
    )
    op.create_index(
        op.f('ix_investment_positions_overflow_position_id'),
        'investment_positions', ['overflow_position_id'], unique=False
    )
    # SET NULL: si el destino desaparece, el apartado que lo apuntaba
    # sobrevive y su excedente pasa al saldo disponible.
    op.create_foreign_key(
        'fk_investment_positions_overflow_position_id', 'investment_positions',
        'investment_positions', ['overflow_position_id'], ['id'], ondelete='SET NULL'
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        'fk_investment_positions_overflow_position_id',
        'investment_positions', type_='foreignkey'
    )
    op.drop_index(
        op.f('ix_investment_positions_overflow_position_id'),
        table_name='investment_positions'
    )
    op.drop_column('investment_positions', 'overflow_position_id')
    op.drop_column('investment_positions', 'overflow_action')
    op.drop_column('investment_positions', 'max_balance')

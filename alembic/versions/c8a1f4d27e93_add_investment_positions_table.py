"""add investment positions table and position_id references

Revision ID: c8a1f4d27e93
Revises: b808e02b7a51
Create Date: 2026-08-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c8a1f4d27e93'
down_revision: Union[str, None] = 'b808e02b7a51'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('investment_positions',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('account_id', sa.Integer(), nullable=False),
    sa.Column('uuid', sa.CHAR(length=36), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('position_type', sa.Enum('ON_DEMAND', 'FIXED_TERM', name='positiontype'), nullable=False),
    sa.Column('status', sa.Enum('ACTIVE', 'MATURED', 'LIQUIDATED', name='positionstatus'), nullable=False),
    sa.Column('balance', sa.DECIMAL(precision=15, scale=2), nullable=False),
    sa.Column('accrued_yield', sa.DECIMAL(precision=15, scale=2), nullable=False),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('annual_rate', sa.DECIMAL(precision=5, scale=2), nullable=False),
    sa.Column('interest_type', sa.Enum('SIMPLE', 'COMPOUND', name='interesttype'), nullable=False),
    sa.Column('base_principal', sa.DECIMAL(precision=15, scale=2), nullable=True),
    sa.Column('start_date', sa.Date(), nullable=False),
    sa.Column('term_days', sa.Integer(), nullable=True),
    sa.Column('lock_period_end_date', sa.Date(), nullable=True),
    sa.Column('maturity_date', sa.Date(), nullable=True),
    sa.Column('early_withdrawal_penalty', sa.DECIMAL(precision=5, scale=2), nullable=True),
    sa.Column('on_maturity', sa.Enum('AUTO_RENEW', 'LIQUIDATE', 'HOLD', name='maturityaction'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_investment_positions_uuid'), 'investment_positions', ['uuid'], unique=True)
    op.create_index(op.f('ix_investment_positions_account_id'), 'investment_positions', ['account_id'], unique=False)
    op.create_index('idx_positions_status', 'investment_positions', ['status'], unique=False)
    op.create_index('idx_positions_maturity_date', 'investment_positions', ['maturity_date'], unique=False)

    op.add_column('investment_yields', sa.Column('position_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_investment_yields_position_id'), 'investment_yields', ['position_id'], unique=False)
    op.create_foreign_key(
        'fk_investment_yields_position_id', 'investment_yields',
        'investment_positions', ['position_id'], ['id'], ondelete='CASCADE'
    )

    op.add_column('transactions', sa.Column('position_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_transactions_position_id'), 'transactions', ['position_id'], unique=False)
    op.create_foreign_key(
        'fk_transactions_position_id', 'transactions',
        'investment_positions', ['position_id'], ['id'], ondelete='SET NULL'
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_transactions_position_id', 'transactions', type_='foreignkey')
    op.drop_index(op.f('ix_transactions_position_id'), table_name='transactions')
    op.drop_column('transactions', 'position_id')

    op.drop_constraint('fk_investment_yields_position_id', 'investment_yields', type_='foreignkey')
    op.drop_index(op.f('ix_investment_yields_position_id'), table_name='investment_yields')
    op.drop_column('investment_yields', 'position_id')

    op.drop_index('idx_positions_maturity_date', table_name='investment_positions')
    op.drop_index('idx_positions_status', table_name='investment_positions')
    op.drop_index(op.f('ix_investment_positions_account_id'), table_name='investment_positions')
    op.drop_index(op.f('ix_investment_positions_uuid'), table_name='investment_positions')
    op.drop_table('investment_positions')

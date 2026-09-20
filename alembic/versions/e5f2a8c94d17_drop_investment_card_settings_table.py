"""drop investment_card_settings table

La configuración de inversión vive ahora en investment_positions (un
apartado por posición); esta tabla quedó sin escrituras ni lecturas.

El downgrade la recrea y la repuebla de forma aproximada desde el apartado
activo más antiguo de cada cuenta (la relación original era 1:1 por cuenta).

Revision ID: e5f2a8c94d17
Revises: d4b7e91c52a8
Create Date: 2026-08-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e5f2a8c94d17'
down_revision: Union[str, None] = 'd4b7e91c52a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_table('investment_card_settings')


def downgrade() -> None:
    """Downgrade schema (best effort)."""
    op.create_table('investment_card_settings',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('account_id', sa.Integer(), nullable=False),
    sa.Column('uuid', sa.CHAR(length=36), nullable=False),
    sa.Column('investment_type', sa.String(length=50), nullable=False),
    sa.Column('investment_rate', sa.DECIMAL(precision=5, scale=2), nullable=False),
    sa.Column('interest_type', sa.Enum('SIMPLE', 'COMPOUND', name='interesttype'), nullable=False),
    sa.Column('lock_period_end_date', sa.Date(), nullable=True),
    sa.Column('maturity_date', sa.Date(), nullable=True),
    sa.Column('early_withdrawal_penalty', sa.DECIMAL(precision=5, scale=2), nullable=True),
    sa.Column('base_principal', sa.DECIMAL(precision=15, scale=2), nullable=True),
    sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('account_id')
    )
    op.create_index(op.f('ix_investment_card_settings_uuid'), 'investment_card_settings', ['uuid'], unique=True)
    op.create_index('idx_lock_period_end_date', 'investment_card_settings', ['lock_period_end_date'], unique=False)
    op.create_index('idx_maturity_date', 'investment_card_settings', ['maturity_date'], unique=False)

    op.execute("""
        INSERT INTO investment_card_settings (
            account_id, uuid, investment_type, investment_rate, interest_type,
            lock_period_end_date, maturity_date, early_withdrawal_penalty,
            base_principal
        )
        SELECT
            p.account_id,
            UUID(),
            CASE WHEN p.position_type = 'FIXED_TERM' THEN 'fixed_term' ELSE 'variable' END,
            p.annual_rate,
            p.interest_type,
            p.lock_period_end_date,
            p.maturity_date,
            p.early_withdrawal_penalty,
            p.base_principal
        FROM investment_positions p
        WHERE p.status = 'ACTIVE'
          AND p.id = (
              SELECT MIN(p2.id) FROM investment_positions p2
              WHERE p2.account_id = p.account_id AND p2.status = 'ACTIVE'
          )
    """)

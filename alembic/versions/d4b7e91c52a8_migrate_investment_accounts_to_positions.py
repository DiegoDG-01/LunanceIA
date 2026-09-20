"""migrate investment accounts to positions

Convierte cada cuenta con investment_card_settings en una cuenta con un
apartado (investment_position):
  - El saldo completo de la cuenta pasa al apartado y el saldo disponible
    queda en 0 (current_balance = solo disponible).
  - Los investment_yields históricos se re-apuntan al apartado nuevo.
  - La unicidad de rendimientos pasa de (account_id, yield_date) a
    (position_id, yield_date) para permitir varios apartados por cuenta.

Los apartados migrados quedan con on_maturity=HOLD (lo más conservador).
Un settings 'fixed_term' sin maturity_date se migra como ON_DEMAND para
que siga rindiendo a la vista.

Revision ID: d4b7e91c52a8
Revises: c8a1f4d27e93
Create Date: 2026-08-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd4b7e91c52a8'
down_revision: Union[str, None] = 'c8a1f4d27e93'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Un apartado por cada configuración de inversión existente
    op.execute("""
        INSERT INTO investment_positions (
            account_id, uuid, name, position_type, status, balance,
            accrued_yield, currency, annual_rate, interest_type,
            base_principal, start_date, term_days, lock_period_end_date,
            maturity_date, early_withdrawal_penalty, on_maturity
        )
        SELECT
            a.id,
            UUID(),
            a.name,
            CASE
                WHEN s.investment_type = 'fixed_term' AND s.maturity_date IS NOT NULL
                THEN 'FIXED_TERM' ELSE 'ON_DEMAND'
            END,
            'ACTIVE',
            a.current_balance,
            0,
            a.currency,
            s.investment_rate,
            s.interest_type,
            s.base_principal,
            DATE(a.creation_date),
            CASE
                WHEN s.investment_type = 'fixed_term' AND s.maturity_date IS NOT NULL
                THEN GREATEST(DATEDIFF(s.maturity_date, DATE(a.creation_date)), 1)
                ELSE NULL
            END,
            s.lock_period_end_date,
            CASE
                WHEN s.investment_type = 'fixed_term' THEN s.maturity_date
                ELSE NULL
            END,
            s.early_withdrawal_penalty,
            'HOLD'
        FROM investment_card_settings s
        INNER JOIN accounts a ON a.id = s.account_id
    """)

    # 2. Re-apuntar los rendimientos históricos al apartado nuevo
    op.execute("""
        UPDATE investment_yields y
        INNER JOIN investment_positions p ON p.account_id = y.account_id
        SET y.position_id = p.id
        WHERE y.position_id IS NULL
    """)

    # 3. El dinero queda apartado: el disponible de esas cuentas pasa a 0
    op.execute("""
        UPDATE accounts a
        INNER JOIN investment_positions p ON p.account_id = a.id
        SET a.current_balance = 0
    """)

    # 4. Unicidad por apartado en vez de por cuenta
    op.drop_constraint('uq_account__yield_date', 'investment_yields', type_='unique')
    op.create_unique_constraint(
        'uq_position__yield_date', 'investment_yields', ['position_id', 'yield_date']
    )


def downgrade() -> None:
    """Downgrade schema (best effort: regresa el dinero apartado al disponible)."""
    op.drop_constraint('uq_position__yield_date', 'investment_yields', type_='unique')
    op.create_unique_constraint(
        'uq_account__yield_date', 'investment_yields', ['account_id', 'yield_date']
    )

    op.execute("""
        UPDATE accounts a
        INNER JOIN (
            SELECT account_id, SUM(balance + accrued_yield) AS total
            FROM investment_positions
            WHERE status IN ('ACTIVE', 'MATURED')
            GROUP BY account_id
        ) p ON p.account_id = a.id
        SET a.current_balance = a.current_balance + p.total
    """)

    op.execute("UPDATE investment_yields SET position_id = NULL")
    op.execute("DELETE FROM investment_positions")

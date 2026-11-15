"""monedas de cuentas y apartados en mayúsculas

Revision ID: c41d7e2a9b10
Revises: ae7c8693e402
Create Date: 2026-11-15 16:30:00.000000

Desde ahora una cuenta o un apartado solo puede estar en MXN, USD o EUR. Antes se aceptaba
cualquier texto de tres letras, así que aquí:

- se pasan a mayúsculas y sin espacios `accounts.currency` e `investment_positions.currency`;
- si después de eso queda alguna moneda fuera de la lista, la migración se detiene y dice
  cuáles son. No se adivina: hay que corregirlas a mano y volver a correrla.

No hay downgrade de datos: las mayúsculas no se pueden deshacer y no estorban.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c41d7e2a9b10"
down_revision: str | None = "ae7c8693e402"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SUPPORTED = ("MXN", "USD", "EUR")
TABLES = ("accounts", "investment_positions")


def upgrade() -> None:
    bind = op.get_bind()
    unsupported: list[str] = []
    for table in TABLES:
        bind.execute(sa.text(f"UPDATE {table} SET currency = UPPER(TRIM(currency))"))
        rows = bind.execute(
            sa.text(
                f"SELECT currency, COUNT(*) FROM {table} "
                "WHERE currency NOT IN :supported GROUP BY currency"
            ).bindparams(sa.bindparam("supported", expanding=True)),
            {"supported": list(SUPPORTED)},
        ).all()
        unsupported += [f"{table}: {currency!r} ({count})" for currency, count in rows]
    if unsupported:
        raise RuntimeError(
            "Hay monedas fuera de MXN, USD y EUR; corrígelas a mano y vuelve a correr la "
            "migración: " + "; ".join(unsupported)
        )


def downgrade() -> None:
    pass

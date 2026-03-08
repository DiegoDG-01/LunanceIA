"""seed_initial_banks_and_categories

Revision ID: b3f92a1d4e07
Revises: 070c7148a41c
Create Date: 2026-03-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b3f92a1d4e07"
down_revision: Union[str, None] = "070c7148a41c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


banks_table = sa.table(
    "banks",
    sa.column("name", sa.String),
    sa.column("code", sa.String),
    sa.column("country", sa.String),
    sa.column("logo_url", sa.String),
    sa.column("color", sa.String),
    sa.column("is_active", sa.Boolean),
)

categories_table = sa.table(
    "categories",
    sa.column("name", sa.String),
    sa.column("type", sa.String),
    sa.column("icon", sa.String),
    sa.column("color", sa.String),
    sa.column("description", sa.String),
    sa.column("is_active", sa.Boolean),
)

BANKS = [
    {"name": "BBVA México",     "code": "BBV", "country": "MX", "logo_url": "https://pub-359f496be1f4482bb564fd2b4c5e16d8.r2.dev/bbva.webp",          "color": "#004481", "is_active": True},
    {"name": "Santander",       "code": "SAN", "country": "MX", "logo_url": "https://pub-359f496be1f4482bb564fd2b4c5e16d8.r2.dev/santander.webp",      "color": "#EC0000", "is_active": True},
    {"name": "Banorte",         "code": "BNO", "country": "MX", "logo_url": "https://pub-359f496be1f4482bb564fd2b4c5e16d8.r2.dev/banorte.webp",        "color": "#CB0C2E", "is_active": True},
    {"name": "Citibanamex",     "code": "CIT", "country": "MX", "logo_url": "https://pub-359f496be1f4482bb564fd2b4c5e16d8.r2.dev/citibanamex.webp",    "color": "#1A4480", "is_active": True},
    {"name": "HSBC",            "code": "HSB", "country": "MX", "logo_url": "https://pub-359f496be1f4482bb564fd2b4c5e16d8.r2.dev/hsbc.png",            "color": "#DB0011", "is_active": True},
    {"name": "Scotiabank",      "code": "SCO", "country": "MX", "logo_url": "https://pub-359f496be1f4482bb564fd2b4c5e16d8.r2.dev/scotiabank.webp",     "color": "#EC111A", "is_active": True},
    {"name": "Banco Azteca",    "code": "AZT", "country": "MX", "logo_url": "https://pub-359f496be1f4482bb564fd2b4c5e16d8.r2.dev/banco_azteca.webp",   "color": "#00A650", "is_active": True},
    {"name": "Inbursa",         "code": "INB", "country": "MX", "logo_url": "https://pub-359f496be1f4482bb564fd2b4c5e16d8.r2.dev/inbursa.webp",        "color": "#003DA5", "is_active": True},
    {"name": "BanCoppel",       "code": "COP", "country": "MX", "logo_url": "https://pub-359f496be1f4482bb564fd2b4c5e16d8.r2.dev/bancoppel.webp",      "color": "#FFD100", "is_active": True},
    {"name": "Nu México",       "code": "NU",  "country": "MX", "logo_url": "https://pub-359f496be1f4482bb564fd2b4c5e16d8.r2.dev/nu.webp",             "color": "#820AD1", "is_active": True},
    {"name": "Rappi",           "code": "RAP", "country": "MX", "logo_url": "https://pub-359f496be1f4482bb564fd2b4c5e16d8.r2.dev/rappi.webp",          "color": "#FF5A00", "is_active": True},
    {"name": "Hey Banco",       "code": "HEY", "country": "MX", "logo_url": "https://pub-359f496be1f4482bb564fd2b4c5e16d8.r2.dev/hey.png",             "color": "#00D26A", "is_active": True},
    {"name": "Spin by OXXO",    "code": "SPN", "country": "MX", "logo_url": "https://pub-359f496be1f4482bb564fd2b4c5e16d8.r2.dev/spin.webp",           "color": "#D52B1E", "is_active": True},
    {"name": "Mercado Pago",    "code": "MPA", "country": "MX", "logo_url": "https://pub-359f496be1f4482bb564fd2b4c5e16d8.r2.dev/mp.webp",             "color": "#00B1EA", "is_active": True},
    {"name": "Stori",           "code": "STO", "country": "MX", "logo_url": "https://pub-359f496be1f4482bb564fd2b4c5e16d8.r2.dev/stori.webp",          "color": "#00BFFF", "is_active": True},
    {"name": "Revolut",         "code": "REV", "country": "MX", "logo_url": "https://pub-359f496be1f4482bb564fd2b4c5e16d8.r2.dev/revolut.webp",        "color": "#0075EB", "is_active": True},
    {"name": "Ualá",            "code": "UAL", "country": "MX", "logo_url": "https://pub-359f496be1f4482bb564fd2b4c5e16d8.r2.dev/uala.webp",           "color": "#3C14FA", "is_active": True},
    {"name": "Finsus",          "code": "FIN", "country": "MX", "logo_url": "https://pub-359f496be1f4482bb564fd2b4c5e16d8.r2.dev/finsus.png",          "color": "#00C389", "is_active": True},
    {"name": "Klar",            "code": "KLR", "country": "MX", "logo_url": "https://pub-359f496be1f4482bb564fd2b4c5e16d8.r2.dev/klar.png",            "color": "#00C389", "is_active": True},
    {"name": "GBM",             "code": "GBM", "country": "MX", "logo_url": "https://pub-359f496be1f4482bb564fd2b4c5e16d8.r2.dev/gbm.webp",            "color": "#00C389", "is_active": True},
    {"name": "American Expres", "code": "AMX", "country": "MX", "logo_url": "https://pub-359f496be1f4482bb564fd2b4c5e16d8.r2.dev/amex.webp",           "color": "#00C389", "is_active": True},
]

CATEGORIES = [
    {"name": "Comida",      "type": "EXPENSE", "icon": "🍔", "color": "#FF5733", "description": "Gastos relacionados con alimentos y bebidas.",        "is_active": True},
    {"name": "Transporte",  "type": "EXPENSE", "icon": "🚗", "color": "#33FF57", "description": "Gastos de movilidad: gasolina, bus, taxi.",           "is_active": True},
    {"name": "Sueldo",      "type": "INCOME",  "icon": "💰", "color": "#3357FF", "description": "Salario y otros ingresos principales.",               "is_active": True},
    {"name": "Inversiones", "type": "INCOME",  "icon": "📈", "color": "#FFFF33", "description": "Ganancias por inversiones o dividendos.",             "is_active": True},
    {"name": "Viajes",      "type": "EXPENSE", "icon": "✈️", "color": "#3357FF", "description": "Gastos generales",                                    "is_active": True},
]


def upgrade() -> None:
    conn = op.get_bind()

    existing_bank_codes = {
        row[0] for row in conn.execute(sa.text("SELECT code FROM banks"))
    }
    new_banks = [b for b in BANKS if b["code"] not in existing_bank_codes]
    if new_banks:
        op.bulk_insert(banks_table, new_banks)

    existing_category_names = {
        row[0] for row in conn.execute(sa.text("SELECT name FROM categories"))
    }
    new_categories = [c for c in CATEGORIES if c["name"] not in existing_category_names]
    if new_categories:
        op.bulk_insert(categories_table, new_categories)


def downgrade() -> None:
    bank_names = [b["name"] for b in BANKS]
    category_names = [c["name"] for c in CATEGORIES]

    op.execute(
        sa.text("DELETE FROM banks WHERE name IN :names").bindparams(
            sa.bindparam("names", expanding=True)
        ),
        {"names": bank_names},
    )
    op.execute(
        sa.text("DELETE FROM categories WHERE name IN :names").bindparams(
            sa.bindparam("names", expanding=True)
        ),
        {"names": category_names},
    )
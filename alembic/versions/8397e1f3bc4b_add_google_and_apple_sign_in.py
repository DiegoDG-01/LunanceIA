"""google and apple sign in: provider subjects and the encrypted apple refresh token

Revision ID: 8397e1f3bc4b
Revises: 64410d772dfd
Create Date: 2026-11-10 23:00:00.000000

Columnas nuevas en `users`:
- `google_sub`, `apple_sub`: claim `sub` del ID token de cada proveedor. Únicas (NULL se
  repite sin problema en MySQL) y con collation binaria: el identificador distingue
  mayúsculas.
- `apple_refresh_token`: refresh token de Sign in with Apple cifrado con AES-GCM
  (`APPLE_TOKEN_ENCRYPTION_KEY`). Solo sirve para revocar la autorización al borrar la cuenta.

`users.password` ya aceptaba NULL: las cuentas creadas con Google o Apple no tienen contraseña
hasta que eligen una con "Olvidé mi contraseña".

Bajar esta migración pierde los vínculos: las cuentas sin contraseña solo podrán entrar
después de restablecerla por correo.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import mysql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8397e1f3bc4b"
down_revision: str | None = "64410d772dfd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _subject() -> sa.types.TypeEngine:
    return sa.String(length=255).with_variant(
        mysql.VARCHAR(length=255, charset="utf8mb4", collation="utf8mb4_bin"), "mysql"
    )


def upgrade() -> None:
    op.add_column("users", sa.Column("google_sub", _subject(), nullable=True))
    op.add_column("users", sa.Column("apple_sub", _subject(), nullable=True))
    op.add_column(
        "users",
        sa.Column("apple_refresh_token", sa.String(length=1024), nullable=True),
    )
    op.create_index(op.f("ix_users_google_sub"), "users", ["google_sub"], unique=True)
    op.create_index(op.f("ix_users_apple_sub"), "users", ["apple_sub"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_users_apple_sub"), table_name="users")
    op.drop_index(op.f("ix_users_google_sub"), table_name="users")
    op.drop_column("users", "apple_refresh_token")
    op.drop_column("users", "apple_sub")
    op.drop_column("users", "google_sub")

"""email login: required users.email, pending signups and password reset tokens

Revision ID: 64410d772dfd
Revises: e7f4a1c9d203
Create Date: 2026-11-10 21:00:00.000000

El login pasa a ser por correo: `users.email` deja de aceptar NULL y se guarda normalizado
(sin espacios y en minúsculas). No hay usuarios reales, así que no hay periodo de transición:
los usuarios de desarrollo sin correo reciben uno de relleno (`user-<id>@sin-correo.invalid`,
dominio reservado que nunca recibe correo) y para entrar hay que cambiarlo a mano en la base.

Tablas nuevas:
- `pending_signups`: registros con correo a la espera de confirmar (la cuenta se crea al abrir
  el enlace). Solo el hash de la contraseña.
- `email_verification_tokens`: SHA-256 de cada enlace de verificación enviado.
- `password_reset_tokens`: SHA-256 de cada enlace de "Olvidé mi contraseña", de un solo uso.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import mysql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "64410d772dfd"
down_revision: str | None = "e7f4a1c9d203"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PLACEHOLDER_DOMAIN = "sin-correo.invalid"


def upgrade() -> None:
    op.execute(
        "UPDATE users SET email = LOWER(TRIM(email)) "
        "WHERE email IS NOT NULL AND TRIM(email) <> ''"
    )
    op.execute(
        "UPDATE users SET email = CONCAT('user-', id, '@"
        + PLACEHOLDER_DOMAIN
        + "') WHERE email IS NULL OR TRIM(email) = ''"
    )
    op.alter_column(
        "users",
        "email",
        existing_type=mysql.VARCHAR(length=100),
        type_=sa.String(length=255),
        nullable=False,
    )

    op.create_table(
        "pending_signups",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_pending_signups_email"), "pending_signups", ["email"], unique=True
    )
    op.create_index(
        op.f("ix_pending_signups_username"),
        "pending_signups",
        ["username"],
        unique=True,
    )
    op.create_index(
        "ix_pending_signups_expires_at",
        "pending_signups",
        ["expires_at"],
        unique=False,
    )

    op.create_table(
        "email_verification_tokens",
        sa.Column("token_hash", sa.CHAR(length=64), nullable=False),
        sa.Column("pending_signup_id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["pending_signup_id"], ["pending_signups.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("token_hash"),
    )
    op.create_index(
        "ix_email_verification_tokens_signup",
        "email_verification_tokens",
        ["pending_signup_id"],
        unique=False,
    )

    op.create_table(
        "password_reset_tokens",
        sa.Column("token_hash", sa.CHAR(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("token_hash"),
    )
    op.create_index(
        "ix_password_reset_tokens_user_used",
        "password_reset_tokens",
        ["user_id", "used_at"],
        unique=False,
    )
    op.create_index(
        "ix_password_reset_tokens_expires_at",
        "password_reset_tokens",
        ["expires_at"],
        unique=False,
    )


def downgrade() -> None:
    # Borrar la tabla borra sus índices; MySQL no deja quitar antes los que usa una FK.
    op.drop_table("password_reset_tokens")
    op.drop_table("email_verification_tokens")
    op.drop_index(op.f("ix_pending_signups_username"), table_name="pending_signups")
    op.drop_index(op.f("ix_pending_signups_email"), table_name="pending_signups")
    op.drop_index("ix_pending_signups_expires_at", table_name="pending_signups")
    op.drop_table("pending_signups")

    # Primero se vuelve a aceptar NULL; luego se quitan los correos de relleno y los que no
    # caben en la columna anterior (más de 100 caracteres), y al final se acorta.
    op.alter_column(
        "users",
        "email",
        existing_type=sa.String(length=255),
        nullable=True,
    )
    op.execute(
        "UPDATE users SET email = NULL WHERE email LIKE '%@" + PLACEHOLDER_DOMAIN + "'"
    )
    op.execute("UPDATE users SET email = NULL WHERE CHAR_LENGTH(email) > 100")
    op.alter_column(
        "users",
        "email",
        existing_type=sa.String(length=255),
        type_=mysql.VARCHAR(length=100),
        existing_nullable=True,
    )

"""add multi-device sessions, opaque refresh tokens and auth events

Revision ID: c3a91f7e2b10
Revises: 8d2f1b6a3c49
Create Date: 2026-11-10 00:00:00.000000

No hay usuarios reales: `refresh_tokens` se borra y se recrea sin migrar datos (todos vuelven a
iniciar sesión una vez). Se elimina `users.auth0_id`: Auth0 nunca llegó a producción.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import mysql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3a91f7e2b10"
down_revision: str | None = "8d2f1b6a3c49"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index(op.f("ix_refresh_tokens_id"), table_name="refresh_tokens")
    op.drop_table("refresh_tokens")

    op.create_table(
        "user_sessions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("uuid", sa.CHAR(length=36), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.CHAR(length=36), nullable=False),
        sa.Column(
            "platform",
            sa.Enum("web", "ios", "android", name="session_platform"),
            nullable=False,
        ),
        sa.Column("device_name", sa.String(length=100), nullable=True),
        sa.Column("client", sa.String(length=50), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("created_ip", sa.String(length=45), nullable=True),
        sa.Column("last_ip", sa.String(length=45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("idle_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("absolute_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_reason", sa.String(length=30), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_user_sessions_uuid"), "user_sessions", ["uuid"], unique=True
    )
    op.create_index(
        "ix_user_sessions_user_revoked",
        "user_sessions",
        ["user_id", "revoked_at"],
        unique=False,
    )
    op.create_index(
        "ix_user_sessions_user_device",
        "user_sessions",
        ["user_id", "device_id"],
        unique=False,
    )

    op.create_table(
        "refresh_tokens",
        sa.Column("token_hash", sa.CHAR(length=64), nullable=False),
        sa.Column("session_id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rotated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["session_id"], ["user_sessions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("token_hash"),
    )
    op.create_index(
        "ix_refresh_tokens_session_id",
        "refresh_tokens",
        ["session_id"],
        unique=False,
    )

    op.create_table(
        "auth_events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("session_id", sa.BigInteger(), nullable=True),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("ip", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_auth_events_user_created",
        "auth_events",
        ["user_id", "created_at"],
        unique=False,
    )

    op.drop_index(op.f("ix_users_auth0_id"), table_name="users")
    op.drop_column("users", "auth0_id")


def downgrade() -> None:
    op.add_column(
        "users",
        sa.Column("auth0_id", mysql.VARCHAR(length=255), nullable=True),
    )
    op.create_index(op.f("ix_users_auth0_id"), "users", ["auth0_id"], unique=True)

    # Borrar la tabla borra sus índices; MySQL no deja quitar antes los que usa una FK.
    op.drop_table("auth_events")
    op.drop_table("refresh_tokens")
    op.drop_table("user_sessions")

    # La tabla anterior, vacía: los refresh JWT ya no se pueden reconstruir.
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", mysql.VARCHAR(length=255), nullable=False),
        sa.Column("is_revoked", sa.Boolean(), nullable=False),
        sa.Column("expired_at", sa.DateTime(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_refresh_tokens_id"), "refresh_tokens", ["id"], unique=False
    )

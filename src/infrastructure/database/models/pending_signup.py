from datetime import datetime

from sqlalchemy import CHAR, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.connection import Base
from infrastructure.database.types import BigIntId


class PendingSignupModel(Base):
    """Registro con correo a la espera de confirmarse. La fila de `users` se crea al abrir el
    enlace; hasta entonces solo existe esto, con el hash de la contraseña elegida.

    Correo y username son únicos aquí también: un registro abierto reserva el username. Un
    registro caducado deja de reservarlo (se borra antes de insertar otro que choque).
    """

    __tablename__ = "pending_signups"
    __table_args__ = (Index("ix_pending_signups_expires_at", "expires_at"),)

    id: Mapped[int] = mapped_column(BigIntId, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class EmailVerificationTokenModel(Base):
    """Cada enlace enviado para un registro. Solo el SHA-256 del token."""

    __tablename__ = "email_verification_tokens"
    __table_args__ = (
        Index("ix_email_verification_tokens_signup", "pending_signup_id"),
    )

    token_hash: Mapped[str] = mapped_column(CHAR(64), primary_key=True)
    pending_signup_id: Mapped[int] = mapped_column(
        BigIntId, ForeignKey("pending_signups.id", ondelete="CASCADE")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

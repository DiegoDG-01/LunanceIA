from datetime import datetime

from sqlalchemy import CHAR, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.connection import Base


class PasswordResetTokenModel(Base):
    """Enlaces de "Olvidé mi contraseña". Solo el SHA-256 del token; `used_at` lo gasta."""

    __tablename__ = "password_reset_tokens"
    __table_args__ = (
        Index("ix_password_reset_tokens_user_used", "user_id", "used_at"),
        Index("ix_password_reset_tokens_expires_at", "expires_at"),
    )

    token_hash: Mapped[str] = mapped_column(CHAR(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

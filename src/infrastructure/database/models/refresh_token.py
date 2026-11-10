from datetime import datetime

from sqlalchemy import CHAR, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.connection import Base
from infrastructure.database.types import BigIntId


class RefreshTokenModel(Base):
    """Solo el SHA-256 del token opaco: una fuga de la tabla no expone sesiones vivas."""

    __tablename__ = "refresh_tokens"
    __table_args__ = (Index("ix_refresh_tokens_session_id", "session_id"),)

    token_hash: Mapped[str] = mapped_column(CHAR(64), primary_key=True)
    session_id: Mapped[int] = mapped_column(
        BigIntId, ForeignKey("user_sessions.id", ondelete="CASCADE")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    rotated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

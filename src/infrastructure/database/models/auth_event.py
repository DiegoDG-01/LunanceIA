from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.connection import Base
from infrastructure.database.types import BigIntId


class AuthEventModel(Base):
    """Auditoría de inicios de sesión y sesiones. Sin FKs: sobrevive a la purga de sesiones."""

    __tablename__ = "auth_events"
    __table_args__ = (Index("ix_auth_events_user_created", "user_id", "created_at"),)

    id: Mapped[int] = mapped_column(BigIntId, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(nullable=True)
    session_id: Mapped[int | None] = mapped_column(BigIntId, nullable=True)
    action: Mapped[str] = mapped_column(String(50))
    ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    details: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

import uuid
from datetime import datetime

from sqlalchemy import CHAR, DateTime, Enum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from domain.entities.auth.session import Platform
from infrastructure.database.connection import Base
from infrastructure.database.types import BigIntId


class UserSessionModel(Base):
    __tablename__ = "user_sessions"
    __table_args__ = (
        Index("ix_user_sessions_user_revoked", "user_id", "revoked_at"),
        Index("ix_user_sessions_user_device", "user_id", "device_id"),
    )

    id: Mapped[int] = mapped_column(BigIntId, primary_key=True, autoincrement=True)
    uuid: Mapped[str] = mapped_column(
        CHAR(36), unique=True, index=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    device_id: Mapped[str] = mapped_column(CHAR(36))
    platform: Mapped[Platform] = mapped_column(
        Enum(
            Platform,
            name="session_platform",
            values_callable=lambda enum: [member.value for member in enum],
        )
    )
    device_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    client: Mapped[str | None] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    last_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    idle_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    absolute_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_reason: Mapped[str | None] = mapped_column(String(30), nullable=True)

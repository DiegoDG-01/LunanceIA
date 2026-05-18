from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, Enum, Text
from datetime import timezone
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.connection import Base
from domain.objects.enums import NotificationType


class NotificationModel(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(100), nullable=True)
    message: Mapped[str] = mapped_column(Text)
    type: Mapped[NotificationType] = mapped_column(Enum(NotificationType))
    is_read: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),  # TIMESTAMP WITH TIME ZONE
        default=lambda: datetime.now(timezone.utc),
        index=True
    )

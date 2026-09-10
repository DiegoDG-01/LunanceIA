from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from domain.objects.enums import ReminderType
from infrastructure.database.connection import Base


class ReminderModel(Base):
    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    reminder_date: Mapped[date] = mapped_column(Date, index=True)
    type: Mapped[ReminderType] = mapped_column(
        Enum(ReminderType), default=ReminderType.OTRO
    )
    is_completed: Mapped[bool] = mapped_column(default=False, index=True)
    creation_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

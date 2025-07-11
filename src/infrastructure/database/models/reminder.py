from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Enum,
    Text,
    Date,
)
from sqlalchemy.sql import func

from infrastructure.database.connection import Base
from domain.objects.enums import ReminderType


class ReminderModel(Base):
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title = Column(String(100), nullable=False)
    description = Column(Text)
    reminder_date = Column(Date, nullable=False, index=True)
    type = Column(Enum(ReminderType), default=ReminderType.OTRO)
    is_completed = Column(Boolean, default=False, index=True)
    creation_date = Column(DateTime(timezone=True), server_default=func.now())

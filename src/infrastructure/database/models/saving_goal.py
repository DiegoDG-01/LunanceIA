import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CHAR, DECIMAL, Date, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from infrastructure.database.connection import Base


class SavingGoalModel(Base):
    __tablename__ = "saving_goals"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id"),
    )
    uuid: Mapped[str] = mapped_column(
        CHAR(36), unique=True, index=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(100))
    target_amount: Mapped[Decimal] = mapped_column(DECIMAL(12, 2))
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, index=True)
    creation_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completion_date: Mapped[date | None] = mapped_column(Date, nullable=True)

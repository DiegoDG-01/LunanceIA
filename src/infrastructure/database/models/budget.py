import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import String, DateTime, ForeignKey, Enum, DECIMAL, Date, CHAR
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.connection import Base
from domain.objects.enums import BudgetPeriod


class BudgetModel(Base):
    __tablename__ = "budgets"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    category_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("categories.id"), nullable=True
    )
    uuid: Mapped[str] = mapped_column(
        CHAR(36), unique=True, index=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(100))
    limit_amount: Mapped[Decimal] = mapped_column(DECIMAL(12, 2))
    period: Mapped[BudgetPeriod] = mapped_column(Enum(BudgetPeriod))
    start_date: Mapped[date] = mapped_column(Date, index=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, index=True, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, index=True)
    alert_percentage: Mapped[int] = mapped_column(default=80)
    creation_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

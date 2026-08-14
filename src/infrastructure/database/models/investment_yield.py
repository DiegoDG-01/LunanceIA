import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    ForeignKey,
    DECIMAL,
    Date,
    DateTime,
    Enum,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.connection import Base
from domain.objects.enums import InterestType


class InvestmentYieldModel(Base):
    __tablename__ = "investment_yields"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), index=True
    )
    position_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("investment_positions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    uuid: Mapped[str] = mapped_column(
        CHAR(36), unique=True, index=True, default=lambda: str(uuid.uuid4())
    )
    yield_date: Mapped[date] = mapped_column(Date)
    principal_amount: Mapped[Decimal] = mapped_column(DECIMAL(12, 2))
    yield_amount: Mapped[Decimal] = mapped_column(DECIMAL(12, 2))
    cumulative_balance: Mapped[Decimal] = mapped_column(DECIMAL(12, 2))
    annual_rate: Mapped[Decimal] = mapped_column(DECIMAL(5, 2))
    interest_type: Mapped[InterestType] = mapped_column(Enum(InterestType))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("position_id", "yield_date", name="uq_position__yield_date"),
        Index("idx_yield_date", "yield_date"),
    )

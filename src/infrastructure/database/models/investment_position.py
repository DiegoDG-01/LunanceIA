import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import DECIMAL, Date, DateTime, Enum, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from domain.objects.enums import (
    InterestType,
    MaturityAction,
    OverflowAction,
    PositionStatus,
    PositionType,
)
from infrastructure.database.connection import Base


class InvestmentPositionModel(Base):
    __tablename__ = "investment_positions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), index=True
    )
    uuid: Mapped[str] = mapped_column(
        CHAR(36), unique=True, index=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(100))
    position_type: Mapped[PositionType] = mapped_column(Enum(PositionType))
    status: Mapped[PositionStatus] = mapped_column(
        Enum(PositionStatus), default=PositionStatus.ACTIVE
    )
    balance: Mapped[Decimal] = mapped_column(DECIMAL(15, 2), default=0.00)
    accrued_yield: Mapped[Decimal] = mapped_column(DECIMAL(15, 2), default=0.00)
    currency: Mapped[str] = mapped_column(String(3), default="MXN")
    annual_rate: Mapped[Decimal] = mapped_column(DECIMAL(5, 2))
    interest_type: Mapped[InterestType] = mapped_column(
        Enum(InterestType), default=InterestType.COMPOUND
    )
    base_principal: Mapped[Decimal | None] = mapped_column(
        DECIMAL(15, 2), nullable=True
    )
    start_date: Mapped[date] = mapped_column(Date)
    term_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lock_period_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    maturity_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    early_withdrawal_penalty: Mapped[Decimal | None] = mapped_column(
        DECIMAL(5, 2), nullable=True
    )
    on_maturity: Mapped[MaturityAction] = mapped_column(
        Enum(MaturityAction), default=MaturityAction.HOLD
    )
    max_balance: Mapped[Decimal | None] = mapped_column(DECIMAL(15, 2), nullable=True)
    overflow_action: Mapped[OverflowAction | None] = mapped_column(
        Enum(OverflowAction), nullable=True
    )
    # SET NULL y no CASCADE: que desaparezca el destino nunca debe borrar al
    # apartado que lo apuntaba. La cadena rota se resuelve cayendo al disponible.
    overflow_position_id: Mapped[int | None] = mapped_column(
        ForeignKey("investment_positions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("idx_positions_status", "status"),
        Index("idx_positions_maturity_date", "maturity_date"),
    )

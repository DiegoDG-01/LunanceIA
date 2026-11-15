"""Operaciones sobre valores (compras, ventas, dividendos, splits) y las tenencias que se
calculan de ellas."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    DECIMAL,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from domain.objects.enums import HoldingStatus, TradeType
from infrastructure.database.connection import Base


class SecurityTradeModel(Base):
    __tablename__ = "security_trades"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    uuid: Mapped[str] = mapped_column(
        CHAR(36), unique=True, index=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE")
    )
    instrument_id: Mapped[int] = mapped_column(
        ForeignKey("instruments.id", ondelete="RESTRICT")
    )
    trade_type: Mapped[TradeType] = mapped_column(Enum(TradeType))
    trade_date: Mapped[date] = mapped_column(Date)
    quantity: Mapped[Decimal] = mapped_column(DECIMAL(24, 8))
    price: Mapped[Decimal] = mapped_column(DECIMAL(20, 6))
    fees: Mapped[Decimal] = mapped_column(DECIMAL(15, 2))
    tax_withheld: Mapped[Decimal] = mapped_column(DECIMAL(15, 2))
    gross_amount: Mapped[Decimal | None] = mapped_column(DECIMAL(15, 2), nullable=True)
    cash_amount: Mapped[Decimal] = mapped_column(DECIMAL(15, 2))
    split_from: Mapped[int | None] = mapped_column(Integer, nullable=True)
    split_to: Mapped[int | None] = mapped_column(Integer, nullable=True)
    transaction_id: Mapped[int | None] = mapped_column(
        ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True, unique=True
    )
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index(
            "idx_security_trade_account_instrument_date",
            "account_id",
            "instrument_id",
            "trade_date",
        ),
    )


class SecurityHoldingModel(Base):
    __tablename__ = "security_holdings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    uuid: Mapped[str] = mapped_column(
        CHAR(36), unique=True, index=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE")
    )
    instrument_id: Mapped[int] = mapped_column(
        ForeignKey("instruments.id", ondelete="RESTRICT"), index=True
    )
    quantity: Mapped[Decimal] = mapped_column(DECIMAL(24, 8))
    avg_cost: Mapped[Decimal] = mapped_column(DECIMAL(20, 6))
    cost_basis: Mapped[Decimal] = mapped_column(DECIMAL(15, 2))
    realized_pnl: Mapped[Decimal] = mapped_column(DECIMAL(15, 2))
    dividends: Mapped[Decimal] = mapped_column(DECIMAL(15, 2))
    status: Mapped[HoldingStatus] = mapped_column(Enum(HoldingStatus))
    opened_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    closed_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "account_id", "instrument_id", name="uq_holding_account_instrument"
        ),
    )

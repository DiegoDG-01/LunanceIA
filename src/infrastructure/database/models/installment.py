import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    DECIMAL,
    Integer,
    Text,
    CHAR
)
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.connection import Base
from domain.objects.enums import InstallmentType


class InstallmentPurchaseModel(Base):
    __tablename__ = "installment_purchases"

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
    category_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("categories.id"), nullable=True
    )
    description: Mapped[str] = mapped_column(Text)
    total_amount: Mapped[Decimal] = mapped_column(DECIMAL(12, 2))
    num_installments: Mapped[int] = mapped_column(Integer)
    installment_type: Mapped[InstallmentType] = mapped_column(Enum(InstallmentType))
    annual_interest_rate: Mapped[Decimal] = mapped_column(DECIMAL(5, 2))
    monthly_payment: Mapped[Decimal] = mapped_column(DECIMAL(12, 2))
    purchase_date: Mapped[date] = mapped_column(Date)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    creation_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class InstallmentChargeModel(Base):
    __tablename__ = "installment_charges"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    uuid: Mapped[str] = mapped_column(
        CHAR(36), unique=True, index=True, default=lambda: str(uuid.uuid4())
    )
    installment_purchase_id: Mapped[int] = mapped_column(
        ForeignKey("installment_purchases.id", ondelete="CASCADE"), index=True
    )
    transaction_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True
    )
    installment_number: Mapped[int] = mapped_column(Integer)
    amount: Mapped[Decimal] = mapped_column(DECIMAL(12, 2))
    due_date: Mapped[date] = mapped_column(Date, index=True)
    paid: Mapped[bool] = mapped_column(Boolean, default=False)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    creation_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )




















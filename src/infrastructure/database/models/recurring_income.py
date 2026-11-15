import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CHAR,
    DECIMAL,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    select,
)
from sqlalchemy.orm import Mapped, column_property, mapped_column
from sqlalchemy.sql import func

from domain.objects.enums import Frequency, TransactionStatus
from infrastructure.database.connection import Base
from infrastructure.database.models.account import AccountModel, account_currency


class RecurringIncomeModel(Base):
    __tablename__ = "recurring_incomes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    currency: Mapped[str] = account_currency(account_id)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    uuid: Mapped[str] = mapped_column(
        CHAR(36), unique=True, index=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(100))
    amount: Mapped[Decimal] = mapped_column(DECIMAL(12, 2))
    frequency: Mapped[Frequency] = mapped_column(Enum(Frequency))
    start_date: Mapped[date] = mapped_column(Date, index=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    creation_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    next_payment_date: Mapped[date] = mapped_column(Date, index=True)


class IncomeDepositModel(Base):
    __tablename__ = "income_deposits"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    recurring_income_id: Mapped[int] = mapped_column(
        ForeignKey("recurring_incomes.id", ondelete="CASCADE"), index=True
    )
    # La moneda de la cuenta del ingreso recurrente.
    currency: Mapped[str] = column_property(
        select(AccountModel.currency)
        .join(RecurringIncomeModel, RecurringIncomeModel.account_id == AccountModel.id)
        .where(RecurringIncomeModel.id == recurring_income_id)
        .correlate_except(AccountModel, RecurringIncomeModel)
        .scalar_subquery(),
        expire_on_flush=False,
    )
    uuid: Mapped[str] = mapped_column(
        CHAR(36), unique=True, index=True, default=lambda: str(uuid.uuid4())
    )
    transaction_id: Mapped[int | None] = mapped_column(
        ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True
    )
    deposit_date: Mapped[date] = mapped_column(Date, index=True)
    amount: Mapped[Decimal] = mapped_column(DECIMAL(12, 2))
    status: Mapped[TransactionStatus] = mapped_column(
        Enum(TransactionStatus), default=TransactionStatus.PENDIENTE, index=True
    )
    processing_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        UniqueConstraint(
            "recurring_income_id", "deposit_date", name="uq_income_deposit_date"
        ),
    )

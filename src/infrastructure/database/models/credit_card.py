import uuid
from decimal import Decimal

from sqlalchemy import DECIMAL, ForeignKey, Index
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.connection import Base


class CreditCardSettingsModel(Base):
    __tablename__ = "credit_card_settings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), unique=True, index=True
    )
    uuid: Mapped[str] = mapped_column(
        CHAR(36), unique=True, index=True, default=lambda: str(uuid.uuid4())
    )

    # Billing cycle fields
    billing_cycle_day: Mapped[int] = mapped_column()
    payment_due_day: Mapped[int] = mapped_column()
    credit_limit: Mapped[Decimal] = mapped_column(DECIMAL(12, 2))
    minimum_payment_percentage: Mapped[Decimal] = mapped_column(
        DECIMAL(5, 2), default=5.0
    )

    # Indexes for reminder queries
    __table_args__ = (
        Index("idx_billing_cycle_day", "billing_cycle_day"),
        Index("idx_payment_due_day", "payment_due_day"),
    )

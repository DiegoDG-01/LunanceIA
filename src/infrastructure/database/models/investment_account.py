import uuid
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import ForeignKey, DECIMAL, Date, String, Index, Enum
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.connection import Base
from domain.objects.enums import InterestType


class InvestmentCardSettingsModel(Base):
    __tablename__ = "investment_card_settings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), unique=True, index=True
    )
    uuid: Mapped[str] = mapped_column(
        CHAR(36), unique=True, index=True, default=lambda: str(uuid.uuid4())
    )

    investment_type: Mapped[str] = mapped_column(String(50))
    investment_rate: Mapped[Decimal] = mapped_column(DECIMAL(5, 2))
    interest_type: Mapped[InterestType] = mapped_column(
        Enum(InterestType), default=InterestType.COMPOUND
    )
    lock_period_end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    maturity_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    early_withdrawal_penalty: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(5, 2), nullable=True
    )
    base_principal: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(15, 2), nullable=True
    )

    __table_args__ = (
        Index("idx_lock_period_end_date", "lock_period_end_date"),
        Index("idx_maturity_date", "maturity_date"),
    )

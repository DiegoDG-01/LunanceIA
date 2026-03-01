from sqlalchemy import Column, Integer, ForeignKey, DECIMAL, Index
from sqlalchemy.dialects.mysql import CHAR
from infrastructure.database.connection import Base

import uuid


class CreditCardSettingsModel(Base):
    __tablename__ = "credit_card_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(
        Integer,
        ForeignKey("accounts.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    uuid = Column(
        CHAR(36),
        unique=True,
        index=True,
        default=lambda: str(uuid.uuid4()),
        nullable=False,
    )

    # Billing cicles fields
    billing_cycle_day = Column(Integer, nullable=False)
    payment_due_day = Column(Integer, nullable=False)
    credit_limit = Column(DECIMAL(12, 2), nullable=False)
    minimum_payment_percentage = Column(DECIMAL(5, 2), nullable=False, default=5.0)

    # Indexes for reminder queries
    __table_args__ = (
        Index("idx_billing_cycle_day", "billing_cycle_day"),
        Index("idx_payment_due_day", "payment_due_day"),
    )

from sqlalchemy import Column, Integer, ForeignKey, DECIMAL, Date, String, Index
from sqlalchemy.dialects.mysql import CHAR
from infrastructure.database.connection import Base

import uuid


class InvestmentCardSettingsModel(Base):
    __tablename__ = "investment_card_settings"

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

    investment_type = Column(String(50), nullable=False)
    investment_rate = Column(DECIMAL(5, 2), nullable=False)
    lock_period_end_date = Column(Date, nullable=False)
    maturity_date = Column(Date, nullable=True)
    early_withdrawal_penalty = Column(DECIMAL(5, 2), nullable=True)

    __table_args__ = (
        Index("idx_lock_period_end_date", "lock_period_end_date"),
        Index("idx_maturity_date", "maturity_date"),
    )

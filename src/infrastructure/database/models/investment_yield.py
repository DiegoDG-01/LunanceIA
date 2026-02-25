import uuid
from sqlalchemy import (
    Column,
    Integer,
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

from infrastructure.database.connection import Base
from domain.objects.enums import InterestType


class InvestmentYieldModel(Base):
    __tablename__ = "investment_yields"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(
        Integer,
        ForeignKey("accounts.id", ondelete="CASCADE"),
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
    yield_date = Column(Date, nullable=False)
    principal_amount = Column(DECIMAL(12, 2), nullable=False)
    yield_amount = Column(DECIMAL(12, 2), nullable=False)
    cumulative_balance = Column(DECIMAL(12, 2), nullable=False)
    annual_rate = Column(DECIMAL(5, 2), nullable=False)
    interest_type = Column(Enum(InterestType), nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("account_id", "yield_date", name="uq_account__yield_date"),
        Index("idx_yield_date", "yield_date"),
    )

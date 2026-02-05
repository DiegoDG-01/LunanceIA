from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Enum,
    DECIMAL,
    Text,
    Date,
    CHAR,
)
from sqlalchemy.sql import func
import uuid

from infrastructure.database.connection import Base
from domain.objects.enums import Frequency, TransactionStatus


class SubscriptionModel(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    uuid = Column(
        CHAR(36),
        unique=True,
        index=True,
        default=lambda: str(uuid.uuid4()),
        nullable=False,
    )
    name = Column(String(100), nullable=False)
    amount = Column(DECIMAL(12, 2), nullable=False)
    frequency = Column(Enum(Frequency), nullable=False)
    start_date = Column(Date, nullable=False, index=True)
    end_date = Column(Date)
    billing_day = Column(Integer)
    is_active = Column(Boolean, default=True, index=True)
    description = Column(Text)
    service_url = Column(String(255))
    creation_date = Column(DateTime(timezone=True), server_default=func.now())


class SubscriptionChargeModel(Base):
    __tablename__ = "subscription_charges"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    subscription_id = Column(
        Integer,
        ForeignKey("subscriptions.id", ondelete="CASCADE"),
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
    transaction_id = Column(Integer, ForeignKey("transactions.id", ondelete="SET NULL"))
    charge_date = Column(Date, nullable=False, index=True)
    amount = Column(DECIMAL(12, 2), nullable=False)
    status = Column(
        Enum(TransactionStatus), default=TransactionStatus.PENDIENTE, index=True
    )
    processing_date = Column(DateTime(timezone=True))

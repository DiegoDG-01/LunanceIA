from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum, DECIMAL, Text, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base
from utils.enums import Frequency, TransactionStatus


class Subscription(Base):
    __tablename__ = "subscriptions"

    subscription_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    account_id = Column(Integer, ForeignKey("accounts.account_id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.category_id"), nullable=False)
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

    # Relaciones
    user = relationship("User", back_populates="subscriptions")
    account = relationship("Account", back_populates="subscriptions")
    category = relationship("Category", back_populates="subscriptions")
    subscription_charges = relationship("SubscriptionCharge", back_populates="subscription", cascade="all, delete-orphan")


class SubscriptionCharge(Base):
    __tablename__ = "subscription_charges"

    charge_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    subscription_id = Column(Integer, ForeignKey("subscriptions.subscription_id", ondelete="CASCADE"), nullable=False,
                            index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.transaction_id"))
    charge_date = Column(Date, nullable=False, index=True)
    amount = Column(DECIMAL(12, 2), nullable=False)
    status = Column(Enum(TransactionStatus), default=TransactionStatus.PENDIENTE, index=True)
    processing_date = Column(DateTime(timezone=True))

    # Relaciones
    subscription = relationship("Subscription", back_populates="subscription_charges")
    transactions = relationship("Transaction", back_populates="subscription_charge", uselist=False)
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum, DECIMAL
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base
from utils.enums import AccountType


class Account(Base):
    __tablename__ = "accounts"

    account_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    type = Column(Enum(AccountType), nullable=False)
    bank = Column(String(100))
    current_balance = Column(DECIMAL(12, 2), default=0.00)
    currency = Column(String(3), default="MXN")
    is_active = Column(Boolean, default=True)
    creation_date = Column(DateTime(timezone=True), server_default=func.now())

    # Relaciones
    user = relationship("User", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="account")
    subscriptions = relationship("Subscription", back_populates="account")
    saving_goals = relationship("SavingGoal", back_populates="account")
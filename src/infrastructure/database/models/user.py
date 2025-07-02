from sqlalchemy import CHAR,Column, Integer, String, DateTime, Boolean, func
from sqlalchemy.orm import relationship
import uuid

from infrastructure.database.connection import Base


class UserModel(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    uuid = Column(CHAR(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    registration_date = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)

    # Relaciones - Temporalmente comentadas hasta migrar todos los modelos
    # accounts = relationship("AccountModel", back_populates="user", cascade="all, delete-orphan")
    # transactions = relationship("TransactionModel", back_populates="user", cascade="all, delete-orphan")
    # subscriptions = relationship("SubscriptionModel", back_populates="user", cascade="all, delete-orphan")
    # budgets = relationship("BudgetModel", back_populates="user", cascade="all, delete-orphan")
    # saving_goals = relationship("SavingGoalModel", back_populates="user", cascade="all, delete-orphan")
    # tags = relationship("TagModel", back_populates="user", cascade="all, delete-orphan")
    # reminders = relationship("ReminderModel", back_populates="user", cascade="all, delete-orphan")
    # refresh_tokens = relationship("RefreshTokenModel", back_populates="user", cascade="all, delete-orphan")

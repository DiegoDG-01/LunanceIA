from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Enum,
    DECIMAL,
)
from sqlalchemy.sql import func

from infrastructure.database.connection import Base
from domain.objects.enums import AccountType


class AccountModel(Base):
    __tablename__ = "accounts"

    account_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_uuid = Column(
        String(36),
        ForeignKey("users.uuid", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(100), nullable=False)
    type = Column(Enum(AccountType), nullable=False)
    bank = Column(String(100))
    current_balance = Column(DECIMAL(12, 2), default=0.00)
    currency = Column(String(3), default="MXN")
    is_active = Column(Boolean, default=True)
    creation_date = Column(DateTime(timezone=True), server_default=func.now())

    # Relaciones - Temporalmente comentadas hasta migrar todos los modelos
    # user = relationship("UserModel", back_populates="accounts")
    # transactions = relationship("TransactionModel", back_populates="account", cascade="all,delete")
    # subscriptions = relationship("SubscriptionModel", back_populates="account")
    # saving_goals = relationship("SavingGoalModel", back_populates="account")

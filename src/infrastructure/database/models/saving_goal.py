from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, DECIMAL, Text, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from infrastructure.database.connection import Base


class SavingGoalModel(Base):
    __tablename__ = "saving_goals"

    goal_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    account_id = Column(Integer, ForeignKey("accounts.account_id"))
    name = Column(String(100), nullable=False)
    target_amount = Column(DECIMAL(12, 2), nullable=False)
    current_amount = Column(DECIMAL(12, 2), default=0.00)
    target_date = Column(Date)
    description = Column(Text)
    is_active = Column(Boolean, default=True, index=True)
    creation_date = Column(DateTime(timezone=True), server_default=func.now())
    completion_date = Column(Date)

    # Relaciones
    user = relationship("User", back_populates="saving_goals")
    account = relationship("Account", back_populates="saving_goals")

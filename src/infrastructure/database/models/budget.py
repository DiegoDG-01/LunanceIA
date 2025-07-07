from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum, DECIMAL, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from infrastructure.database.connection import Base
from domain.objects.enums import BudgetPeriod


class BudgetModel(Base):
    __tablename__ = "budgets"

    budget_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("categories.category_id"))
    name = Column(String(100), nullable=False)
    limit_amount = Column(DECIMAL(12, 2), nullable=False)
    period = Column(Enum(BudgetPeriod), nullable=False)
    start_date = Column(Date, nullable=False, index=True)
    end_date = Column(Date, index=True)
    is_active = Column(Boolean, default=True, index=True)
    alert_percentage = Column(Integer, default=80)
    creation_date = Column(DateTime(timezone=True), server_default=func.now())

    # Relaciones
    user = relationship("User", back_populates="budgets")
    category = relationship("Category", back_populates="budgets")
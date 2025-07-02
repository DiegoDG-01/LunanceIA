from sqlalchemy import Column, Integer, String, Boolean, Enum, Text
from sqlalchemy.orm import relationship

from infrastructure.database.connection import Base
from domain.objects.enums import TransactionType


class CategoryModel(Base):
    __tablename__ = "categories"

    category_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    type = Column(Enum(TransactionType), nullable=False, index=True)
    icon = Column(String(50))
    color = Column(String(7))  # Para código hex del color
    description = Column(Text)
    is_active = Column(Boolean, default=True)

    # Relaciones
    transactions = relationship("Transaction", back_populates="category")
    subscriptions = relationship("Subscription", back_populates="category")
    budgets = relationship("Budget", back_populates="category")
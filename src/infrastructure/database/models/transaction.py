from sqlalchemy import Column, Integer, DateTime, ForeignKey, Enum, DECIMAL, Text, Date, Table
from sqlalchemy.sql import func

from infrastructure.database.connection import Base
from domain.objects.enums import TransactionType

# Tabla de asociación para la relación muchos a muchos - Temporalmente comentada
transaction_tags = Table(
    'transaction_tags',
    Base.metadata,
    Column('transaction_id', Integer, ForeignKey('transactions.transaction_id', ondelete="CASCADE"), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.tag_id', ondelete="CASCADE"), primary_key=True)
)


class TransactionModel(Base):
    __tablename__ = "transactions"

    transaction_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    account_id = Column(Integer, ForeignKey("accounts.account_id", ondelete="CASCADE"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.category_id"), nullable=False)
    type = Column(Enum(TransactionType), nullable=False, index=True)
    amount = Column(DECIMAL(12, 2), nullable=False)
    transaction_date = Column(Date, nullable=False, index=True)
    description = Column(Text)
    notes = Column(Text)
    creation_date = Column(DateTime(timezone=True), server_default=func.now())

    # Relaciones - Temporalmente comentadas hasta migrar todos los modelos
    # user = relationship("UserModel", back_populates="transactions")
    # account = relationship("AccountModel", back_populates="transactions")
    # category = relationship("CategoryModel", back_populates="transactions")
    # tags = relationship("TagModel", secondary="transaction_tags", back_populates="transactions")
    # subscription_charge = relationship("SubscriptionChargeModel", back_populates="transactions", uselist=False)
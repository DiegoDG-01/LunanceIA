from sqlalchemy import (
    Column,
    Integer,
    DateTime,
    ForeignKey,
    Enum,
    DECIMAL,
    Text,
    Date,
    CHAR,
    Table,
)
from sqlalchemy.sql import func
import uuid

from infrastructure.database.connection import Base
from domain.objects.enums import TransactionType

# Tabla de asociación para la relación muchos a muchos - Temporalmente comentada
transaction_tags = Table(
    "transaction_tags",
    Base.metadata,
    Column(
        "transaction_id",
        Integer,
        ForeignKey("transactions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True
    ),
)


class TransactionModel(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_id = Column(
        Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    uuid = Column(
        CHAR(36),
        unique=True,
        index=True,
        default=lambda: str(uuid.uuid4()),
        nullable=False,
    )
    type = Column(Enum(TransactionType), nullable=False, index=True)
    amount = Column(DECIMAL(12, 2), nullable=False)
    transaction_date = Column(Date, nullable=False, index=True)
    description = Column(Text)
    notes = Column(Text)
    creation_date = Column(DateTime(timezone=True), server_default=func.now())

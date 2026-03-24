import uuid
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Enum,
    DECIMAL,
    CHAR,
)
from sqlalchemy.sql import func

from infrastructure.database.connection import Base
from domain.objects.enums import AccountType


class AccountModel(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    bank_id = Column(
        Integer, ForeignKey("banks.id", ondelete="RESTRICT"), nullable=False
    )
    uuid = Column(
        CHAR(36),
        unique=True,
        index=True,
        default=lambda: str(uuid.uuid4()),
        nullable=False,
    )
    name = Column(String(100), nullable=False)
    type = Column(Enum(AccountType), nullable=False)
    current_balance = Column(DECIMAL(12, 2), default=0.00)
    currency = Column(String(3), default="MXN")
    is_active = Column(Boolean, default=True)
    creation_date = Column(DateTime(timezone=True), server_default=func.now())

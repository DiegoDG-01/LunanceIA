from typing import Optional

from sqlalchemy import String, Enum, Text
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.connection import Base
from domain.objects.enums import TransactionType


class CategoryModel(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50))
    type: Mapped[TransactionType] = mapped_column(Enum(TransactionType), index=True)
    icon: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    color: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)

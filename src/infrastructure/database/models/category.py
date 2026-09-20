from sqlalchemy import Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from domain.objects.enums import TransactionType
from infrastructure.database.connection import Base


class CategoryModel(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50))
    type: Mapped[TransactionType] = mapped_column(Enum(TransactionType), index=True)
    icon: Mapped[str | None] = mapped_column(String(50), nullable=True)
    color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)

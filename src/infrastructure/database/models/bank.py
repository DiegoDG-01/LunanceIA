from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.connection import Base


class BankModel(Base):
    __tablename__ = "banks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    code: Mapped[str] = mapped_column(String(3), unique=True, index=True)
    country: Mapped[str] = mapped_column(String(2), default="MX")
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)

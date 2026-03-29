from typing import Optional

from sqlalchemy import String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.connection import Base


class TagModel(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(50))
    color: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)

    # Constraint único
    __table_args__ = (UniqueConstraint("user_id", "name", name="unique_tag_per_user"),)

from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from infrastructure.database.connection import Base
from .transaction import transaction_tags


class TagModel(Base):
    __tablename__ = "tags"

    tag_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    name = Column(String(50), nullable=False)
    color = Column(String(7))

    # Constraint único
    __table_args__ = (
        UniqueConstraint('user_id', 'name', name='unique_tag_per_user'),
    )

    # Relaciones
    user = relationship("User", back_populates="tags")
    transactions = relationship("Transaction", secondary=transaction_tags, back_populates="tags")
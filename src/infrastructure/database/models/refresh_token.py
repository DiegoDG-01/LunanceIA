from sqlalchemy import CHAR, Column, Integer, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.mysql import VARCHAR
from sqlalchemy.orm import relationship

from infrastructure.database.connection import Base
from datetime import datetime


class RefreshTokenModel(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_uuid = Column(CHAR(36), ForeignKey("users.uuid"), nullable=False)
    token_hash = Column(VARCHAR(255), nullable=False)
    is_revoked = Column(Boolean, default=False)
    expired_at = Column(DateTime, nullable=False, default=datetime.now())
    created_at = Column(DateTime, nullable=False, default=datetime.now())

    # user = relationship("UserModel", back_populates="refresh_tokens")

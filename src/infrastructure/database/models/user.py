from sqlalchemy import CHAR, Column, Integer, String, DateTime, Boolean, func
import uuid

from infrastructure.database.connection import Base


class UserModel(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    auth0_id = Column(String(255), unique=True, index=True, nullable=False)
    uuid = Column(CHAR(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False, index=True)
    picture = Column(String(500), nullable=True)
    email_verified = Column(Boolean, default=False)
    last_login = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    registration_date = Column(DateTime(timezone=True), server_default=func.now())


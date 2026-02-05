from sqlalchemy import Column, Integer, String, Boolean
from infrastructure.database.connection import Base


class BankModel(Base):
    __tablename__ = "banks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    code = Column(String(3), nullable=False, unique=True, index=True)
    country = Column(String(2), nullable=False, default="MX")
    logo_url = Column(String(500), nullable=True)
    color = Column(String(7), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

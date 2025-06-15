from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, ConfigDict


class BaseUser(BaseModel):
    name: str
    email: EmailStr
    is_active: bool = True


class CreateUser(BaseUser):
    password: str


class UpdateUser(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    password_hash: Optional[str] = None


class InDBUser(BaseUser):
    user_id: int
    registration_date: datetime

    model_config = ConfigDict(from_attributes=True)


class User(BaseUser):
    uuid: str
    registration_date: datetime

    model_config = ConfigDict(from_attributes=True)


class UserWithStats(User):
    total_accounts: int = 0
    total_transactions: int = 0
    total_active_suscriptions: int = 0
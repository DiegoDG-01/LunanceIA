from typing import Optional
from pydantic import BaseModel, ConfigDict

from utils.enums import TransactionType


class BaseCategory(BaseModel):
    name: str
    type: TransactionType
    icon: Optional[str] = None
    color: Optional[str] = None
    description: Optional[str] = None
    is_active: bool = True


class CreateCategory(BaseCategory):
    pass


class UpdateCategory(BaseModel):
    name: Optional[str] = None
    type: Optional[TransactionType] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class Category(BaseCategory):
    category_id: int

    model_config = ConfigDict(from_attributes=True)


class CategoriaWithStats(Category):
    total_transactions: int = 0
    total_gastado: float = 0
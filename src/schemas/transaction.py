from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field

from utils.enums import TransactionType
from .category import Category
from .account import Account
from .tag import Tag


class BaseTransaction(BaseModel):
    account_id: int
    category_id: int
    type: TransactionType
    amount: Decimal = Field(..., decimal_places=2, gt=0)
    transaction_date: date
    description: Optional[str] = None
    notes: Optional[str] = None


class CreateTransaction(BaseTransaction):
    etiquetas_ids: Optional[List[int]] = []


class UpdateTransaction(BaseModel):
    account_id: Optional[int] = None
    category_id: Optional[int] = None
    type: Optional[TransactionType] = None
    amount: Optional[Decimal] = Field(None, decimal_places=2, gt=0)
    transaction_date: Optional[date] = None
    description: Optional[str] = None
    notes: Optional[str] = None
    tag_ids: Optional[List[int]] = None


class Transaction(BaseTransaction):
    transaction_id: int
    user_id: int
    transaction_date: datetime

    model_config = ConfigDict(from_attributes=True)


class TransactionDetails(Transaction):
    category: Category
    account: Account
    tags: List[Tag] = []
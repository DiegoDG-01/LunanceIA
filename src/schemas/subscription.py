from typing import Optional
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field

from utils.enums import Frequency, TransactionStatus
from .category import Category
from .account import Account


class BaseSubscription(BaseModel):
    account_id: int
    category_id: int
    name: str
    amount: Decimal = Field(..., decimal_places=2, gt=0)
    frequency: Frequency
    start_date: date
    end_date: Optional[date] = None
    billing_day: Optional[int] = Field(None, ge=1, le=31)
    is_active: bool = True
    description: Optional[str] = None
    service_url: Optional[str] = None


class CreateSubscription(BaseSubscription):
    pass


class UpdateSubscription(BaseModel):
    account_id: Optional[int] = None
    category_id: Optional[int] = None
    name: Optional[str] = None
    amount: Optional[Decimal] = Field(None, decimal_places=2, gt=0)
    frequency: Optional[Frequency] = None
    strt_date: Optional[date] = None
    end_date: Optional[date] = None
    billing_day: Optional[int] = Field(None, ge=1, le=31)
    is_active: Optional[bool] = None
    description: Optional[str] = None
    service_url: Optional[str] = None


class Subscription(BaseSubscription):
    subscription_id: int
    user_id: int
    creation_date: datetime

    model_config = ConfigDict(from_attributes=True)


class SubscriptionDetail(Subscription):
    category: Category
    account: Account
    estimated_monthly_cost: Decimal
    next_payment: Optional[date] = None


# Schemas para CobroSuscripcion
class BaseSubscriptionBilling(BaseModel):
    billing_date: date
    amount: Decimal = Field(..., decimal_places=2, gt=0)
    status: TransactionStatus = TransactionStatus.PENDIENTE


class CreateSubscriptionBilling(BaseSubscriptionBilling):
    subscription_id: int


class UpdateSubscriptionBilling(BaseModel):
    status: Optional[TransactionStatus] = None
    transaction_id: Optional[int] = None


class SubscriptionBilling(BaseSubscriptionBilling):
    charge_id: int
    subscription_id: int
    transaction_id: Optional[int] = None
    processing_date: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
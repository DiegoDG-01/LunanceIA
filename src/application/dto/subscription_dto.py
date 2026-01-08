from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
from datetime import date, datetime

from domain.objects.enums import Frequency

@dataclass
class CreateSubscriptionDTO:

    user_id: int
    category_id: int
    account_uuid: str
    name: str
    amount: Decimal
    frequency: Frequency
    start_date: date
    end_date: Optional[date] = None
    billing_day: Optional[int] = None
    description: Optional[str] = None
    service_url: Optional[str] = None
    currency: str = "MXN"


@dataclass
class UpdateSubscriptionDTO:
    name: Optional[str] = None
    amount: Optional[Decimal] = None
    frequency: Optional[Frequency] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    billing_day: Optional[int] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None
    service_url: Optional[str] = None
    category_id: Optional[int] = None


@dataclass
class SubscriptionResponseDTO:
    uuid: str
    account_name: str
    category_name: Optional[str]
    name: str
    amount: Decimal
    currency: str
    frequency: Frequency
    start_date: date
    end_date: Optional[date]
    billing_day: Optional[int]
    is_active: bool
    description: Optional[str]
    service_url: Optional[str]
    creation_date: datetime

    @classmethod
    def from_entity(
            cls,
            subscription,
            account_name: str,
            category_name: Optional[str]
    ):
        return cls(
            uuid=subscription.uuid,
            account_name=account_name,
            category_name=category_name,
            name=subscription.name,
            amount=subscription.amount.amount,
            currency=subscription.amount.currency,
            frequency=subscription.frequency,
            start_date=subscription.start_date,
            end_date=subscription.end_date,
            billing_day=subscription.billing_day,
            is_active=subscription.is_active,
            description=subscription.description,
            service_url=subscription.service_url,
            creation_date=subscription.creation_date,
        )



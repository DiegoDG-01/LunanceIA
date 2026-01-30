from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
from datetime import date, datetime

from domain.objects.enums import Frequency, TransactionStatus


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
    account_uuid: str = None
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
    account_uuid: str
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
        account_uuid: str,
        account_name: str,
        category_name: Optional[str],
    ):
        return cls(
            uuid=subscription.uuid,
            account_uuid=account_uuid,
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


@dataclass
class SubscriptionChargeDetailResponseDTO:
    """DTO para subscription_charges con datos relacionados"""

    charge_id: str  # sc.id (UUID)
    subscription_name: str  # s.name
    charge_date: date  # sc.charge_date
    charge_amount: Decimal  # sc.amount
    charge_status: TransactionStatus  # sc.status

    transaction_id: Optional[str]  # t.uuid
    transaction_amount: Decimal  # t.amount
    transaction_description: Optional[str]  # t.description

    category_name: Optional[str]  # c.name
    account_name: str  # a.name

    @classmethod
    def from_entity(
        cls,
        charge,
        subscription_name: str,
        transaction_uuid: Optional[str],
        transaction_amount: Decimal,
        transaction_description: Optional[str],
        category_name: Optional[str],
        account_name: str,
    ):
        return cls(
            charge_id=charge.uuid,
            subscription_name=subscription_name,
            charge_date=charge.charge_date,
            charge_amount=charge.amount,
            charge_status=charge.status,
            transaction_id=transaction_uuid,
            transaction_amount=transaction_amount,
            transaction_description=transaction_description,
            category_name=category_name,
            account_name=account_name,
        )

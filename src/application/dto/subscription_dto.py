from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

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
    end_date: date | None = None
    billing_day: int | None = None
    description: str | None = None
    service_url: str | None = None
    currency: str = "MXN"


@dataclass
class UpdateSubscriptionDTO:
    account_uuid: str | None = None
    name: str | None = None
    amount: Decimal | None = None
    frequency: Frequency | None = None
    start_date: date | None = None
    end_date: date | None = None
    billing_day: int | None = None
    is_active: bool | None = None
    description: str | None = None
    service_url: str | None = None
    category_id: int | None = None


@dataclass
class SubscriptionResponseDTO:
    uuid: str
    account_uuid: str | None
    account_name: str | None
    category_name: str | None
    name: str
    amount: Decimal
    currency: str
    frequency: Frequency
    start_date: date
    end_date: date | None
    billing_day: int | None
    next_charge_date: date
    is_active: bool
    description: str | None
    service_url: str | None
    creation_date: datetime

    @classmethod
    def from_entity(
        cls,
        subscription,
        account_uuid: str | None,
        account_name: str | None,
        category_name: str | None,
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
            next_charge_date=subscription.next_charge_date,
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

    transaction_id: str | None  # t.uuid
    transaction_amount: Decimal  # t.amount
    transaction_description: str | None  # t.description

    category_name: str | None  # c.name
    account_name: str  # a.name

    @classmethod
    def from_entity(
        cls,
        charge,
        subscription_name: str,
        transaction_uuid: str | None,
        transaction_amount: Decimal,
        transaction_description: str | None,
        category_name: str | None,
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


@dataclass
class SubscriptionLastTransactionsResponseDTO:
    name: str
    account_name: str | None
    amount: Decimal
    charge_date: date

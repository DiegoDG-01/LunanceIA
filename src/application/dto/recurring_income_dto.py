from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from domain.objects.enums import Frequency, TransactionStatus


@dataclass
class CreateRecurringIncomeDTO:
    user_id: int
    category_id: int
    account_uuid: str
    name: str
    amount: Decimal
    frequency: Frequency
    start_date: date
    end_date: date | None = None
    next_payment_date: date | None = None
    description: str | None = None
    currency: str = "MXN"


@dataclass
class RecurringIncomeResponseDTO:
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
    next_payment_date: date
    is_active: bool
    description: str | None
    creation_date: datetime

    @classmethod
    def from_entity(
        cls,
        income,
        account_uuid: str | None,
        account_name: str | None,
        category_name: str | None,
    ):
        return cls(
            uuid=income.uuid,
            account_uuid=account_uuid,
            account_name=account_name,
            category_name=category_name,
            name=income.name,
            amount=income.amount.amount,
            currency=income.amount.currency,
            frequency=income.frequency,
            start_date=income.start_date,
            end_date=income.end_date,
            next_payment_date=income.next_payment_date,
            is_active=income.is_active,
            description=income.description,
            creation_date=income.creation_date,
        )


@dataclass
class UpdateRecurringIncomeDTO:
    account_uuid: str | None = None
    name: str | None = None
    amount: Decimal | None = None
    frequency: Frequency | None = None
    start_date: date | None = None
    end_date: date | None = None
    next_payment_date: date | None = None
    is_active: bool | None = None
    description: str | None = None
    category_id: int | None = None


@dataclass
class IncomeDepositResponseDTO:
    uuid: str
    deposit_date: date
    amount: Decimal
    currency: str
    status: TransactionStatus
    transaction_uuid: str | None

    @classmethod
    def from_entity(cls, deposit, transaction_uuid: str | None = None):
        return cls(
            uuid=deposit.uuid,
            deposit_date=deposit.deposit_date,
            amount=deposit.amount.amount,
            currency=deposit.amount.currency,
            status=deposit.status,
            transaction_uuid=transaction_uuid,
        )

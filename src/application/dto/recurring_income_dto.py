from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
from datetime import date, datetime

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
    end_date: Optional[date] = None
    next_payment_date: Optional[date] = None
    description: Optional[str] = None
    currency: str = "MXN"


@dataclass
class RecurringIncomeResponseDTO:
    uuid: str
    account_uuid: Optional[str]
    account_name: Optional[str]
    category_name: Optional[str]
    name: str
    amount: Decimal
    currency: str
    frequency: Frequency
    start_date: date
    end_date: Optional[date]
    next_payment_date: date
    is_active: bool
    description: Optional[str]
    creation_date: datetime

    @classmethod
    def from_entity(
        cls,
        income,
        account_uuid: Optional[str],
        account_name: Optional[str],
        category_name: Optional[str],
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
    account_uuid: Optional[str] = None
    name: Optional[str] = None
    amount: Optional[Decimal] = None
    frequency: Optional[Frequency] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    next_payment_date: Optional[date] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None
    category_id: Optional[int] = None


@dataclass
class IncomeDepositResponseDTO:
    uuid: str
    deposit_date: date
    amount: Decimal
    currency: str
    status: TransactionStatus
    transaction_uuid: Optional[str]

    @classmethod
    def from_entity(cls, deposit, transaction_uuid: Optional[str] = None):
        return cls(
            uuid=deposit.uuid,
            deposit_date=deposit.deposit_date,
            amount=deposit.amount.amount,
            currency=deposit.amount.currency,
            status=deposit.status,
            transaction_uuid=transaction_uuid,
        )

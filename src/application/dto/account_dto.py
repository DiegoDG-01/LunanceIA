from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
from datetime import date

from domain.objects.enums import AccountType, TransactionType


@dataclass
class CreditCardSettingsDTO:
    billing_cycle_day: int
    payment_due_day: int
    credit_limit: Decimal
    minimum_payment_percentage: Decimal


@dataclass
class CreateAccountDTO:
    """
    Data Transfer Object for creating an account
    """

    user_id: int
    bank_id: int
    name: str
    account_type: AccountType
    initial_balance: Decimal = Decimal("0.00")
    currency: str = "MXN"
    credit_card_settings: Optional[CreditCardSettingsDTO] = None


@dataclass
class UpdateAccountDTO:
    """
    Data Transfer Object for updating an account
    """

    account_uuid: str
    user_id: int
    bank_id: Optional[int]
    name: Optional[str] = None
    current_balance: Optional[Decimal] = None
    credit_card_settings: Optional[CreditCardSettingsDTO] = None


@dataclass
class AccountResponseDTO:
    account_uuid: str
    bank_id: Optional[int]
    name: str
    account_type: AccountType
    current_balance: Decimal
    currency: str
    is_active: bool
    bank_name: Optional[str]
    bank_code: Optional[str]
    credit_card_settings: Optional[CreditCardSettingsDTO] = None


@dataclass
class AccountActivityResponseDTO:
    name: str
    transaction_type: TransactionType
    category_name: Optional[str]
    amount: Decimal
    transaction_date: date

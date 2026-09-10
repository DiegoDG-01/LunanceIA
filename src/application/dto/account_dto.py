from dataclasses import dataclass
from datetime import date
from decimal import Decimal

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
    credit_card_settings: CreditCardSettingsDTO | None = None


@dataclass
class UpdateAccountDTO:
    """
    Data Transfer Object for updating an account
    """

    account_uuid: str
    user_id: int
    bank_id: int | None
    name: str | None = None
    current_balance: Decimal | None = None
    credit_card_settings: CreditCardSettingsDTO | None = None


@dataclass
class AccountResponseDTO:
    account_uuid: str
    bank_id: int | None
    name: str
    account_type: AccountType
    current_balance: Decimal
    currency: str
    is_active: bool
    bank_name: str | None
    bank_code: str | None
    credit_card_settings: CreditCardSettingsDTO | None = None


@dataclass
class AccountActivityResponseDTO:
    name: str
    transaction_type: TransactionType
    category_name: str | None
    amount: Decimal
    transaction_date: date

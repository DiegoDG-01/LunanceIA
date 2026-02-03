from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
from datetime import date

from domain.objects.enums import AccountType


@dataclass
class CreditCardSettingsDTO:
    billing_cycle_day: int
    payment_due_day: int
    credit_limit: Optional[Decimal] = None
    minimum_payment_percentage: Optional[Decimal] = None


@dataclass
class InvestmentCardSettingsDTO:
    investment_type: str
    interest_rate: Decimal
    lock_period_end_date: Optional[date] = None
    maturity_date: Optional[date] = None
    early_withdrawal_penalty: Optional[Decimal] = None


@dataclass
class CreateAccountDTO:
    """
    Data Transfer Object for creating an account
    """

    user_id: int
    name: str
    account_type: AccountType
    bank: Optional[str]
    initial_balance: Decimal = Decimal("0.00")
    currency: str = "MXN"
    credit_card_settings: Optional[CreditCardSettingsDTO] = None
    investment_settings: Optional[InvestmentCardSettingsDTO] = None


@dataclass
class UpdateAccountDTO:
    """
    Data Transfer Object for updating an account
    """

    account_uuid: str
    user_id: int
    name: Optional[str] = None
    bank: Optional[str] = None
    current_balance: Optional[Decimal] = None
    credit_card_settings: Optional[CreditCardSettingsDTO] = None
    investment_settings: Optional[InvestmentCardSettingsDTO] = None


@dataclass
class AccountResponseDTO:
    account_uuid: str
    name: str
    account_type: AccountType
    current_balance: Decimal
    currency: str
    bank: Optional[str]
    is_active: bool
    credit_card_settings: Optional[CreditCardSettingsDTO] = None
    investment_settings: Optional[InvestmentCardSettingsDTO] = None

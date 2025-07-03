from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
from datetime import datetime

from domain.objects.enums import AccountType


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


@dataclass
class UpdateAccountDTO:
    """
    Data Transfer Object for updating an account
    """

    account_id: int
    user_id: str
    name: Optional[str] = None
    bank: Optional[str] = None
    current_balance: Optional[Decimal] = None


@dataclass
class AccountResponseDTO:
    account_id: int
    user_id: str
    name: str
    account_type: AccountType
    current_balance: Decimal
    currency: str
    bank: Optional[str]
    is_active: bool
    creation_date: datetime

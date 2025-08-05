from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from domain.objects.money import Money
from domain.objects.enums import AccountType


@dataclass
class Account:
    id: Optional[int]
    uuid: Optional[str]
    user_id: int
    name: str
    account_type: AccountType
    current_balance: Money
    bank: Optional[str]
    is_active: bool
    creation_date: datetime

    @classmethod
    def create_new(
        cls,
        user_id: int,
        name: str,
        account_type: AccountType,
        bank: Optional[str],
        initial_balance: Money = None,
    ) -> "Account":
        if initial_balance is None:
            initial_balance = Money(0, "MXN")

        return cls(
            id=None,
            uuid=None,
            user_id=user_id,
            name=name,
            account_type=account_type,
            current_balance=initial_balance,
            bank=bank,
            is_active=True,
            creation_date=datetime.now(),
        )

    def deactivate(self) -> None:
        self.is_active = False

    def activate(self) -> None:
        self.is_active = True

    def update_balance(self, new_balance: Money) -> None:
        if new_balance.currency != self.current_balance.currency:
            raise ValueError("Currencies must be the same to update balance")
        if not self.is_active:
            raise ValueError("Account is inactive")
        if (
            new_balance.amount < self.current_balance.amount
            and self.account_type != AccountType.CREDIT
        ):
            raise ValueError(
                "Balance cannot be less than current balance for non-credit accounts"
            )
        self.current_balance = new_balance

    def can_withdraw(self, amount: Money) -> bool:
        return self.current_balance.amount >= amount.amount

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import cast

from domain.objects.credit_card_settings import CreditCardSettings
from domain.objects.enums import AccountType
from domain.objects.money import Money
from shared.exceptions.domain import AccountInactiveError, InvalidBalanceUpdateError


@dataclass
class Account:
    id: int | None
    uuid: str | None
    user_id: int
    bank_id: int
    name: str
    account_type: AccountType
    current_balance: Money
    is_active: bool
    creation_date: datetime
    credit_card_settings: CreditCardSettings | None = None
    bank_name: str | None = None
    bank_code: str | None = None

    @classmethod
    def create_new(
        cls,
        user_id: int,
        bank_id: int,
        name: str,
        account_type: AccountType,
        initial_balance: Money | None = None,
    ) -> "Account":
        if initial_balance is None:
            initial_balance = Money(Decimal(0), "MXN")

        return cls(
            id=None,
            uuid=None,
            user_id=user_id,
            bank_id=bank_id,
            name=name,
            account_type=account_type,
            current_balance=initial_balance,
            is_active=True,
            creation_date=datetime.now(UTC),
        )

    def deactivate(self) -> None:
        self.is_active = False

    def activate(self) -> None:
        self.is_active = True

    def update_balance(self, new_balance: Money) -> None:
        if new_balance.currency != self.current_balance.currency:
            raise InvalidBalanceUpdateError(
                "Currencies must be the same to update balance"
            )
        if not self.is_active:
            raise AccountInactiveError(cast(int, self.id))
        if new_balance.amount < 0 and self.account_type != AccountType.CREDIT_CARD:
            raise InvalidBalanceUpdateError(self.account_type)
        self.current_balance = new_balance

    def can_withdraw(self, amount: Money) -> bool:
        return self.current_balance.amount >= amount.amount

from dataclasses import dataclass
from decimal import Decimal

from domain.objects.enums import Currency
from shared.exceptions.domain import (
    CurrencyMismatchError,
    InsufficientFundsError,
    InvalidCurrencyError,
    NegativeAmountError,
)

SUPPORTED_CURRENCIES = frozenset(c.value for c in Currency)


def ensure_supported_currency(currency: str) -> None:
    """Una cuenta o un apartado solo puede estar en MXN, USD o EUR.

    `Money` no lo exige por sí solo: también representa precios de valores, que pueden
    venir en otra moneda.
    """
    if currency not in SUPPORTED_CURRENCIES:
        raise InvalidCurrencyError(currency)


@dataclass(frozen=True)
class Money:
    """Value Object to represent a Money"""

    amount: Decimal
    currency: str = "MXN"

    def __post_init__(self):
        if self.amount < 0:
            raise NegativeAmountError(float(self.amount))

    def add(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise CurrencyMismatchError(self.currency, other.currency)
        return Money(self.amount + other.amount, self.currency)

    def subtract(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise CurrencyMismatchError(self.currency, other.currency)
        result_amount = self.amount - other.amount
        if result_amount < 0:
            raise InsufficientFundsError(
                required_amount=float(other.amount),
                available_amount=float(self.amount),
            )
        return Money(result_amount, self.currency)

    def __str__(self):
        return f"{self.amount:.2f} {self.currency}"

from dataclasses import dataclass
from decimal import Decimal
from typing import Union, List

@dataclass(frozen=True)
class Money:
    """Value Object to represent a Money"""
    amount: Decimal
    currency: str = "MXN"

    def __post_init__(self):
        if self.amount < 0:
            raise ValueError("Amount must be greater than 0")

    def add(self, other: 'Money') -> 'Money':
        if self.currency != other.currency:
            raise ValueError("Currencies must be the same to add")
        return Money(self.amount + other.amount, self.currency)

    def subtract(self, other: 'Money') -> 'Money':
        if self.currency != other.currency:
            raise ValueError("Currencies must be the same to subtract")
        return Money(self.amount - other.amount, self.currency)


    def __str__(self):
        return f"{self.amount:.2f} {self.currency}"
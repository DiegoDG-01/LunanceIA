from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional, List

from domain.objects.money import Money
from domain.objects.enums import TransactionType


@dataclass
class Transaction:
    transaction_id: Optional[int]
    user_id: int
    account_id: int
    category_id: Optional[int]
    transaction_type: TransactionType
    amount: Money
    transaction_date: date
    description: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[List[int]] = None
    creation_date: Optional[datetime] = None

    @classmethod
    def create_new(
        cls,
        user_id: int,
        account_id: int,
        category_id: Optional[int],
        transaction_type: TransactionType,
        amount: Money,
        transaction_date: date,
        description: Optional[str] = None,
        notes: Optional[str] = None,
        tags: Optional[List[int]] = None,
    ):
        if transaction_date is None:
            transaction_date = date.today()
        return cls(
            transaction_id=None,
            user_id=user_id,
            account_id=account_id,
            category_id=category_id,
            transaction_type=transaction_type,
            amount=amount,
            transaction_date=transaction_date,
            description=description,
            notes=notes,
            tags=tags,
            creation_date=datetime.now(),
        )

    def is_income(self):
        return self.transaction_type == TransactionType.INCOME

    def is_expense(self):
        return self.transaction_type == TransactionType.EXPENSE

    def update_description(self, new_description: str):
        self.description = new_description

    def add_notes(self, notes: str):
        if self.notes:
            self.notes += f"\n{notes}"
        else:
            self.notes = notes

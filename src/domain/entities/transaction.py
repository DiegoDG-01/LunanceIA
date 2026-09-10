from dataclasses import dataclass
from datetime import UTC, date, datetime

from domain.objects.enums import TransactionType
from domain.objects.money import Money


@dataclass
class Transaction:
    id: int | None
    uuid: str | None
    user_id: int
    account_id: int
    category_id: int | None
    transaction_type: TransactionType
    amount: Money
    transaction_date: date
    description: str | None = None
    notes: str | None = None
    tags: list[int] | None = None
    creation_date: datetime | None = None
    transfer_uuid: str | None = None
    position_id: int | None = None

    @classmethod
    def create_new(
        cls,
        user_id: int,
        account_id: int,
        category_id: int | None,
        transaction_type: TransactionType,
        amount: Money,
        transaction_date: date,
        description: str | None = None,
        notes: str | None = None,
        tags: list[int] | None = None,
    ):
        if transaction_date is None:
            transaction_date = date.today()
        return cls(
            id=None,
            uuid=None,
            user_id=user_id,
            account_id=account_id,
            category_id=category_id,
            transaction_type=transaction_type,
            amount=amount,
            transaction_date=transaction_date,
            description=description,
            notes=notes,
            tags=tags,
            creation_date=datetime.now(UTC),
        )

    def is_income(self):
        return self.transaction_type == TransactionType.INCOME

    def is_expense(self):
        return self.transaction_type == TransactionType.EXPENSE

    def is_transfer(self):
        return self.transaction_type == TransactionType.TRANSFER

    def update_description(self, new_description: str):
        self.description = new_description

    def add_notes(self, notes: str):
        if self.notes:
            self.notes += f"\n{notes}"
        else:
            self.notes = notes

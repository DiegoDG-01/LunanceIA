from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
from datetime import date, datetime

from domain.objects.enums import TransactionType, AccountType


@dataclass
class CreateTransactionDTO:
    """DTO para crear transacción."""

    user_id: int
    account_uuid: str
    category_id: Optional[int]
    transaction_type: TransactionType
    amount: Decimal
    description: Optional[str] = None
    notes: Optional[str] = None
    transaction_date: Optional[date] = None
    currency: str = "MXN"


@dataclass
class UpdateTransactionDTO:
    """DTO para actualizar transacción."""

    description: Optional[str] = None
    notes: Optional[str] = None
    category_id: Optional[int] = None
    transaction_type: Optional[TransactionType] = None
    amount: Optional[Decimal] = None
    transaction_date: Optional[date] = None


@dataclass
class TransactionResponseDTO:
    """DTO para respuesta de transacción."""

    uuid: str
    category: Optional[str]
    transaction_type: TransactionType
    amount: Decimal
    transaction_date: date
    description: Optional[str]
    notes: Optional[str]
    creation_date: datetime
    account_name: str
    account_type: AccountType
    account_bank: Optional[str]

    @classmethod
    def from_entity(
        cls, transaction, account_name, account_type, account_bank, category_name
    ):
        """Create DTO from Transaction entity."""
        return cls(
            uuid=transaction.uuid,
            category=category_name,
            transaction_type=transaction.transaction_type,
            amount=transaction.amount.amount,
            transaction_date=transaction.transaction_date,
            description=transaction.description,
            notes=transaction.notes,
            creation_date=transaction.creation_date,
            account_name=account_name,
            account_type=account_type,
            account_bank=account_bank,
        )

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
from datetime import date, datetime

from domain.objects.enums import TransactionType


@dataclass
class CreateTransactionDTO:
    """DTO para crear transacción."""
    user_id: int
    account_id: int
    category_id: int
    type: TransactionType
    amount: Decimal
    currency: str = "MXN"
    description: Optional[str] = None
    notes: Optional[str] = None
    transaction_date: Optional[date] = None


@dataclass
class UpdateTransactionDTO:
    """DTO para actualizar transacción."""
    transaction_id: int
    user_id: int
    description: Optional[str] = None
    notes: Optional[str] = None
    category_id: Optional[int] = None


@dataclass
class TransactionResponseDTO:
    """DTO para respuesta de transacción."""
    transaction_id: int
    user_id: int
    account_id: int
    category_id: int
    type: TransactionType
    amount: Decimal
    currency: str
    transaction_date: date
    description: Optional[str]
    notes: Optional[str]
    creation_date: datetime

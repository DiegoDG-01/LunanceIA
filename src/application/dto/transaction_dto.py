from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from domain.objects.enums import AccountType, TransactionType


@dataclass
class CreateTransactionDTO:
    """DTO para crear transacción."""

    user_id: int
    account_uuid: str
    category_id: int | None
    transaction_type: TransactionType
    amount: Decimal
    description: str | None = None
    notes: str | None = None
    transaction_date: date | None = None
    currency: str = "MXN"


@dataclass
class UpdateTransactionDTO:
    """DTO para actualizar transacción."""

    description: str | None = None
    notes: str | None = None
    category_id: int | None = None
    transaction_type: TransactionType | None = None
    amount: Decimal | None = None
    transaction_date: date | None = None


@dataclass
class TransactionResponseDTO:
    """DTO para respuesta de transacción."""

    uuid: str
    category: str | None
    transaction_type: TransactionType
    amount: Decimal
    transaction_date: date
    description: str | None
    notes: str | None
    creation_date: datetime
    account_name: str
    account_type: AccountType
    account_uuid: str
    transfer_uuid: str | None = None

    @classmethod
    def from_entity(
        cls,
        transaction,
        account_name: str,
        account_type: AccountType,
        account_uuid: str,
        category_name: str | None,
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
            account_uuid=account_uuid,
            transfer_uuid=transaction.transfer_uuid,
        )


@dataclass
class CreateTransferDTO:
    """DTO para crear transferencia entre cuentas."""

    user_id: int
    source_account_uuid: str
    destination_account_uuid: str
    amount: Decimal
    description: str | None = None
    notes: str | None = None
    transfer_date: date | None = None
    currency: str = "MXN"


@dataclass
class TransferResponseDTO:
    """DTO para respuesta de transferencia."""

    transfer_uuid: str
    amount: Decimal
    transfer_date: date
    description: str | None
    source_account_name: str
    source_account_uuid: str
    destination_account_name: str
    destination_account_uuid: str
    creation_date: datetime

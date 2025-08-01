from typing import Optional
from datetime import datetime
from dataclasses import dataclass

from domain.objects.money import Money
from domain.entities.transaction import TransactionType
from application.dto.transaction_dto import TransactionResponseDTO
from shared.exceptions.domain import TransactionNotFoundError


@dataclass
class UpdateTransactionCommand:
    transaction_uuid: str
    user_id: int
    description: Optional[str] = None
    notes: Optional[str] = None
    category_id: Optional[int] = None
    transaction_type: Optional[str] = None
    amount: Optional[float] = None
    transaction_date: Optional[str] = None


class UpdateTransactionCommandHandler:
    def __init__(self, transaction_repository):
        self.transaction_repository = transaction_repository

    def handle(self, command: UpdateTransactionCommand) -> TransactionResponseDTO:
        transaction = self.transaction_repository.get_by_uuid_and_user_id(
            command.transaction_uuid, command.user_id
        )
        if not transaction:
            raise TransactionNotFoundError(command.transaction_uuid)

        if command.description is not None:
            transaction.description = command.description

        if command.notes is not None:
            transaction.notes = command.notes

        if command.category_id is not None:
            transaction.category_id = command.category_id

        if command.transaction_type is not None:
            try:
                transaction.transaction_type = TransactionType(command.transaction_type)
            except ValueError:
                raise ValueError(
                    f"Invalid transaction type: {command.transaction_type}"
                )

        if command.amount is not None:
            transaction.amount = Money(amount=command.amount, currency="MXN")

        if command.transaction_date is not None:
            if isinstance(command.transaction_date, str):
                transaction.transaction_date = datetime.strptime(
                    command.transaction_date, "%Y-%m-%d"
                ).date()
            else:
                transaction.transaction_date = command.transaction_date

        try:
            self.transaction_repository.update(transaction)
        except Exception as e:
            raise TransactionNotFoundError(f"Error updating transaction: {e}")

        try:
            result = self.transaction_repository.get_by_uuid_with_account_details(
                transaction.uuid, command.user_id
            )
        except Exception as e:
            raise TransactionNotFoundError(
                f"Failed to retrieve updated transaction: {str(e)}"
            )

        if not result:
            raise TransactionNotFoundError(command.transaction_uuid)

        transaction_entity, account_name, account_type, account_bank = result

        return TransactionResponseDTO.from_entity(
            transaction_entity, account_name, account_type, account_bank
        )

from dataclasses import dataclass

from domain.repositories.transaction_repository import TransactionRepository
# from application.dto.transaction_dto import DeleteTransactionDTO


@dataclass
class DeleteTransactionCommand:
    uuid: str
    user_id: int


class DeleteTransactionHandler:
    def __init__(
        self,
        transaction_repository: TransactionRepository,
    ):
        self.transaction_repository = transaction_repository

    def handle(self, command: DeleteTransactionCommand):
        deleted = self.transaction_repository.delete_by_uuid(
            command.uuid, command.user_id
        )

        if not deleted:
            raise ValueError(f"Transaction {command.uuid} not found or access denied")

        return True

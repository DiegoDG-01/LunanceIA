from dataclasses import dataclass

from domain.repositories.transaction_repository import TransactionRepository
from domain.repositories.user_repository import UserRepository
# from application.dto.transaction_dto import DeleteTransactionDTO


@dataclass
class DeleteTransactionCommand:
    uuid: str
    user_id: int


class DeleteTransactionHandler:
    def __init__(
        self,
        transaction_repository: TransactionRepository,
        user_repository: UserRepository,
    ):
        self.transaction_repository = transaction_repository
        self.user_repository = user_repository

    async def handle(self, command: DeleteTransactionCommand):
        self.transaction_repository.delete_by_uuid(command.uuid, command.user_id)

        return True

from dataclasses import dataclass

from domain.repositories.transaction_repository import TransactionRepository
from application.dto.transaction_dto import TransactionResponseDTO
from shared.exceptions.domain import TransactionNotFoundError


@dataclass
class GetTransactionByUuidQuery:
    uuid: str
    user_id: int


class GetTransactionByUuidHandler:
    def __init__(self, transaction_repository: TransactionRepository):
        self.transaction_repository = transaction_repository

    async def handle(self, query: GetTransactionByUuidQuery) -> TransactionResponseDTO:
        transaction = self.transaction_repository.get_by_uuid_with_account_details(
            query.uuid, query.user_id
        )

        if not transaction:
            raise TransactionNotFoundError(query.uuid)

        return TransactionResponseDTO.from_entity(
            transaction[0], transaction[1], transaction[2], transaction[3]
        )

from dataclasses import dataclass
from datetime import date
from typing import cast

from application.dto.transaction_dto import TransactionResponseDTO
from domain.objects.enums import TransactionType
from domain.repositories.transaction_repository import TransactionRepository
from shared.exceptions.domain import TransactionNotFoundError


@dataclass
class GetTransactionsQuery:
    """
    Query to get transactions
    """

    user_id: int
    account_uuid: str | None

    skip: int = 0
    limit: int = 100
    start_date: date | None = None
    end_date: date | None = None
    transaction_type: TransactionType | None = None
    category_id: int | None = None


class GetTransactionsHandler:
    """
    Handler to get transactions
    """

    def __init__(self, transaction_repository: TransactionRepository):
        self.transaction_repository = transaction_repository

    async def handle(self, query: GetTransactionsQuery) -> list[TransactionResponseDTO]:
        transactions = await self.transaction_repository.get_filtered(
            user_id=query.user_id,
            account_uuid=query.account_uuid,
            offset=query.skip,
            limit=query.limit,
            start_date=query.start_date,
            end_date=query.end_date,
            transaction_type=query.transaction_type,
            category_id=query.category_id,
        )

        if transactions is None:
            raise TransactionNotFoundError(
                f"Not found transactions for account: {query.account_uuid}"
            )

        return [
            TransactionResponseDTO.from_entity(
                transaction,
                account_name,
                account_type,
                cast(str, account_uuid),
                category_name,
            )
            for transaction, account_name, account_type, account_uuid, category_name in transactions
        ]

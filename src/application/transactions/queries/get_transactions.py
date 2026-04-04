from dataclasses import dataclass

from datetime import date
from typing import Optional, cast
from domain.objects.enums import TransactionType
from domain.repositories.transaction_repository import TransactionRepository
from application.dto.transaction_dto import TransactionResponseDTO
from shared.exceptions.domain import TransactionNotFoundError


@dataclass
class GetTransactionsQuery:
    """
    Query to get transactions
    """

    user_id: int
    account_uuid: Optional[str]

    skip: int = 0
    limit: int = 100
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    transaction_type: Optional[TransactionType] = None
    category_id: Optional[int] = (
        None  # TODO: Implement category filtering in repository methods
    )


class GetTransactionsHandler:
    """
    Handler to get transactions
    """

    def __init__(self, transaction_repository: TransactionRepository):
        self.transaction_repository = transaction_repository

    async def handle(self, query: GetTransactionsQuery) -> list[TransactionResponseDTO]:
        if query.start_date or query.end_date:
            transactions = await self.transaction_repository.get_by_date_range(
                user_id=query.user_id,
                start_date=query.start_date,
                end_date=query.end_date,
                account_uuid=query.account_uuid,
                transaction_type=query.transaction_type,
            )
        else:
            transactions = await self.transaction_repository.get_by_user(
                user_id=query.user_id, limit=query.limit, offset=query.skip
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

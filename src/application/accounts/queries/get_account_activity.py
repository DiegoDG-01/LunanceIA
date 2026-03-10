from dataclasses import dataclass
from typing import List

from domain.repositories.account_repository import AccountRepository
from domain.repositories.transaction_repository import TransactionRepository
from application.dto.account_dto import AccountActivityResponseDTO
from shared.exceptions.domain import AccountNotFoundError


@dataclass
class GetAccountActivityQuery:
    user_id: int
    account_uuid: str


class GetAccountActivitiesHandler:
    def __init__(
        self,
        account_repository: AccountRepository,
        transaction_repository: TransactionRepository,
    ):
        self.account_repository = account_repository
        self.transaction_repository = transaction_repository

    async def handle(
        self, query: GetAccountActivityQuery
    ) -> List[AccountActivityResponseDTO]:
        account = await self.account_repository.get_by_uuid_and_user_id(
            account_uuid=query.account_uuid, user_id=query.user_id
        )

        if not account:
            raise AccountNotFoundError(account_uuid=query.account_uuid)

        transactions = await self.transaction_repository.get_activity_by_account_id(
            account_id=account.id, limit=5
        )

        if not transactions:
            return []

        account_recent_activities = []

        for transaction, category_name in transactions:
            account_recent_activities.append(
                AccountActivityResponseDTO(
                    name=transaction.description,
                    amount=transaction.amount.amount,
                    category_name=category_name,
                    transaction_date=transaction.transaction_date,
                )
            )

        return account_recent_activities

from dataclasses import dataclass
from typing import List

from application.dto.subscription_dto import SubscriptionLastTransactionsResponseDTO
from domain.repositories.subscription_charge_repository import (
    SubscriptionChargeRepository,
)
from domain.repositories.subscription_repository import SubscriptionRepository
from shared.exceptions.domain import (
    SubscriptionNotFoundError,
    TransactionNotActivityError,
)


@dataclass
class GetLastTransactionsQuery:
    user_id: int
    subscription_uuid: str


class GetLastTransactionsHandler:
    def __init__(
        self,
        subscription_repository: SubscriptionRepository,
        subscription_charge_repository: SubscriptionChargeRepository,
    ):
        self.subscription_repository = subscription_repository
        self.subscription_charge_repository = subscription_charge_repository

    async def handle(
        self, query: GetLastTransactionsQuery
    ) -> List[SubscriptionLastTransactionsResponseDTO]:
        # async def handle(self, query: GetLastTransactionsQuery) -> bool:
        subscription = await self.subscription_repository.get_by_uuid_and_user_id(
            query.subscription_uuid, query.user_id
        )

        if subscription is None:
            raise SubscriptionNotFoundError(subscription_uuid=query.subscription_uuid)

        last_transactions = await self.subscription_charge_repository.get_last_charges_by_subscription_id(
            subscription_id=subscription.id,
        )
        if not last_transactions:
            # TODO: Change to subscriptionNotActivityError
            raise TransactionNotActivityError()

        transactions = []

        for subs_charge, subs_name, account_name in last_transactions:
            transactions.append(
                SubscriptionLastTransactionsResponseDTO(
                    name=subs_name,
                    account_name=account_name,
                    amount=subs_charge.amount.amount,
                    charge_date=subs_charge.processing_date.date(),
                )
            )

        return transactions

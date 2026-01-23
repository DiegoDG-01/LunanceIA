from dataclasses import dataclass
from typing import List, Optional

from application.subscriptions.queries.get_subscriptions import GetSubscriptionsHandler
from domain.repositories.account_repository import AccountRepository
from domain.repositories.category_repository import CategoryRepository
from domain.repositories.subscription_repository import SubscriptionRepository
from application.dto.subscription_dto import SubscriptionResponseDTO

from shared.exceptions.domain import SubscriptionNotFoundError


@dataclass
class GetSubscriptionsByIdQuery:
    subscription_uuid: str
    user_id: int



class GetSubscriptionsByIdHandler:

    def __init__(
            self,
            subscription_repository: SubscriptionRepository,
            account_repository: AccountRepository,
            category_repository: CategoryRepository
    ):
        self.subscription_repository = subscription_repository
        self.account_repository = account_repository
        self.category_repository = category_repository


    async def handle(self, query: GetSubscriptionsByIdQuery) -> Optional[SubscriptionResponseDTO]:

        subscription = self.subscription_repository.get_by_uuid_and_user_id(
            subscription_uuid=query.subscription_uuid, user_id=query.user_id
        )

        if not subscription:
            raise SubscriptionNotFoundError(subscription_uuid=query.subscription_uuid)

        account = await self.account_repository.get_by_id(subscription.account_id)
        account_name = account.name if account else None

        category = (
            await self.category_repository.get_by_id(subscription.category_id)
            if subscription.category_id else None
        )
        category_name = category.name if category else None

        return SubscriptionResponseDTO.from_entity(
            subscription=subscription,
            account_name=account_name,
            category_name=category_name
        )
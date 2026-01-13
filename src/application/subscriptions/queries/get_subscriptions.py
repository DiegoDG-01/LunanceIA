from dataclasses import dataclass
from typing import Optional, List

from domain.repositories.subscription_repository import SubscriptionRepository
from domain.repositories.account_repository import AccountRepository
from domain.repositories.category_repository import CategoryRepository

from application.dto.subscription_dto import SubscriptionResponseDTO


@dataclass
class GetSubscriptionsQuery:
    user_id: int
    account_uuid: Optional[str] = None
    category_id: Optional[int] = None
    active_only: bool = False
    limit: int = 100
    offset: int = 0


class GetSubscriptionsHandler:

    def __init__(
            self,
            subscription_repository: SubscriptionRepository,
            account_repository: AccountRepository,
            category_repository: CategoryRepository,
    ):
        self.subscription_repository = subscription_repository
        self.account_repository = account_repository
        self.category_repository = category_repository

    async def handle(self, query: GetSubscriptionsQuery) -> List[SubscriptionResponseDTO]:
        if query.account_uuid:
            subscriptions = self.subscription_repository.get_by_account(
                account_uuid=query.account_uuid, user_id=query.user_id, limit=query.limit, offset=query.offset
            )
        elif query.category_id:
            subscriptions = self.subscription_repository.get_by_category(
                category_id=query.category_id, user_id=query.user_id
            )
        else:
            subscriptions = self.subscription_repository.get_by_user(
                user_id=query.user_id, active_only=query.active_only,
            )

        response_dtos = []
        for subscription in subscriptions:
            account = await self.account_repository.get_by_id(subscription.account_id)
            account_name = account.name if account else None

            category = (
                await self.category_repository.get_by_id(subscription.category_id)
                if subscription.category_id
                else None
            )

            category_name = category.name if category else None

            dto = SubscriptionResponseDTO.from_entity(subscription, account_name, category_name)
            response_dtos.append(dto)

        return response_dtos

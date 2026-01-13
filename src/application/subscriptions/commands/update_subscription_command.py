from dataclasses import dataclass

from domain.repositories.subscription_repository import SubscriptionRepository
from domain.repositories.category_repository import CategoryRepository
from domain.repositories.account_repository import AccountRepository
from application.dto.subscription_dto import UpdateSubscriptionDTO, SubscriptionResponseDTO
from shared.exceptions.domain import SubscriptionNotFoundError, CategoryNotFoundError


@dataclass
class UpdateSubscriptionCommand:
    subscription_uuid: str
    user_id: int
    dto: UpdateSubscriptionDTO


class UpdateSubscriptionHandler:

    def __init__(
            self,
            subscription_repository: SubscriptionRepository,
            category_repository: CategoryRepository,
            account_repository: AccountRepository,
    ):
        self.subscription_repository = subscription_repository
        self.category_repository = category_repository
        self.account_repository = account_repository

    async def handle(self, command: UpdateSubscriptionCommand) -> SubscriptionResponseDTO:
        dto = command.dto

        subscription = self.subscription_repository.get_by_uuid_and_user_id(
            command.subscription_uuid, command.user_id
        )

        if not subscription:
            raise SubscriptionNotFoundError(command.subscription_uuid)

        if dto.category_id is not None:
            category = await self.category_repository.get_by_id(dto.category_id)
            if not category:
                raise CategoryNotFoundError(dto.category_id)

        for key, value in dto.dict().items():
            if value is not None:
                setattr(subscription, key, value)

        updated_subscription = self.subscription_repository.update(subscription)

        account = await self.account_repository.get_by_id(subscription.account_id)
        account_name = account.name if account else None

        category = (
            await self.category_repository.get_by_id(subscription.category_id)
            if updated_subscription.category_id
            else None
        )
        category_name = category.name if category else None

        return SubscriptionResponseDTO.from_entity(updated_subscription, account_name, category_name)



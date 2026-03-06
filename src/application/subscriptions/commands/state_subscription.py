from dataclasses import dataclass

from domain.repositories.account_repository import AccountRepository
from domain.repositories.category_repository import CategoryRepository
from domain.repositories.subscription_repository import SubscriptionRepository
from domain.repositories.unit_of_work import AbstractUnitOfWork
from application.dto.subscription_dto import SubscriptionResponseDTO

from shared.exceptions.domain import SubscriptionNotFoundError


@dataclass
class StateSubscriptionCommand:
    subscription_uuid: str
    user_id: int


class StateSubscriptionHandler:
    def __init__(
        self,
        subscription_repository: SubscriptionRepository,
        category_repository: CategoryRepository,
        account_repository: AccountRepository,
        uow: AbstractUnitOfWork,
    ):
        self.subscription_repository = subscription_repository
        self.category_repository = category_repository
        self.account_repository = account_repository
        self.uow = uow

    async def handle(self, command: StateSubscriptionCommand) -> bool:
        subscription = await self.subscription_repository.get_by_uuid_and_user_id(
            command.subscription_uuid, command.user_id
        )
        if not subscription:
            raise SubscriptionNotFoundError(subscription_uuid=command.subscription_uuid)

        account = await self.account_repository.get_by_id(subscription.account_id)
        account_uuid = account.uuid if account else None
        account_name = account.name if account else None

        category = (
            await self.category_repository.get_by_id(subscription.category_id)
            if subscription.category_id
            else None
        )
        category_name = category.name if category else None

        async with self.uow:
            subscription_update = await self.subscription_repository.switch_status(
                subscription
            )
            await self.uow.commit()

        return SubscriptionResponseDTO.from_entity(
            subscription_update, account_uuid, account_name, category_name
        )

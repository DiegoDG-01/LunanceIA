from dataclasses import dataclass

from domain.repositories.subscription_repository import SubscriptionRepository
from domain.repositories.unit_of_work import AbstractUnitOfWork
from shared.exceptions.domain import SubscriptionNotFoundError


@dataclass
class DeleteSubscriptionCommand:
    subscription_uuid: str
    user_id: int


class DeleteSubscriptionHandler:
    def __init__(
        self,
        subscription_repository: SubscriptionRepository,
        uow: AbstractUnitOfWork,
    ):
        self.subscription_repository = subscription_repository
        self.uow = uow

    async def handle(self, command: DeleteSubscriptionCommand):
        subscription = await self.subscription_repository.get_by_uuid_and_user_id(
            subscription_uuid=command.subscription_uuid, user_id=command.user_id
        )

        if not subscription:
            raise SubscriptionNotFoundError(subscription_uuid=command.subscription_uuid)

        async with self.uow:
            deleted = await self.subscription_repository.delete(
                uuid=command.subscription_uuid, user_id=command.user_id
            )
            await self.uow.commit()

        if not deleted:
            raise SubscriptionNotFoundError(subscription_uuid=command.subscription_uuid)

        return True

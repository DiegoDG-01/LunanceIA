from dataclasses import dataclass

from domain.repositories.subscription_repository import SubscriptionRepository
from domain.repositories.account_repository import AccountRepository

from shared.exceptions.domain import SubscriptionNotFoundError


@dataclass
class DeleteSubscriptionCommand:
    subscription_uuid: str
    user_id: int


class DeleteSubscriptionHandler:
    def __init__(
            self,
            subscription_repository: SubscriptionRepository,
    ):
        self.subscription_repository = subscription_repository

    def handle(self, command: DeleteSubscriptionCommand):
        subscription = self.subscription_repository.get_by_uuid_and_user_id(
            subscription_uuid=command.subscription_uuid,
            user_id=command.user_id
        )

        if not subscription:
            raise SubscriptionNotFoundError(subscription_uuid=command.subscription_uuid)

        deleted = self.subscription_repository.delete(
            uuid=command.subscription_uuid,
            user_id=command.user_id
        )

        if not deleted:
            raise SubscriptionNotFoundError(subscription_uuid=command.subscription_uuid)

        return True
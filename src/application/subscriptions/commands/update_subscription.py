from dataclasses import dataclass
from datetime import date
from typing import cast

from domain.objects.money import Money
from domain.repositories.subscription_repository import SubscriptionRepository
from domain.repositories.category_repository import CategoryRepository
from domain.repositories.account_repository import AccountRepository
from domain.repositories.unit_of_work import AbstractUnitOfWork
from application.dto.subscription_dto import (
    UpdateSubscriptionDTO,
    SubscriptionResponseDTO,
)
from shared.exceptions.domain import (
    SubscriptionNotFoundError,
    CategoryNotFoundError,
    AccountNotFoundError,
    InvalidSubscriptionDateRangeError,
)


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
        uow: AbstractUnitOfWork,
    ):
        self.subscription_repository = subscription_repository
        self.category_repository = category_repository
        self.account_repository = account_repository
        self.uow = uow

    async def handle(
        self, command: UpdateSubscriptionCommand
    ) -> SubscriptionResponseDTO:
        dto = command.dto

        subscription = await self.subscription_repository.get_by_uuid_and_user_id(
            command.subscription_uuid, command.user_id
        )

        if not subscription:
            raise SubscriptionNotFoundError(command.subscription_uuid)

        if dto.category_id is not None:
            category = await self.category_repository.get_by_id(dto.category_id)
            if not category:
                raise CategoryNotFoundError(dto.category_id)

        if dto.account_uuid is not None:
            account = await self.account_repository.get_by_uuid_and_user_id(
                account_uuid=dto.account_uuid, user_id=command.user_id
            )
            if not account:
                raise AccountNotFoundError(dto.account_uuid)

            subscription.account_id = cast(int, account.id)

        schedule_changed = False

        if dto.category_id is not None:
            subscription.category_id = dto.category_id
        if dto.name is not None:
            subscription.name = dto.name
        if dto.amount is not None:
            subscription.amount = Money(
                dto.amount, currency=subscription.amount.currency
            )
        if dto.frequency is not None:
            subscription.frequency = dto.frequency
            schedule_changed = True
        if dto.start_date is not None:
            subscription.start_date = dto.start_date
            schedule_changed = True
        if dto.end_date is not None:
            subscription.end_date = dto.end_date
        if dto.billing_day is not None:
            subscription.billing_day = dto.billing_day
            schedule_changed = True
        if dto.is_active is not None:
            subscription.is_active = dto.is_active
        if dto.description is not None:
            subscription.description = dto.description
        if dto.service_url is not None:
            subscription.service_url = dto.service_url

        if (
            subscription.end_date is not None
            and subscription.end_date < subscription.start_date
        ):
            raise InvalidSubscriptionDateRangeError(
                str(subscription.start_date), str(subscription.end_date)
            )

        if schedule_changed:
            subscription.reschedule(date.today())

        async with self.uow:
            updated_subscription = await self.subscription_repository.update(
                subscription
            )
            await self.uow.commit()

        account = await self.account_repository.get_by_id(subscription.account_id)
        account_uuid = account.uuid if account else None
        account_name = account.name if account else None

        category = (
            await self.category_repository.get_by_id(subscription.category_id)
            if updated_subscription.category_id
            else None
        )
        category_name = category.name if category else None

        return SubscriptionResponseDTO.from_entity(
            updated_subscription, account_uuid, account_name, category_name
        )

from dataclasses import dataclass
from typing import cast

from domain.entities.subscription import Subscription
from domain.repositories.subscription_repository import SubscriptionRepository
from domain.repositories.user_repository import UserRepository
from domain.repositories.account_repository import AccountRepository
from domain.repositories.category_repository import CategoryRepository
from domain.repositories.unit_of_work import AbstractUnitOfWork
from domain.objects.money import Money
from application.dto.subscription_dto import (
    CreateSubscriptionDTO,
    SubscriptionResponseDTO,
)
from shared.exceptions.domain import UserNotFoundError, AccountNotFoundError


@dataclass
class CreateSubscriptionCommand:
    dto: CreateSubscriptionDTO


class CreateSubscriptionHandler:
    def __init__(
        self,
        subscription_repository: SubscriptionRepository,
        user_repository: UserRepository,
        account_repository: AccountRepository,
        category_repository: CategoryRepository,
        uow: AbstractUnitOfWork,
    ):
        self.subscription_repository = subscription_repository
        self.user_repository = user_repository
        self.account_repository = account_repository
        self.category_repository = category_repository
        self.uow = uow

    async def handle(
        self, command: CreateSubscriptionCommand
    ) -> SubscriptionResponseDTO:
        dto = command.dto

        user = await self.user_repository.get_by_id(dto.user_id)
        if not user or not user.is_active:
            raise UserNotFoundError()

        account = await self.account_repository.get_by_uuid_and_user_id(
            account_uuid=dto.account_uuid, user_id=dto.user_id
        )

        if not account:
            raise AccountNotFoundError(account_uuid=dto.account_uuid)

        category = (
            await self.category_repository.get_by_id(dto.category_id)
            if dto.category_id
            else None
        )

        category_name = category.name if category else None

        amount = Money(amount=dto.amount, currency=dto.currency)

        subscription = Subscription.create_new(
            user_id=dto.user_id,
            account_id=cast(int, account.id),
            category_id=dto.category_id,
            name=dto.name,
            amount=amount,
            frequency=dto.frequency,
            start_date=dto.start_date,
            end_date=dto.end_date,
            billing_day=dto.billing_day,
            description=dto.description,
            service_url=dto.service_url,
        )

        async with self.uow:
            saved_subscription = await self.subscription_repository.create(subscription)
            await self.uow.commit()

        return SubscriptionResponseDTO.from_entity(
            saved_subscription,
            account_uuid=account.uuid,
            account_name=account.name,
            category_name=category_name,
        )

from datetime import date

from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.subscription import Subscription
from domain.objects.money import Money
from domain.repositories.subscription_repository import SubscriptionRepository
from infrastructure.database.models import AccountModel
from infrastructure.database.models.subscription import SubscriptionModel
from shared.exceptions.domain import SubscriptionNotFoundError


class SQLAlchemySubscriptionRepository(SubscriptionRepository):
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _model_to_entity(model: SubscriptionModel) -> Subscription:
        return Subscription(
            id=model.id,
            uuid=model.uuid,
            user_id=model.user_id,
            account_id=model.account_id,
            category_id=model.category_id,
            name=model.name,
            amount=Money(amount=model.amount, currency="MXN"),
            frequency=model.frequency,
            start_date=model.start_date,
            end_date=model.end_date,
            billing_day=model.billing_day,
            is_active=model.is_active,
            description=model.description,
            service_url=model.service_url,
            creation_date=model.creation_date,
            next_charge_date=model.next_charge_date,
        )

    @staticmethod
    def _entity_to_model(entity: Subscription) -> SubscriptionModel:
        return SubscriptionModel(
            uuid=entity.uuid,
            user_id=entity.user_id,
            account_id=entity.account_id,
            category_id=entity.category_id,
            name=entity.name,
            amount=entity.amount.amount,
            frequency=entity.frequency.value,
            start_date=entity.start_date,
            end_date=entity.end_date,
            billing_day=entity.billing_day,
            is_active=entity.is_active,
            description=entity.description,
            service_url=entity.service_url,
            creation_date=entity.creation_date,
            next_charge_date=entity.next_charge_date,
        )

    async def create(self, subscription: Subscription) -> Subscription:
        model = self._entity_to_model(subscription)
        self.db.add(model)
        await self.db.flush()
        await self.db.refresh(model)
        return self._model_to_entity(model)

    async def update(self, subscription: Subscription) -> Subscription:
        stmt = select(SubscriptionModel).where(
            SubscriptionModel.uuid == subscription.uuid
        )
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            raise SubscriptionNotFoundError(str(subscription.uuid))

        model.user_id = subscription.user_id
        model.account_id = subscription.account_id
        model.category_id = subscription.category_id
        model.name = subscription.name
        model.amount = subscription.amount.amount
        model.frequency = subscription.frequency
        model.start_date = subscription.start_date
        model.end_date = subscription.end_date
        model.billing_day = subscription.billing_day
        model.is_active = subscription.is_active
        model.description = subscription.description
        model.service_url = subscription.service_url
        model.next_charge_date = subscription.next_charge_date

        await self.db.flush()
        await self.db.refresh(model)
        return self._model_to_entity(model)

    async def delete(self, uuid: str, user_id: int) -> bool:
        stmt = select(SubscriptionModel).where(
            and_(SubscriptionModel.uuid == uuid, SubscriptionModel.user_id == user_id)
        )
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()

        if model:
            await self.db.delete(model)
            await self.db.flush()
            return True

        return False

    async def get_by_uuid_and_user_id(
        self, subscription_uuid: str, user_id: int
    ) -> Subscription | None:
        stmt = select(SubscriptionModel).where(
            and_(
                SubscriptionModel.uuid == subscription_uuid,
                SubscriptionModel.user_id == user_id,
            )
        )
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()

        return self._model_to_entity(model) if model else None

    async def get_by_account(
        self, account_uuid: str, user_id: int, limit: int = 100, offset: int = 0
    ) -> list[Subscription]:
        stmt = (
            select(SubscriptionModel, AccountModel)
            .join(AccountModel, SubscriptionModel.account_id == AccountModel.id)
            .where(
                and_(
                    AccountModel.uuid == account_uuid,
                    SubscriptionModel.user_id == user_id,
                )
            )
            .order_by(desc(SubscriptionModel.creation_date))
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(stmt)
        models = result.all()

        return [self._model_to_entity(subscription) for subscription, _ in models]

    async def get_by_category(
        self,
        user_id: int,
        category_id: int,
    ) -> list[Subscription]:
        stmt = (
            select(SubscriptionModel)
            .where(
                and_(
                    SubscriptionModel.user_id == user_id,
                    SubscriptionModel.category_id == category_id,
                )
            )
            .order_by(desc(SubscriptionModel.creation_date))
        )
        result = await self.db.execute(stmt)
        models = result.scalars().all()

        return [self._model_to_entity(model) for model in models]

    async def get_by_user(
        self, user_id: int, active_only: bool = False
    ) -> list[Subscription]:
        stmt = select(SubscriptionModel).where(SubscriptionModel.user_id == user_id)

        if active_only:
            stmt = stmt.where(SubscriptionModel.is_active)

        result = await self.db.execute(stmt)
        results = result.scalars().all()

        return [self._model_to_entity(subscription) for subscription in results]

    # async def get_active_subscriptions(self) -> List[Subscription]:
    #     stmt = select(SubscriptionModel).where(SubscriptionModel.is_active)
    #     result = await self.db.execute(stmt)
    #     results = result.scalars().all()
    #
    #     return [self._model_to_entity(subscription) for subscription in results]

    async def get_due_subscriptions(self, as_of: date) -> list[Subscription]:
        stmt = select(SubscriptionModel).where(
            SubscriptionModel.is_active,
            SubscriptionModel.next_charge_date <= as_of,
        )
        result = await self.db.execute(stmt)
        results = result.scalars().all()

        return [self._model_to_entity(subscription) for subscription in results]

    async def switch_status(self, subscription: Subscription) -> Subscription:
        subscription.is_active = not subscription.is_active
        return await self.update(subscription)

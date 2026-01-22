from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from typing import Optional, List

from domain.entities.subscription import Subscription
from domain.repositories.subscription_repository import SubscriptionRepository
from domain.objects.money import Money
from infrastructure.database.models import AccountModel
from infrastructure.database.models.subscription import SubscriptionModel


class SQLAlchemySubscriptionRepository(SubscriptionRepository):

    def __init__(self, db: Session):
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
        )

    def create(self, subscription: Subscription) -> Subscription:
        model = self._entity_to_model(subscription)
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return self._model_to_entity(model)

    def update(self, subscription: Subscription) -> Subscription:
        model = (
            self.db.query(SubscriptionModel)
            .filter(SubscriptionModel.uuid == subscription.uuid)
            .first()
        )

        if not model:
            raise ValueError("Subscription no encontrada")

        for field, value in subscription.__dict__.items():
            setattr(model, field, value)

        self.db.commit()
        self.db.refresh(model)
        return self._model_to_entity(model)

    def delete(self, uuid: str, user_id: int) -> bool:
        result = (
            self.db.query(SubscriptionModel)
            .filter(
                and_(
                    SubscriptionModel.uuid == uuid,
                    SubscriptionModel.user_id == user_id
                )
            )
            .delete(synchronize_session=False)
        )

        self.db.commit()
        return result > 0

    def get_by_uuid_and_user_id(self, subscription_uuid: str, user_id: int) -> Optional[Subscription]:
        model = (
            self.db.query(SubscriptionModel)
            .filter(
                and_(
                    SubscriptionModel.uuid == subscription_uuid,
                    SubscriptionModel.user_id == user_id)
            )
            .first()
        )

        return self._model_to_entity(model) if model else None


    def get_by_account(
            self, account_uuid: str, user_id: int, limit: int = 100, offset: int = 0
    ) -> List[Subscription]:

        models = (
            self.db.query(SubscriptionModel, AccountModel)
            .join(AccountModel, SubscriptionModel.account_id == AccountModel.id)
            .filter(
                and_(
                    AccountModel.uuid == account_uuid,
                    SubscriptionModel.user_id == user_id,
                )
            )
            .order_by(desc(SubscriptionModel.creation_date))
            .limit(limit)
            .offset(offset)
            .all()
        )

        return [self._model_to_entity(subscription) for subscription, _ in models]

    def get_by_category(
            self, user_id: int, category_id: int,
    ) -> List[Subscription]:

        models = (
            self.db.query(SubscriptionModel)
            .filter(
                and_(
                    SubscriptionModel.user_id == user_id,
                    SubscriptionModel.category_id == category_id,
                )
            )
            .order_by(desc(SubscriptionModel.creation_date))
            .all()
        )

        return [self._model_to_entity(model) for model in models]


    def get_by_user(self, user_id: int, active_only: bool = False) -> List[Subscription]:
        results = (
            self.db.query(SubscriptionModel)
            .filter(
                and_(
                    SubscriptionModel.user_id == user_id
                )
            )
        )

        if active_only:
            results = results.filter(SubscriptionModel.is_active)

        results = results.all()

        return [self._model_to_entity(subscription) for subscription in results]

    def get_active_subscriptions(self) -> List[Subscription]:
        results = (
            self.db.query(SubscriptionModel)
            .filter(
                SubscriptionModel.is_active
            )
            .all()
        )

        return [self._model_to_entity(subscription) for subscription in results]
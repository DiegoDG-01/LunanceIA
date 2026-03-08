from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, asc, extract, desc, select
from typing import Optional, List, Tuple
from datetime import date

from domain.entities.subscription_charge import SubscriptionCharge
from domain.repositories.subscription_charge_repository import (
    SubscriptionChargeRepository,
)
from domain.objects.money import Money
from domain.objects.enums import TransactionStatus
from infrastructure.database.models import (
    SubscriptionChargeModel,
    SubscriptionModel,
    TransactionModel,
    CategoryModel,
    AccountModel,
)
from shared.exceptions.domain import SubscriptionNotFoundError


class SQLAlchemySubscriptionChargeRepository(SubscriptionChargeRepository):
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _model_to_entity(model: SubscriptionChargeModel) -> SubscriptionCharge:
        return SubscriptionCharge(
            id=model.id,
            uuid=model.uuid,
            subscription_id=model.subscription_id,
            charge_date=model.charge_date,
            amount=Money(model.amount),
            status=model.status,
            transaction_id=model.transaction_id,
            processing_date=model.processing_date,
        )

    @staticmethod
    def _entity_to_model(entity: SubscriptionCharge) -> SubscriptionChargeModel:
        return SubscriptionChargeModel(
            id=entity.id,
            uuid=entity.uuid,
            subscription_id=entity.subscription_id,
            charge_date=entity.charge_date,
            amount=entity.amount.amount,
            status=entity.status,
            transaction_id=entity.transaction_id,
            processing_date=entity.processing_date,
        )

    async def create(self, subscription: SubscriptionCharge) -> SubscriptionCharge:
        model = self._entity_to_model(subscription)
        self.db.add(model)
        await self.db.flush()
        await self.db.refresh(model)
        return self._model_to_entity(model)

    async def update(self, charge: SubscriptionCharge) -> SubscriptionCharge:
        stmt = select(SubscriptionChargeModel).where(
            SubscriptionChargeModel.uuid == charge.uuid
        )
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            raise SubscriptionNotFoundError(charge.uuid)

        model.subscription_id = charge.subscription_id
        model.charge_date = charge.charge_date
        model.amount = charge.amount.amount
        model.status = charge.status
        model.transaction_id = charge.transaction_id
        model.processing_date = charge.processing_date

        await self.db.flush()
        await self.db.refresh(model)
        return self._model_to_entity(model)

    async def get_by_id(self, charge_id: int) -> Optional[SubscriptionCharge]:
        stmt = select(SubscriptionChargeModel).where(
            SubscriptionChargeModel.id == charge_id
        )
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()

        return self._model_to_entity(model) if model else None

    async def get_by_subscription(
        self, subscription_id: int, limit: int = 100, offset: int = 0
    ) -> List[SubscriptionCharge]:
        stmt = (
            select(SubscriptionChargeModel)
            .where(SubscriptionChargeModel.subscription_id == subscription_id)
            .order_by(asc(SubscriptionChargeModel.charge_date))
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        models = result.scalars().all()

        return [self._model_to_entity(model) for model in models]

    async def get_by_subscription_and_month(
        self, subscription_id: int, year: int, month: int
    ) -> Optional[SubscriptionCharge]:
        stmt = select(SubscriptionChargeModel).where(
            and_(
                SubscriptionChargeModel.subscription_id == subscription_id,
                extract("year", SubscriptionChargeModel.charge_date) == year,
                extract("month", SubscriptionChargeModel.charge_date) == month,
            )
        )
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()

        return self._model_to_entity(model) if model else None

    async def get_by_subscription_and_date(
        self, subscription_id: int, charge_date: date
    ) -> Optional[SubscriptionCharge]:
        stmt = select(SubscriptionChargeModel).where(
            and_(
                SubscriptionChargeModel.subscription_id == subscription_id,
                SubscriptionChargeModel.charge_date == charge_date,
            )
        )
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()

        return self._model_to_entity(model) if model else None

    async def get_pending_charges(self) -> List[SubscriptionCharge]:
        stmt = (
            select(SubscriptionChargeModel)
            .where(SubscriptionChargeModel.status == TransactionStatus.PENDIENTE)
            .order_by(asc(SubscriptionChargeModel.charge_date))
        )
        result = await self.db.execute(stmt)
        models = result.scalars().all()

        return [self._model_to_entity(model) for model in models]

    async def get_by_user_with_details(self, user_id: int) -> List[tuple]:
        """Retorna subscription_charges con datos relacionados via JOIN"""
        stmt = (
            select(
                SubscriptionChargeModel,
                SubscriptionModel,
                TransactionModel,
                CategoryModel,
                AccountModel,
            )
            .join(
                SubscriptionModel,
                SubscriptionChargeModel.subscription_id == SubscriptionModel.id,
            )
            .join(
                TransactionModel,
                SubscriptionChargeModel.transaction_id == TransactionModel.id,
            )
            .outerjoin(CategoryModel, TransactionModel.category_id == CategoryModel.id)
            .join(AccountModel, TransactionModel.account_id == AccountModel.id)
            .where(SubscriptionModel.user_id == user_id)
            .order_by(desc(SubscriptionChargeModel.charge_date))
        )
        result = await self.db.execute(stmt)
        results = result.all()

        return [
            self._models_to_charge_detail(charge, sub, trans, cat, acc)
            for charge, sub, trans, cat, acc in results
        ]

    @staticmethod
    def _models_to_charge_detail(
        charge_model: SubscriptionChargeModel,
        subscription_model: SubscriptionModel,
        transaction_model: TransactionModel,
        category_model: Optional[CategoryModel],
        account_model: AccountModel,
    ) -> tuple:
        """Convierte modelos a tupla con datos necesarios"""
        return (
            charge_model,
            subscription_model.name,
            transaction_model.uuid,
            transaction_model.amount,
            transaction_model.description,
            category_model.name if category_model else None,
            account_model.name,
        )

    async def get_last_charges_by_subscription_id(
        self, subscription_id: int
    ) -> List[Tuple[SubscriptionCharge, Optional[str]]]:
        stmt = (
            select(SubscriptionChargeModel, SubscriptionModel, AccountModel)
            .join(
                SubscriptionModel,
                SubscriptionChargeModel.subscription_id == SubscriptionModel.id,
            )
            .join(AccountModel, SubscriptionModel.account_id == AccountModel.id)
            .where(SubscriptionChargeModel.subscription_id == subscription_id)
            .order_by(desc(SubscriptionChargeModel.charge_date))
            .limit(5)
        )
        result = await self.db.execute(stmt)
        results = result.all()

        return [
            (
                self._model_to_entity(subscription_charge),
                subscription.name,
                account.name,
            )
            for subscription_charge, subscription, account in results
        ]

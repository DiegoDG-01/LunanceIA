from sqlalchemy.orm import Session
from sqlalchemy import and_, asc, extract, desc
from typing import Optional, List
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


class SQLAlchemySubscriptionChargeRepository(SubscriptionChargeRepository):
    def __init__(self, db: Session):
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

    def create(self, subscription: SubscriptionCharge) -> SubscriptionCharge:
        model = self._entity_to_model(subscription)
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return self._model_to_entity(model)

    def update(self, charge: SubscriptionCharge) -> SubscriptionCharge:
        model = (
            self.db.query(SubscriptionChargeModel)
            .filter(SubscriptionChargeModel.uuid == charge.uuid)
            .first()
        )

        model.subscription_id = charge.subscription_id
        model.charge_date = charge.charge_date
        model.amount = charge.amount.amount
        model.status = charge.status
        model.transaction_id = charge.transaction_id
        model.processing_date = charge.processing_date

        self.db.commit()
        self.db.refresh(model)
        return self._model_to_entity(model)

    def get_by_id(self, charge_id: int) -> Optional[SubscriptionCharge]:
        model = (
            self.db.query(SubscriptionChargeModel)
            .filter(SubscriptionChargeModel.id == charge_id)
            .first()
        )

        return self._model_to_entity(model) if model else None

    def get_by_subscription(
        self, subscription_id: int, limit: int = 100, offset: int = 0
    ) -> List[SubscriptionCharge]:
        models = (
            self.db.query(SubscriptionChargeModel)
            .filter(SubscriptionChargeModel.subscription_id == subscription_id)
            .order_by(asc(SubscriptionChargeModel.charge_date))
            .offset(offset)
            .limit(limit)
            .all()
        )

        return [self._model_to_entity(model) for model in models]

    def get_by_subscription_and_month(
        self, subscription_id: int, year: int, month: int
    ) -> Optional[SubscriptionCharge]:
        model = (
            self.db.query(SubscriptionChargeModel)
            .filter(
                and_(
                    SubscriptionChargeModel.subscription_id == subscription_id,
                    extract("year", SubscriptionChargeModel.charge_date) == year,
                    extract("month", SubscriptionChargeModel.charge_date) == month,
                )
            )
            .first()
        )

        return self._model_to_entity(model) if model else None

    def get_by_subscription_and_date(
        self, subscription_id: int, charge_date: date
    ) -> Optional[SubscriptionCharge]:
        model = (
            self.db.query(SubscriptionChargeModel)
            .filter(
                and_(
                    SubscriptionChargeModel.subscription_id == subscription_id,
                    SubscriptionChargeModel.charge_date == charge_date,
                )
            )
            .first()
        )

        return self._model_to_entity(model) if model else None

    def get_pending_charges(self) -> List[SubscriptionCharge]:
        models = (
            self.db.query(SubscriptionChargeModel)
            .filter(SubscriptionChargeModel.status == TransactionStatus.PENDIENTE)
            .order_by(asc(SubscriptionChargeModel.charge_date))
            .all()
        )

        return [self._model_to_entity(model) for model in models]

    def get_by_user_with_details(self, user_id: int) -> List[tuple]:
        """Retorna subscription_charges con datos relacionados via JOIN"""
        results = (
            self.db.query(
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
            .filter(SubscriptionModel.user_id == user_id)
            .order_by(desc(SubscriptionChargeModel.charge_date))
            .all()
        )

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

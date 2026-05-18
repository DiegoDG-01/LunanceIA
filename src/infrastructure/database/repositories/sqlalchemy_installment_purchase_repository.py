from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from domain.entities.installment_purchase import InstallmentPurchase
from domain.repositories.installment_purchase_repository import (
    InstallmentPurchaseRepository,
)
from domain.objects.money import Money
from infrastructure.database.models.installment import InstallmentPurchaseModel


class SQLAlchemyInstallmentPurchaseRepository(InstallmentPurchaseRepository):
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _model_to_entity(model: InstallmentPurchaseModel) -> InstallmentPurchase:
        return InstallmentPurchase(
            id=model.id,
            uuid=model.uuid,
            user_id=model.user_id,
            account_id=model.account_id,
            category_id=model.category_id,
            description=model.description,
            total_amount=Money(model.total_amount),
            num_installments=model.num_installments,
            installment_type=model.installment_type,
            annual_interest_rate=model.annual_interest_rate,
            monthly_payment=model.monthly_payment,
            purchase_date=model.purchase_date,
            notes=model.notes,
            is_active=model.is_active,
            creation_date=model.creation_date,
        )

    @staticmethod
    def _entity_to_model(entity: InstallmentPurchase) -> InstallmentPurchaseModel:
        return InstallmentPurchaseModel(
            id=entity.id,
            uuid=entity.uuid,
            user_id=entity.user_id,
            account_id=entity.account_id,
            category_id=entity.category_id,
            description=entity.description,
            total_amount=entity.total_amount.amount,
            num_installments=entity.num_installments,
            installment_type=entity.installment_type,
            annual_interest_rate=entity.annual_interest_rate,
            monthly_payment=entity.monthly_payment,
            purchase_date=entity.purchase_date,
            notes=entity.notes,
            is_active=entity.is_active,
            creation_date=entity.creation_date,
        )

    async def create(self, purchase: InstallmentPurchase) -> InstallmentPurchase:
        model = self._entity_to_model(purchase)
        self.db.add(model)
        await self.db.flush()
        await self.db.refresh(model)
        return self._model_to_entity(model)

    async def get_by_id(self, purchase_id: int) -> Optional[InstallmentPurchase]:
        stmt = select(InstallmentPurchaseModel).where(
            InstallmentPurchaseModel.id == purchase_id
        )
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()
        return self._model_to_entity(model) if model else None

    async def get_by_uuid(
        self, uuid: str, user_id: int
    ) -> Optional[InstallmentPurchase]:
        stmt = select(InstallmentPurchaseModel).where(
            InstallmentPurchaseModel.uuid == uuid,
            InstallmentPurchaseModel.user_id == user_id,
        )
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()
        return self._model_to_entity(model) if model else None

    async def get_all_by_user_id(self, user_id: int) -> List[InstallmentPurchase]:
        stmt = select(InstallmentPurchaseModel).where(
            InstallmentPurchaseModel.user_id == user_id
        )
        result = await self.db.execute(stmt)
        models = result.scalars().all()
        return [self._model_to_entity(model) for model in models]

    async def update(self, purchase: InstallmentPurchase) -> InstallmentPurchase:
        stmt = select(InstallmentPurchaseModel).where(
            InstallmentPurchaseModel.id == purchase.id
        )
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()
        model.is_active = purchase.is_active
        model.notes = purchase.notes
        model.description = purchase.description
        model.category_id = purchase.category_id
        await self.db.flush()
        await self.db.refresh(model)
        return self._model_to_entity(model)

    async def delete(self, purchase_uuid: str) -> bool:
        stmt = select(InstallmentPurchaseModel).where(
            InstallmentPurchaseModel.uuid == purchase_uuid
        )
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return False
        await self.db.delete(model)
        return True

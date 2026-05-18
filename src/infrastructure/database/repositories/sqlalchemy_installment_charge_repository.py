from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, delete

from domain.entities.installment_charge import InstallmentCharge
from domain.repositories.installment_charge_repository import (
    InstallmentChargeRepository,
)
from infrastructure.database.models import InstallmentPurchaseModel
from infrastructure.database.models.installment import InstallmentChargeModel


class SQLAlchemyInstallmentChargeRepository(InstallmentChargeRepository):
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _model_to_entity(model: InstallmentChargeModel) -> InstallmentCharge:
        return InstallmentCharge(
            id=model.id,
            uuid=model.uuid,
            installment_purchase_id=model.installment_purchase_id,
            installment_number=model.installment_number,
            amount=model.amount,
            due_date=model.due_date,
            paid=model.paid,
            transaction_id=model.transaction_id,
            paid_at=model.paid_at,
            creation_date=model.creation_date,
        )

    async def create_bulk(
        self, charges: List[InstallmentCharge]
    ) -> List[InstallmentCharge]:
        models = [
            InstallmentChargeModel(
                installment_purchase_id=c.installment_purchase_id,
                installment_number=c.installment_number,
                amount=c.amount,
                due_date=c.due_date,
                paid=c.paid,
            )
            for c in charges
        ]
        self.db.add_all(models)
        await self.db.flush()
        for model in models:
            await self.db.refresh(model)
        return [self._model_to_entity(model) for model in models]

    async def get_by_uuid(self, uuid: str) -> Optional[InstallmentCharge]:
        stmt = select(InstallmentChargeModel).where(InstallmentChargeModel.uuid == uuid)
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()
        return self._model_to_entity(model) if model else None

    async def get_by_purchase_id(self, purchase_id: int) -> List[InstallmentCharge]:
        stmt = (
            select(InstallmentChargeModel)
            .where(InstallmentChargeModel.installment_purchase_id == purchase_id)
            .order_by(InstallmentChargeModel.installment_number)
        )
        result = await self.db.execute(stmt)
        models = result.scalars().all()
        return [self._model_to_entity(model) for model in models]

    async def get_bulk_by_purchase_ids(
        self, purchase_ids: List[int]
    ) -> List[InstallmentCharge]:
        if not purchase_ids:
            return []
        stmt = (
            select(InstallmentChargeModel)
            .where(InstallmentChargeModel.installment_purchase_id.in_(purchase_ids))
            .order_by(
                InstallmentChargeModel.installment_purchase_id,
                InstallmentChargeModel.installment_number,
            )
        )
        result = await self.db.execute(stmt)
        models = result.scalars().all()
        return [self._model_to_entity(model) for model in models]

    async def get_pending_charges(self, user_id: int) -> List[InstallmentCharge]:
        stmt = (
            select(InstallmentChargeModel)
            .join(
                InstallmentPurchaseModel,
                InstallmentChargeModel.installment_purchase_id
                == InstallmentPurchaseModel.id,
            )
            .where(
                and_(
                    InstallmentPurchaseModel.user_id == user_id,
                    InstallmentChargeModel.paid == False,
                )
            )
            .order_by(InstallmentChargeModel.due_date)
        )
        result = await self.db.execute(stmt)
        models = result.scalars().all()
        return [self._model_to_entity(model) for model in models]

    async def update(self, charge: InstallmentCharge) -> InstallmentCharge:
        stmt = select(InstallmentChargeModel).where(
            InstallmentChargeModel.uuid == charge.uuid
        )
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()
        model.paid = charge.paid
        model.transaction_id = charge.transaction_id
        model.paid_at = charge.paid_at
        await self.db.flush()
        await self.db.refresh(model)
        return self._model_to_entity(model)

    async def delete_by_purchase_id(self, purchase_id: int) -> None:
        stmt = delete(InstallmentChargeModel).where(
            InstallmentChargeModel.installment_purchase_id == purchase_id
        )
        await self.db.execute(stmt)

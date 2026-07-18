from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, desc, select
from typing import Optional, List, Tuple, cast
from datetime import date

from infrastructure.database.models import IncomeDepositModel, TransactionModel
from domain.entities.income_deposit import IncomeDeposit
from domain.repositories.income_deposit_repository import IncomeDepositRepository
from domain.objects.money import Money
from shared.exceptions.domain import (
    IncomeDepositNotFoundError,
)


class SQLAlchemyIncomeDepositRepository(IncomeDepositRepository):
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _model_to_entity(model: IncomeDepositModel) -> IncomeDeposit:
        return IncomeDeposit(
            id=model.id,
            uuid=model.uuid,
            recurring_income_id=model.recurring_income_id,
            deposit_date=model.deposit_date,
            amount=Money(model.amount, currency="MXN"),
            status=model.status,
            transaction_id=model.transaction_id,
            processing_date=model.processing_date,
        )

    @staticmethod
    def _entity_to_model(entity: IncomeDeposit) -> IncomeDepositModel:
        return IncomeDepositModel(
            recurring_income_id=entity.recurring_income_id,
            deposit_date=entity.deposit_date,
            amount=entity.amount.amount,
            status=entity.status,
            transaction_id=entity.transaction_id,
            processing_date=entity.processing_date,
        )

    async def create(self, deposit: IncomeDeposit) -> IncomeDeposit:
        model = self._entity_to_model(deposit)
        self.db.add(model)
        await self.db.flush()
        await self.db.refresh(model)
        return self._model_to_entity(model)

    async def update(self, deposit: IncomeDeposit) -> IncomeDeposit:
        stmt = select(IncomeDepositModel).where(IncomeDepositModel.uuid == deposit.uuid)
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            raise IncomeDepositNotFoundError(cast(str, deposit.uuid))

        model.recurring_income_id = deposit.recurring_income_id
        model.deposit_date = deposit.deposit_date
        model.amount = deposit.amount.amount
        model.status = deposit.status
        model.transaction_id = deposit.transaction_id
        model.processing_date = deposit.processing_date

        await self.db.flush()
        await self.db.refresh(model)
        return self._model_to_entity(model)

    async def get_by_income(
        self, recurring_income_id: int, limit: int = 100, offset: int = 0
    ) -> List[Tuple[IncomeDeposit, Optional[str]]]:
        stmt = (
            select(IncomeDepositModel, TransactionModel.uuid)
            .outerjoin(
                TransactionModel,
                IncomeDepositModel.transaction_id == TransactionModel.id,
            )
            .where(IncomeDepositModel.recurring_income_id == recurring_income_id)
            .order_by(desc(IncomeDepositModel.deposit_date))
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        rows = result.all()

        return [
            (self._model_to_entity(model), transaction_uuid)
            for model, transaction_uuid in rows
        ]

    async def get_by_income_and_date(
        self, recurring_income_id: int, deposit_date: date
    ) -> Optional[IncomeDeposit]:
        stmt = select(IncomeDepositModel).where(
            and_(
                IncomeDepositModel.recurring_income_id == recurring_income_id,
                IncomeDepositModel.deposit_date == deposit_date,
            )
        )
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()

        return self._model_to_entity(model) if model else None

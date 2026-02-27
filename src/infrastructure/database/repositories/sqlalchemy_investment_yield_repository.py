from datetime import date
from typing import Optional, List

from sqlalchemy import and_, asc, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.investment_yield import InvestmentYield
from domain.repositories.investment_yield_repository import InvestmentYieldRepository
from infrastructure.database.models.investment_yield import InvestmentYieldModel


class SQLAlchemyInvestmentYieldRepository(InvestmentYieldRepository):
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _model_to_entity(model: InvestmentYieldModel) -> InvestmentYield:
        return InvestmentYield(
            id=model.id,
            uuid=model.uuid,
            account_id=model.account_id,
            yield_date=model.yield_date,
            principal_amount=model.principal_amount,
            yield_amount=model.yield_amount,
            cumulative_balance=model.cumulative_balance,
            annual_rate=model.annual_rate,
            interest_type=model.interest_type,
            created_at=model.created_at,
        )

    @staticmethod
    def _entity_to_model(entity: InvestmentYield) -> InvestmentYieldModel:
        return InvestmentYieldModel(
            id=entity.id,
            uuid=entity.uuid,
            account_id=entity.account_id,
            yield_date=entity.yield_date,
            principal_amount=entity.principal_amount,
            yield_amount=entity.yield_amount,
            cumulative_balance=entity.cumulative_balance,
            annual_rate=entity.annual_rate,
            interest_type=entity.interest_type,
            created_at=entity.created_at,
        )

    async def create(self, yield_record: InvestmentYield) -> InvestmentYield:
        model = self._entity_to_model(yield_record)

        self.db.add(model)
        await self.db.commit()
        await self.db.refresh(model)

        return self._model_to_entity(model)

    async def get_by_account_id(
        self, account_id: int, limit: int = 365, offset: int = 0
    ) -> List[InvestmentYield]:
        stmt = (
            select(InvestmentYieldModel)
            .where(InvestmentYieldModel.account_id == account_id)
            .order_by(desc(InvestmentYieldModel.yield_date))
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(stmt)
        models = result.scalars().all()
        return [self._model_to_entity(model) for model in models]

    async def get_by_account_and_date(
        self, account_id: int, yield_date: date
    ) -> Optional[InvestmentYield]:
        stmt = select(InvestmentYieldModel).where(
            and_(
                InvestmentYieldModel.account_id == account_id,
                InvestmentYieldModel.yield_date == yield_date,
            )
        )
        result = await self.db.execute(stmt)
        model = result.scalars().one_or_none()
        return self._model_to_entity(model) if model else None

    async def get_first_by_account_id(
        self,
        account_id: int,
    ) -> Optional[InvestmentYield]:
        stmt = (
            select(InvestmentYieldModel)
            .where(InvestmentYieldModel.account_id == account_id)
            .order_by(asc(InvestmentYieldModel.yield_date))
            .limit(1)
        )
        result = await self.db.execute(stmt)
        model = result.scalars().one_or_none()
        return self._model_to_entity(model) if model else None

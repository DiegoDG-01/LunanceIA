from datetime import date
from decimal import Decimal

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.budget import Budget
from domain.objects.enums import BudgetPeriod, TransactionType
from domain.repositories.budget_repository import BudgetRepository
from infrastructure.database.models.budget import BudgetModel
from infrastructure.database.models.transaction import TransactionModel
from shared.exceptions.domain import BudgetNotFoundError


class SQLAlchemyBudgetRepository(BudgetRepository):
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _model_to_entity(model: BudgetModel) -> Budget:
        return Budget(
            id=model.id,
            uuid=model.uuid,
            user_id=model.user_id,
            category_id=model.category_id,
            name=model.name,
            limit_amount=model.limit_amount,
            period=BudgetPeriod(model.period),
            start_date=model.start_date,
            end_date=model.end_date,
            is_active=model.is_active,
            alert_percentage=model.alert_percentage,
            creation_date=model.creation_date,
        )

    @staticmethod
    def _entity_to_model(entity: Budget) -> BudgetModel:
        return BudgetModel(
            user_id=entity.user_id,
            category_id=entity.category_id,
            name=entity.name,
            limit_amount=entity.limit_amount,
            period=entity.period.value,
            start_date=entity.start_date,
            end_date=entity.end_date,
            is_active=entity.is_active,
            alert_percentage=entity.alert_percentage,
            creation_date=entity.creation_date,
        )

    async def create(self, budget: Budget) -> Budget:
        model = self._entity_to_model(budget)
        self.db.add(model)
        await self.db.flush()
        await self.db.refresh(model)
        return self._model_to_entity(model)

    async def update(self, budget: Budget) -> Budget:
        stmt = select(BudgetModel).where(BudgetModel.uuid == budget.uuid)
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            raise BudgetNotFoundError(str(budget.uuid))

        model.category_id = budget.category_id
        model.name = budget.name
        model.limit_amount = budget.limit_amount
        model.period = budget.period
        model.start_date = budget.start_date
        model.end_date = budget.end_date
        model.is_active = budget.is_active
        model.alert_percentage = budget.alert_percentage

        await self.db.flush()
        await self.db.refresh(model)
        return self._model_to_entity(model)

    async def delete(self, uuid: str, user_id: int) -> bool:
        stmt = select(BudgetModel).where(
            and_(BudgetModel.uuid == uuid, BudgetModel.user_id == user_id)
        )
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()

        if model:
            await self.db.delete(model)
            await self.db.flush()
            return True

        return False

    async def get_by_uuid_and_user_id(
        self, budget_uuid: str, user_id: int
    ) -> Budget | None:
        stmt = select(BudgetModel).where(
            and_(
                BudgetModel.uuid == budget_uuid,
                BudgetModel.user_id == user_id,
            )
        )
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()
        return self._model_to_entity(model) if model else None

    async def get_by_user(
        self,
        user_id: int,
        active_only: bool = False,
        category_id: int | None = None,
    ) -> list[Budget]:
        stmt = select(BudgetModel).where(BudgetModel.user_id == user_id)

        if active_only:
            stmt = stmt.where(BudgetModel.is_active.is_(True))

        if category_id is not None:
            stmt = stmt.where(BudgetModel.category_id == category_id)

        stmt = stmt.order_by(desc(BudgetModel.creation_date))

        result = await self.db.execute(stmt)
        models = result.scalars().all()
        return [self._model_to_entity(m) for m in models]

    async def switch_status(self, budget: Budget) -> Budget:
        budget.is_active = not budget.is_active
        return await self.update(budget)

    async def get_spending_for_period(
        self,
        user_id: int,
        period_start: date,
        period_end: date,
        category_id: int | None = None,
    ) -> Decimal:
        """
        Suma el total de transacciones de tipo EXPENSE del usuario en el rango de fechas,
        opcionalmente filtrado por categoría.
        """
        stmt = select(func.coalesce(func.sum(TransactionModel.amount), 0)).where(
            and_(
                TransactionModel.user_id == user_id,
                TransactionModel.type == TransactionType.EXPENSE,
                TransactionModel.transaction_date >= period_start,
                TransactionModel.transaction_date <= period_end,
            )
        )

        if category_id is not None:
            stmt = stmt.where(TransactionModel.category_id == category_id)

        result = await self.db.execute(stmt)
        total = result.scalar_one()
        return Decimal(str(total)) if total else Decimal("0.00")

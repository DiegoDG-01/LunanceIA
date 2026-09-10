from datetime import date

from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.recurring_income import RecurringIncome
from domain.objects.money import Money
from domain.repositories.recurring_income_repository import RecurringIncomeRepository
from infrastructure.database.models import AccountModel
from infrastructure.database.models.recurring_income import RecurringIncomeModel
from shared.exceptions.domain import RecurringIncomeNotFoundError


class SQLAlchemyRecurringIncomeRepository(RecurringIncomeRepository):
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _model_to_entity(model: RecurringIncomeModel) -> RecurringIncome:
        return RecurringIncome(
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
            next_payment_date=model.next_payment_date,
            is_active=model.is_active,
            description=model.description,
            creation_date=model.creation_date,
        )

    @staticmethod
    def _entity_to_model(entity: RecurringIncome) -> RecurringIncomeModel:
        return RecurringIncomeModel(
            user_id=entity.user_id,
            account_id=entity.account_id,
            category_id=entity.category_id,
            name=entity.name,
            next_payment_date=entity.next_payment_date,
            frequency=entity.frequency.value,
            amount=entity.amount.amount,
            start_date=entity.start_date,
            end_date=entity.end_date,
            is_active=entity.is_active,
            description=entity.description,
            creation_date=entity.creation_date,
        )

    async def create(self, income: RecurringIncome) -> RecurringIncome:
        model = self._entity_to_model(income)
        self.db.add(model)
        await self.db.flush()
        await self.db.refresh(model)
        return self._model_to_entity(model)

    async def update(self, recurring_income: RecurringIncome) -> RecurringIncome:
        stmt = select(RecurringIncomeModel).where(
            RecurringIncomeModel.uuid == recurring_income.uuid
        )
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            raise RecurringIncomeNotFoundError(str(recurring_income.uuid))

        model.user_id = recurring_income.user_id
        model.account_id = recurring_income.account_id
        model.category_id = recurring_income.category_id
        model.name = recurring_income.name
        model.amount = recurring_income.amount.amount
        model.frequency = recurring_income.frequency
        model.start_date = recurring_income.start_date
        model.end_date = recurring_income.end_date
        model.is_active = recurring_income.is_active
        model.description = recurring_income.description
        model.next_payment_date = recurring_income.next_payment_date

        await self.db.flush()
        await self.db.refresh(model)
        return self._model_to_entity(model)

    async def delete(self, uuid: str, user_id: int) -> bool:
        stmt = select(RecurringIncomeModel).where(
            and_(
                RecurringIncomeModel.uuid == uuid,
                RecurringIncomeModel.user_id == user_id,
            )
        )
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()

        if model:
            await self.db.delete(model)
            await self.db.flush()
            return True

        return False

    async def get_by_uuid_and_user_id(
        self, income_uuid: str, user_id: int
    ) -> RecurringIncome | None:
        stmt = select(RecurringIncomeModel).where(
            and_(
                RecurringIncomeModel.uuid == income_uuid,
                RecurringIncomeModel.user_id == user_id,
            )
        )
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()

        return self._model_to_entity(model) if model else None

    async def get_by_account(
        self, account_uuid: str, user_id: int, limit: int = 100, offset: int = 0
    ) -> list[RecurringIncome]:
        stmt = (
            select(RecurringIncomeModel, AccountModel)
            .join(AccountModel, RecurringIncomeModel.account_id == AccountModel.id)
            .where(
                and_(
                    AccountModel.uuid == account_uuid,
                    RecurringIncomeModel.user_id == user_id,
                )
            )
            .order_by(desc(RecurringIncomeModel.creation_date))
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(stmt)
        models = result.all()

        return [self._model_to_entity(income) for income, _ in models]

    async def get_by_category(
        self,
        user_id: int,
        category_id: int,
    ) -> list[RecurringIncome]:
        stmt = (
            select(RecurringIncomeModel)
            .where(
                and_(
                    RecurringIncomeModel.user_id == user_id,
                    RecurringIncomeModel.category_id == category_id,
                )
            )
            .order_by(desc(RecurringIncomeModel.creation_date))
        )
        result = await self.db.execute(stmt)
        models = result.scalars().all()

        return [self._model_to_entity(model) for model in models]

    async def get_by_user(
        self, user_id: int, active_only: bool = False
    ) -> list[RecurringIncome]:
        stmt = select(RecurringIncomeModel).where(
            RecurringIncomeModel.user_id == user_id
        )

        if active_only:
            stmt = stmt.where(RecurringIncomeModel.is_active)

        result = await self.db.execute(stmt)
        results = result.scalars().all()

        return [self._model_to_entity(income) for income in results]

    async def get_due_incomes(self, as_of: date) -> list[RecurringIncome]:
        stmt = select(RecurringIncomeModel).where(
            RecurringIncomeModel.is_active,
            RecurringIncomeModel.next_payment_date <= as_of,
        )
        result = await self.db.execute(stmt)
        results = result.scalars().all()

        return [self._model_to_entity(m) for m in results]

    async def switch_status(self, income: RecurringIncome) -> RecurringIncome:
        income.is_active = not income.is_active
        return await self.update(income)

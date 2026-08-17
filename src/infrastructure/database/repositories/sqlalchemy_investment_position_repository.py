from datetime import date
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, select

from domain.entities.investment_position import InvestmentPosition
from domain.objects.enums import PositionStatus, PositionType
from domain.objects.money import Money
from domain.repositories.investment_position_repository import (
    InvestmentPositionRepository,
)
from infrastructure.database.models.account import AccountModel
from infrastructure.database.models.investment_position import InvestmentPositionModel
from shared.exceptions.domain import InvestmentPositionNotFoundError


class SQLAlchemyInvestmentPositionRepository(InvestmentPositionRepository):
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _model_to_entity(model: InvestmentPositionModel) -> InvestmentPosition:
        return InvestmentPosition(
            id=model.id,
            uuid=model.uuid,
            account_id=model.account_id,
            name=model.name,
            position_type=model.position_type,
            status=model.status,
            balance=Money(amount=model.balance, currency=model.currency),
            accrued_yield=Money(amount=model.accrued_yield, currency=model.currency),
            annual_rate=model.annual_rate,
            interest_type=model.interest_type,
            start_date=model.start_date,
            on_maturity=model.on_maturity,
            base_principal=model.base_principal,
            term_days=model.term_days,
            lock_period_end_date=model.lock_period_end_date,
            maturity_date=model.maturity_date,
            early_withdrawal_penalty=model.early_withdrawal_penalty,
            max_balance=model.max_balance,
            overflow_action=model.overflow_action,
            overflow_position_id=model.overflow_position_id,
            created_at=model.created_at,
        )

    @staticmethod
    def _entity_to_model(entity: InvestmentPosition) -> InvestmentPositionModel:
        return InvestmentPositionModel(
            account_id=entity.account_id,
            name=entity.name,
            position_type=entity.position_type,
            status=entity.status,
            balance=entity.balance.amount,
            accrued_yield=entity.accrued_yield.amount,
            currency=entity.balance.currency,
            annual_rate=entity.annual_rate,
            interest_type=entity.interest_type,
            start_date=entity.start_date,
            on_maturity=entity.on_maturity,
            base_principal=entity.base_principal,
            term_days=entity.term_days,
            lock_period_end_date=entity.lock_period_end_date,
            maturity_date=entity.maturity_date,
            early_withdrawal_penalty=entity.early_withdrawal_penalty,
            max_balance=entity.max_balance,
            overflow_action=entity.overflow_action,
            overflow_position_id=entity.overflow_position_id,
        )

    async def create(self, position: InvestmentPosition) -> InvestmentPosition:
        model = self._entity_to_model(position)
        self.db.add(model)
        await self.db.flush()
        await self.db.refresh(model)
        return self._model_to_entity(model)

    async def get_by_id(
        self, position_id: int, *, for_update: bool = False
    ) -> Optional[InvestmentPosition]:
        stmt = select(InvestmentPositionModel).where(
            InvestmentPositionModel.id == position_id
        )

        if for_update:
            stmt = stmt.with_for_update()

        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._model_to_entity(model)

    async def get_by_uuid_and_user_id(
        self, position_uuid: str, user_id: int, *, for_update: bool = False
    ) -> Optional[InvestmentPosition]:
        stmt = (
            select(InvestmentPositionModel)
            .join(AccountModel, InvestmentPositionModel.account_id == AccountModel.id)
            .where(
                and_(
                    InvestmentPositionModel.uuid == position_uuid,
                    AccountModel.user_id == user_id,
                )
            )
        )

        if for_update:
            stmt = stmt.with_for_update(of=InvestmentPositionModel)

        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._model_to_entity(model)

    async def get_by_account_id(self, account_id: int) -> List[InvestmentPosition]:
        stmt = (
            select(InvestmentPositionModel)
            .where(InvestmentPositionModel.account_id == account_id)
            .order_by(InvestmentPositionModel.id)
        )
        result = await self.db.execute(stmt)
        models = result.scalars().all()
        return [self._model_to_entity(model) for model in models]

    async def get_active_positions(self) -> List[InvestmentPosition]:
        stmt = (
            select(InvestmentPositionModel)
            .join(AccountModel, InvestmentPositionModel.account_id == AccountModel.id)
            .where(
                and_(
                    InvestmentPositionModel.status == PositionStatus.ACTIVE,
                    AccountModel.is_active,
                )
            )
        )
        result = await self.db.execute(stmt)
        models = result.scalars().all()
        return [self._model_to_entity(model) for model in models]

    async def get_due_for_maturity(self, as_of: date) -> List[InvestmentPosition]:
        stmt = (
            select(InvestmentPositionModel)
            .join(AccountModel, InvestmentPositionModel.account_id == AccountModel.id)
            .where(
                and_(
                    InvestmentPositionModel.status == PositionStatus.ACTIVE,
                    InvestmentPositionModel.position_type == PositionType.FIXED_TERM,
                    InvestmentPositionModel.maturity_date <= as_of,
                    AccountModel.is_active,
                )
            )
        )
        result = await self.db.execute(stmt)
        models = result.scalars().all()
        return [self._model_to_entity(model) for model in models]

    async def get_by_overflow_target(
        self, position_id: int, *, for_update: bool = False
    ) -> List[InvestmentPosition]:
        stmt = select(InvestmentPositionModel).where(
            InvestmentPositionModel.overflow_position_id == position_id
        )

        if for_update:
            stmt = stmt.with_for_update()

        result = await self.db.execute(stmt)
        models = result.scalars().all()
        return [self._model_to_entity(model) for model in models]

    async def update(self, position: InvestmentPosition) -> InvestmentPosition:
        stmt = select(InvestmentPositionModel).where(
            InvestmentPositionModel.uuid == position.uuid
        )
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            raise InvestmentPositionNotFoundError(str(position.uuid))

        model.name = position.name
        model.status = position.status
        model.balance = position.balance.amount
        model.accrued_yield = position.accrued_yield.amount
        model.annual_rate = position.annual_rate
        model.interest_type = position.interest_type
        model.base_principal = position.base_principal
        model.start_date = position.start_date
        model.term_days = position.term_days
        model.lock_period_end_date = position.lock_period_end_date
        model.maturity_date = position.maturity_date
        model.early_withdrawal_penalty = position.early_withdrawal_penalty
        model.on_maturity = position.on_maturity
        model.max_balance = position.max_balance
        model.overflow_action = position.overflow_action
        model.overflow_position_id = position.overflow_position_id

        await self.db.flush()
        await self.db.refresh(model)
        return self._model_to_entity(model)

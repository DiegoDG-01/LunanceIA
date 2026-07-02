from sqlalchemy import select, and_
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.saving_goal import SavingGoal
from shared.exceptions.domain import SavingGoalNotFoundError
from infrastructure.database.models.saving_goal import SavingGoalModel
from domain.repositories.saving_goal_repository import SavingGoalRepository


class SQLAlchemySavingGoalRepository(SavingGoalRepository):
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _model_to_entity(model: SavingGoalModel) -> SavingGoal:
        return SavingGoal(
            id=model.id,
            uuid=model.uuid,
            user_id=model.user_id,
            account_id=model.account_id,
            name=model.name,
            target_amount=model.target_amount,
            target_date=model.target_date,
            description=model.description,
            is_active=model.is_active,
            completion_date=model.completion_date,
            creation_date=model.creation_date,
        )

    @staticmethod
    def _entity_to_model(entity: SavingGoal) -> SavingGoalModel:
        return SavingGoalModel(
            id=entity.id,
            uuid=entity.uuid,
            user_id=entity.user_id,
            account_id=entity.account_id,
            name=entity.name,
            target_amount=entity.target_amount,
            target_date=entity.target_date,
            description=entity.description,
            is_active=entity.is_active,
            completion_date=entity.completion_date,
            creation_date=entity.creation_date,
        )

    async def create(self, goal: SavingGoal) -> SavingGoal:
        model = self._entity_to_model(goal)
        self.db.add(model)
        await self.db.flush()
        await self.db.refresh(model)
        return self._model_to_entity(model)

    async def update(self, goal: SavingGoal) -> SavingGoal:
        stmt = select(SavingGoalModel).where(SavingGoalModel.uuid == goal.uuid)
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            raise SavingGoalNotFoundError(goal_uuid=goal.uuid)

        model.name = goal.name
        model.target_amount = goal.target_amount
        model.target_date = goal.target_date
        model.description = goal.description
        model.is_active = goal.is_active
        model.completion_date = goal.completion_date

        await self.db.flush()
        await self.db.refresh(model)
        return self._model_to_entity(model)

    async def delete(self, goal_uuid: str, user_id: int) -> bool:
        stmt = select(SavingGoalModel).where(
            and_(SavingGoalModel.uuid == goal_uuid, SavingGoalModel.user_id == user_id)
        )
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()

        if model:
            await self.db.delete(model)
            await self.db.flush()
            return True
        return False


    async def get_by_uuid_and_user_id(self, goal_uuid: str, user_id: int) -> Optional[SavingGoal]:
        stmt = select(SavingGoalModel).where(
            and_(SavingGoalModel.uuid == goal_uuid, SavingGoalModel.user_id == user_id)
        )
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()
        return self._model_to_entity(model) if model else None


    async def get_by_user(self, user_id: int, active_only: bool = True) -> list[SavingGoal]:
        stmt = select(SavingGoalModel).where(SavingGoalModel.user_id == user_id)

        if active_only:
            stmt = stmt.where(SavingGoalModel.is_active.is_(True))

        stmt = stmt.order_by(SavingGoalModel.creation_date.desc())

        result = await self.db.execute(stmt)
        models = result.scalars().all()
        return [self._model_to_entity(model) for model in models]


    async def switch_status(self, goal: SavingGoal) -> SavingGoal:
        goal.is_active = not goal.is_active
        return await self.update(goal)

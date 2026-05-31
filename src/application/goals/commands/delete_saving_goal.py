from dataclasses import dataclass

from domain.repositories.saving_goal_repository import SavingGoalRepository
from domain.repositories.unit_of_work import AbstractUnitOfWork
from shared.exceptions.domain import SavingGoalNotFoundError


@dataclass
class DeleteSavingGoalCommand:
    user_id: int
    saving_goal_uuid: str


class DeleteSavingGoalHandler:
    def __init__(
        self,
        goal_repository: SavingGoalRepository,
        uow: AbstractUnitOfWork,
    ):
        self.goal_repository = goal_repository
        self.uow = uow

    async def handle(self, command: DeleteSavingGoalCommand) -> bool:
        goal = await self.goal_repository.get_by_uuid_and_user_id(
            goal_uuid=command.saving_goal_uuid, user_id=command.user_id
        )

        if not goal:
            raise SavingGoalNotFoundError(command.saving_goal_uuid)

        async with self.uow:
            deleted = await self.goal_repository.delete(
                goal_uuid=command.saving_goal_uuid, user_id=command.user_id
            )
            await self.uow.commit()

        if not deleted:
            raise SavingGoalNotFoundError(command.saving_goal_uuid)

        return True

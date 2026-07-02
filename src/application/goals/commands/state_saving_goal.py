from dataclasses import dataclass

from application.dto.saving_goal_dto import SavingGoalResponseDTO
from domain.repositories.account_repository import AccountRepository
from domain.repositories.saving_goal_repository import SavingGoalRepository
from domain.repositories.unit_of_work import AbstractUnitOfWork
from shared.exceptions.domain import AccountNotFoundError, SavingGoalNotFoundError


@dataclass
class StateSavingGoalCommand:
    user_id: int
    goal_uuid: str


class StateSavingGoalHandler:
    def __init__(
        self,
        goal_repository: SavingGoalRepository,
        account_repository: AccountRepository,
        uow: AbstractUnitOfWork,
    ):
        self.goal_repository = goal_repository
        self.account_repository = account_repository
        self.uow = uow

    async def handle(self, command: StateSavingGoalCommand) -> SavingGoalResponseDTO:
        goal = await self.goal_repository.get_by_uuid_and_user_id(
            goal_uuid=command.goal_uuid, user_id=command.user_id
        )
        if not goal:
            raise SavingGoalNotFoundError(command.goal_uuid)

        account = await self.account_repository.get_by_id(goal.account_id)
        if not account:
            raise AccountNotFoundError(account_uuid=str(goal.account_id))

        async with self.uow:
            updated_goal = await self.goal_repository.switch_status(goal)
            await self.uow.commit()

        return SavingGoalResponseDTO.from_entity(
            goal=updated_goal,
            account_name=account.name,
            account_uuid=account.uuid,
            current_amount=account.current_balance.amount,
        )
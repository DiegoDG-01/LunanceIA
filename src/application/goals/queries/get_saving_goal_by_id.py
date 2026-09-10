from dataclasses import dataclass

from application.dto.saving_goal_dto import SavingGoalResponseDTO
from domain.repositories.account_repository import AccountRepository
from domain.repositories.saving_goal_repository import SavingGoalRepository
from shared.exceptions.domain import AccountNotFoundError, SavingGoalNotFoundError


@dataclass
class GetSavingGoalQuery:
    user_id: int
    goal_uuid: str


class GetSavingGoalByIdHandler:
    def __init__(
        self,
        goal_repository: SavingGoalRepository,
        account_repository: AccountRepository,
    ):
        self.goal_repository = goal_repository
        self.account_repository = account_repository

    async def handle(self, query: GetSavingGoalQuery) -> SavingGoalResponseDTO:
        goal = await self.goal_repository.get_by_uuid_and_user_id(
            goal_uuid=query.goal_uuid, user_id=query.user_id
        )
        if not goal:
            raise SavingGoalNotFoundError(query.goal_uuid)

        account = await self.account_repository.get_by_id(goal.account_id)
        if not account:
            raise AccountNotFoundError(account_uuid=str(goal.account_id))

        return SavingGoalResponseDTO.from_entity(
            goal=goal,
            account_name=account.name,
            account_uuid=account.uuid,
            current_amount=account.current_balance.amount,
        )

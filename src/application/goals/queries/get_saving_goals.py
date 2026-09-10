from dataclasses import dataclass

from application.dto.saving_goal_dto import SavingGoalResponseDTO
from domain.repositories.account_repository import AccountRepository
from domain.repositories.saving_goal_repository import SavingGoalRepository


@dataclass
class GetSavingGoalsQuery:
    user_id: int
    active_only: bool = True


class GetSavingGoalsHandler:
    def __init__(
        self,
        goal_repository: SavingGoalRepository,
        account_repository: AccountRepository,
    ):
        self.goal_repository = goal_repository
        self.account_repository = account_repository

    async def handle(self, query: GetSavingGoalsQuery) -> list[SavingGoalResponseDTO]:
        goals = await self.goal_repository.get_by_user(
            user_id=query.user_id, active_only=query.active_only
        )
        if not goals:
            return []

        account_ids = list({g.account_id for g in goals if g.account_id is not None})
        accounts = await self.account_repository.get_bulk_by_ids(
            account_ids=account_ids
        )
        accounts_map = {acc.id: acc for acc in accounts}

        result = []
        for goal in goals:
            account = accounts_map.get(goal.account_id)
            if not account:
                continue
            result.append(
                SavingGoalResponseDTO.from_entity(
                    goal=goal,
                    account_name=account.name,
                    account_uuid=account.uuid,
                    current_amount=account.current_balance.amount,
                )
            )
        return result

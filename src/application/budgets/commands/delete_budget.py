from dataclasses import dataclass

from domain.repositories.budget_repository import BudgetRepository
from domain.repositories.unit_of_work import AbstractUnitOfWork
from shared.exceptions.domain import BudgetNotFoundError


@dataclass
class DeleteBudgetCommand:
    budget_uuid: str
    user_id: int


class DeleteBudgetHandler:
    def __init__(
        self,
        budget_repository: BudgetRepository,
        uow: AbstractUnitOfWork,
    ):
        self.budget_repository = budget_repository
        self.uow = uow

    async def handle(self, command: DeleteBudgetCommand) -> bool:
        async with self.uow:
            deleted = await self.budget_repository.delete(
                uuid=command.budget_uuid, user_id=command.user_id
            )
            await self.uow.commit()

        if not deleted:
            raise BudgetNotFoundError(command.budget_uuid)

        return True

from dataclasses import dataclass

from domain.repositories.recurring_income_repository import RecurringIncomeRepository
from domain.repositories.unit_of_work import AbstractUnitOfWork
from shared.exceptions.domain import (
    RecurringIncomeNotFoundError,
)


@dataclass
class DeleteRecurringIncomeCommand:
    income_uuid: str
    user_id: int


class DeleteRecurringIncomeHandler:
    def __init__(
        self,
        recurring_income_repository: RecurringIncomeRepository,
        uow: AbstractUnitOfWork,
    ):
        self.recurring_income_repository = recurring_income_repository
        self.uow = uow

    async def handle(self, command: DeleteRecurringIncomeCommand):
        income = await self.recurring_income_repository.get_by_uuid_and_user_id(
            income_uuid=command.income_uuid, user_id=command.user_id
        )

        if not income:
            raise RecurringIncomeNotFoundError(command.income_uuid)

        async with self.uow:
            deleted = await self.recurring_income_repository.delete(
                uuid=command.income_uuid, user_id=command.user_id
            )
            await self.uow.commit()

        if not deleted:
            raise RecurringIncomeNotFoundError(command.income_uuid)

        return True

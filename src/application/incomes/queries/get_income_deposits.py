from dataclasses import dataclass
from typing import List

from domain.repositories.recurring_income_repository import RecurringIncomeRepository
from domain.repositories.income_deposit_repository import IncomeDepositRepository
from application.dto.recurring_income_dto import IncomeDepositResponseDTO

from shared.exceptions.domain import RecurringIncomeNotFoundError


@dataclass
class GetIncomeDepositsQuery:
    income_uuid: str
    user_id: int
    limit: int = 100
    offset: int = 0


class GetIncomeDepositsHandler:
    def __init__(
        self,
        recurring_income_repository: RecurringIncomeRepository,
        income_deposit_repository: IncomeDepositRepository,
    ):
        self.recurring_income_repository = recurring_income_repository
        self.income_deposit_repository = income_deposit_repository

    async def handle(
        self, query: GetIncomeDepositsQuery
    ) -> List[IncomeDepositResponseDTO]:
        income = await self.recurring_income_repository.get_by_uuid_and_user_id(
            income_uuid=query.income_uuid, user_id=query.user_id
        )

        if not income:
            raise RecurringIncomeNotFoundError(query.income_uuid)

        deposits = await self.income_deposit_repository.get_by_income(
            recurring_income_id=income.id,
            limit=query.limit,
            offset=query.offset,
        )

        return [
            IncomeDepositResponseDTO.from_entity(deposit, transaction_uuid)
            for deposit, transaction_uuid in deposits
        ]

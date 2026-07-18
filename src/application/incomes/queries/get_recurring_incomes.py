from dataclasses import dataclass
from typing import Optional, List

from domain.repositories.recurring_income_repository import RecurringIncomeRepository
from domain.repositories.account_repository import AccountRepository
from domain.repositories.category_repository import CategoryRepository

from application.dto.recurring_income_dto import RecurringIncomeResponseDTO


@dataclass
class GetRecurringIncomesQuery:
    user_id: int
    account_uuid: Optional[str] = None
    category_id: Optional[int] = None
    active_only: bool = False
    limit: int = 100
    offset: int = 0


class GetRecurringIncomesHandler:
    def __init__(
        self,
        recurring_income_repository: RecurringIncomeRepository,
        account_repository: AccountRepository,
        category_repository: CategoryRepository,
    ):
        self.recurring_income_repository = recurring_income_repository
        self.account_repository = account_repository
        self.category_repository = category_repository

    async def handle(
        self, query: GetRecurringIncomesQuery
    ) -> List[RecurringIncomeResponseDTO]:
        if query.account_uuid:
            incomes = await self.recurring_income_repository.get_by_account(
                account_uuid=query.account_uuid,
                user_id=query.user_id,
                limit=query.limit,
                offset=query.offset,
            )
        elif query.category_id:
            incomes = await self.recurring_income_repository.get_by_category(
                category_id=query.category_id, user_id=query.user_id
            )
        else:
            incomes = await self.recurring_income_repository.get_by_user(
                user_id=query.user_id,
                active_only=query.active_only,
            )

        response_dtos = []
        for income in incomes:
            account = await self.account_repository.get_by_id(income.account_id)
            account_uuid = account.uuid if account else None
            account_name = account.name if account else None

            category = (
                await self.category_repository.get_by_id(income.category_id)
                if income.category_id
                else None
            )
            category_name = category.name if category else None

            dto = RecurringIncomeResponseDTO.from_entity(
                income, account_uuid, account_name, category_name
            )
            response_dtos.append(dto)

        return response_dtos

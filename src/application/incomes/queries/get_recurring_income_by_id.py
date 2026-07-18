from dataclasses import dataclass
from typing import Optional

from domain.repositories.account_repository import AccountRepository
from domain.repositories.category_repository import CategoryRepository
from domain.repositories.recurring_income_repository import RecurringIncomeRepository
from application.dto.recurring_income_dto import RecurringIncomeResponseDTO

from shared.exceptions.domain import RecurringIncomeNotFoundError


@dataclass
class GetRecurringIncomeByIdQuery:
    income_uuid: str
    user_id: int


class GetRecurringIncomeByIdHandler:
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
        self, query: GetRecurringIncomeByIdQuery
    ) -> Optional[RecurringIncomeResponseDTO]:
        income = await self.recurring_income_repository.get_by_uuid_and_user_id(
            income_uuid=query.income_uuid, user_id=query.user_id
        )

        if not income:
            raise RecurringIncomeNotFoundError(query.income_uuid)

        account = await self.account_repository.get_by_id(income.account_id)
        account_uuid = account.uuid if account else None
        account_name = account.name if account else None

        category = (
            await self.category_repository.get_by_id(income.category_id)
            if income.category_id
            else None
        )
        category_name = category.name if category else None

        return RecurringIncomeResponseDTO.from_entity(
            income=income,
            account_uuid=account_uuid,
            account_name=account_name,
            category_name=category_name,
        )

from dataclasses import dataclass

from application.dto.budget_dto import BudgetResponseDTO, CreateBudgetDTO
from domain.entities.budget import Budget
from domain.repositories.budget_repository import BudgetRepository
from domain.repositories.category_repository import CategoryRepository
from domain.repositories.unit_of_work import AbstractUnitOfWork
from domain.repositories.user_repository import UserRepository
from shared.exceptions.domain import CategoryNotFoundError, UserNotFoundError


@dataclass
class CreateBudgetCommand:
    dto: CreateBudgetDTO


class CreateBudgetHandler:
    def __init__(
        self,
        budget_repository: BudgetRepository,
        user_repository: UserRepository,
        category_repository: CategoryRepository,
        uow: AbstractUnitOfWork,
    ):
        self.budget_repository = budget_repository
        self.user_repository = user_repository
        self.category_repository = category_repository
        self.uow = uow

    async def handle(self, command: CreateBudgetCommand) -> BudgetResponseDTO:
        dto = command.dto

        user = await self.user_repository.get_by_id(dto.user_id)
        if not user or not user.is_active:
            raise UserNotFoundError()

        category_name: str | None = None
        if dto.category_id is not None:
            category = await self.category_repository.get_by_id(dto.category_id)
            if not category:
                raise CategoryNotFoundError(dto.category_id)
            category_name = category.name

        budget = Budget.create_new(
            user_id=dto.user_id,
            category_id=dto.category_id,
            name=dto.name,
            limit_amount=dto.limit_amount,
            period=dto.period,
            start_date=dto.start_date,
            end_date=dto.end_date,
            alert_percentage=dto.alert_percentage,
        )

        async with self.uow:
            saved_budget = await self.budget_repository.create(budget)
            await self.uow.commit()

        return BudgetResponseDTO.from_entity(saved_budget, category_name=category_name)

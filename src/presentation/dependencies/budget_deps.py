from fastapi import Depends

from application.budgets.commands.create_budget import CreateBudgetHandler
from application.budgets.commands.update_budget import UpdateBudgetHandler
from application.budgets.commands.delete_budget import DeleteBudgetHandler
from application.budgets.commands.state_budget import StateBudgetHandler
from application.budgets.queries.get_budgets import GetBudgetsHandler
from application.budgets.queries.get_budget_by_id import GetBudgetByIdHandler
from application.budgets.queries.get_budget_progress import GetBudgetProgressHandler
from domain.repositories.unit_of_work import AbstractUnitOfWork
from infrastructure.database.repositories.sqlalchemy_budget_repository import (
    SQLAlchemyBudgetRepository,
)
from infrastructure.database.repositories.sqlalchemy_category_repository import (
    SQLAlchemyCategoryRepository,
)
from infrastructure.database.repositories.sqlalchemy_user_repository import (
    SQLAlchemyUserRepository,
)
from presentation.dependencies.repositories import (
    get_budget_repository,
    get_category_repository,
    get_user_repository,
    get_unit_of_work_repository,
)


def get_create_budget_handler(
    budget_repo: SQLAlchemyBudgetRepository = Depends(get_budget_repository),
    user_repo: SQLAlchemyUserRepository = Depends(get_user_repository),
    category_repo: SQLAlchemyCategoryRepository = Depends(get_category_repository),
    uow: AbstractUnitOfWork = Depends(get_unit_of_work_repository),
) -> CreateBudgetHandler:
    return CreateBudgetHandler(budget_repo, user_repo, category_repo, uow)


def get_update_budget_handler(
    budget_repo: SQLAlchemyBudgetRepository = Depends(get_budget_repository),
    category_repo: SQLAlchemyCategoryRepository = Depends(get_category_repository),
    uow: AbstractUnitOfWork = Depends(get_unit_of_work_repository),
) -> UpdateBudgetHandler:
    return UpdateBudgetHandler(budget_repo, category_repo, uow)


def get_delete_budget_handler(
    budget_repo: SQLAlchemyBudgetRepository = Depends(get_budget_repository),
    uow: AbstractUnitOfWork = Depends(get_unit_of_work_repository),
) -> DeleteBudgetHandler:
    return DeleteBudgetHandler(budget_repo, uow)


def get_state_budget_handler(
    budget_repo: SQLAlchemyBudgetRepository = Depends(get_budget_repository),
    category_repo: SQLAlchemyCategoryRepository = Depends(get_category_repository),
    uow: AbstractUnitOfWork = Depends(get_unit_of_work_repository),
) -> StateBudgetHandler:
    return StateBudgetHandler(budget_repo, category_repo, uow)


def get_budgets_handler(
    budget_repo: SQLAlchemyBudgetRepository = Depends(get_budget_repository),
    category_repo: SQLAlchemyCategoryRepository = Depends(get_category_repository),
) -> GetBudgetsHandler:
    return GetBudgetsHandler(budget_repo, category_repo)


def get_budget_by_id_handler(
    budget_repo: SQLAlchemyBudgetRepository = Depends(get_budget_repository),
    category_repo: SQLAlchemyCategoryRepository = Depends(get_category_repository),
) -> GetBudgetByIdHandler:
    return GetBudgetByIdHandler(budget_repo, category_repo)


def get_budget_progress_handler(
    budget_repo: SQLAlchemyBudgetRepository = Depends(get_budget_repository),
    category_repo: SQLAlchemyCategoryRepository = Depends(get_category_repository),
) -> GetBudgetProgressHandler:
    return GetBudgetProgressHandler(budget_repo, category_repo)

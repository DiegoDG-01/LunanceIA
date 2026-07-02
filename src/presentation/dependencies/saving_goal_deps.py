from fastapi.params import Depends

from application.goals.commands.create_saving_goal import CreateSavingGoalHandler
from application.goals.commands.delete_saving_goal import DeleteSavingGoalHandler
from application.goals.commands.state_saving_goal import StateSavingGoalHandler
from application.goals.commands.update_saving_goal import UpdateSavingGoalHandler
from application.goals.queries.get_saving_goal_by_id import GetSavingGoalByIdHandler
from application.goals.queries.get_saving_goals import GetSavingGoalsHandler
from infrastructure.database.repositories.sqlalchemy_account_repository import SQLAlchemyAccountRepository
from infrastructure.database.repositories.sqlalchemy_saving_goal_repository import SQLAlchemySavingGoalRepository
from infrastructure.database.repositories.sqlalchemy_user_repository import SQLAlchemyUserRepository
from domain.repositories.unit_of_work import AbstractUnitOfWork
from presentation.dependencies.repositories import (
    get_user_repository,
    get_account_repository,
    get_saving_goals_repository,
    get_unit_of_work_repository,
)


def get_create_saving_goal_handler(
    user_respo: SQLAlchemyUserRepository = Depends(get_user_repository),
    account_repo: SQLAlchemyAccountRepository = Depends(get_account_repository),
    goal_repo: SQLAlchemySavingGoalRepository = Depends(get_saving_goals_repository),
    uow: AbstractUnitOfWork = Depends(get_unit_of_work_repository)
) -> CreateSavingGoalHandler:
    return CreateSavingGoalHandler(user_respo, account_repo, goal_repo, uow)

def get_update_saving_goal_handler(
    goal_repo: SQLAlchemySavingGoalRepository = Depends(get_saving_goals_repository),
    accounts_repo: SQLAlchemyAccountRepository = Depends(get_account_repository),
    uow: AbstractUnitOfWork = Depends(get_unit_of_work_repository)
) -> UpdateSavingGoalHandler:
    return UpdateSavingGoalHandler(goal_repo, accounts_repo, uow)


def get_delete_saving_goal_handler(
    goal_repo: SQLAlchemySavingGoalRepository = Depends(get_saving_goals_repository),
    uow: AbstractUnitOfWork = Depends(get_unit_of_work_repository)
) -> DeleteSavingGoalHandler:
    return DeleteSavingGoalHandler(goal_repo, uow)

def get_state_saving_goal_handler(
    goal_repo: SQLAlchemySavingGoalRepository = Depends(get_saving_goals_repository),
    account_repo: SQLAlchemyAccountRepository = Depends(get_account_repository),
    uow: AbstractUnitOfWork = Depends(get_unit_of_work_repository)
) -> StateSavingGoalHandler:
    return StateSavingGoalHandler(goal_repo, account_repo, uow)

def get_saving_goals_handler(
    goal_repo: SQLAlchemySavingGoalRepository = Depends(get_saving_goals_repository),
    account_repo: SQLAlchemyAccountRepository = Depends(get_account_repository),
) -> GetSavingGoalsHandler:
    return GetSavingGoalsHandler(goal_repo, account_repo)

def get_saving_goals_by_id_handler(
    goal_repo: SQLAlchemySavingGoalRepository = Depends(get_saving_goals_repository),
    account_repo: SQLAlchemyAccountRepository = Depends(get_account_repository),
) -> GetSavingGoalByIdHandler:
    return GetSavingGoalByIdHandler(goal_repo, account_repo)
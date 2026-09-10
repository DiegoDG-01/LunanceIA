from fastapi import Depends

from application.incomes.commands.create_recurring_income import (
    CreateRecurringIncomeHandler,
)
from application.incomes.commands.delete_recurring_income import (
    DeleteRecurringIncomeHandler,
)
from application.incomes.commands.state_recurring_income import (
    StateRecurringIncomeHandler,
)
from application.incomes.commands.update_recurring_income import (
    UpdateRecurringIncomeHandler,
)
from application.incomes.queries.get_income_deposits import GetIncomeDepositsHandler
from application.incomes.queries.get_recurring_income_by_id import (
    GetRecurringIncomeByIdHandler,
)
from application.incomes.queries.get_recurring_incomes import (
    GetRecurringIncomesHandler,
)
from domain.repositories.unit_of_work import AbstractUnitOfWork
from infrastructure.database.repositories.sqlalchemy_account_repository import (
    SQLAlchemyAccountRepository,
)
from infrastructure.database.repositories.sqlalchemy_category_repository import (
    SQLAlchemyCategoryRepository,
)
from infrastructure.database.repositories.sqlalchemy_income_deposit_repository import (
    SQLAlchemyIncomeDepositRepository,
)
from infrastructure.database.repositories.sqlalchemy_recurring_income_repository import (
    SQLAlchemyRecurringIncomeRepository,
)
from infrastructure.database.repositories.sqlalchemy_user_repository import (
    SQLAlchemyUserRepository,
)
from presentation.dependencies.repositories import (
    get_account_repository,
    get_category_repository,
    get_income_deposit_repository,
    get_recurring_income_repository,
    get_unit_of_work_repository,
    get_user_repository,
)


def get_create_recurring_income_handler(
    income_repo: SQLAlchemyRecurringIncomeRepository = Depends(
        get_recurring_income_repository
    ),
    user_repo: SQLAlchemyUserRepository = Depends(get_user_repository),
    account_repo: SQLAlchemyAccountRepository = Depends(get_account_repository),
    category_repo: SQLAlchemyCategoryRepository = Depends(get_category_repository),
    uow: AbstractUnitOfWork = Depends(get_unit_of_work_repository),
) -> CreateRecurringIncomeHandler:
    return CreateRecurringIncomeHandler(
        income_repo, user_repo, account_repo, category_repo, uow
    )


def get_update_recurring_income_handler(
    income_repo: SQLAlchemyRecurringIncomeRepository = Depends(
        get_recurring_income_repository
    ),
    category_repo: SQLAlchemyCategoryRepository = Depends(get_category_repository),
    account_repo: SQLAlchemyAccountRepository = Depends(get_account_repository),
    uow: AbstractUnitOfWork = Depends(get_unit_of_work_repository),
) -> UpdateRecurringIncomeHandler:
    return UpdateRecurringIncomeHandler(income_repo, category_repo, account_repo, uow)


def get_state_recurring_income_handler(
    income_repo: SQLAlchemyRecurringIncomeRepository = Depends(
        get_recurring_income_repository
    ),
    category_repo: SQLAlchemyCategoryRepository = Depends(get_category_repository),
    account_repo: SQLAlchemyAccountRepository = Depends(get_account_repository),
    uow: AbstractUnitOfWork = Depends(get_unit_of_work_repository),
) -> StateRecurringIncomeHandler:
    return StateRecurringIncomeHandler(income_repo, category_repo, account_repo, uow)


def get_delete_recurring_income_handler(
    income_repo: SQLAlchemyRecurringIncomeRepository = Depends(
        get_recurring_income_repository
    ),
    uow: AbstractUnitOfWork = Depends(get_unit_of_work_repository),
) -> DeleteRecurringIncomeHandler:
    return DeleteRecurringIncomeHandler(income_repo, uow)


def get_recurring_incomes_handler(
    income_repo: SQLAlchemyRecurringIncomeRepository = Depends(
        get_recurring_income_repository
    ),
    account_repo: SQLAlchemyAccountRepository = Depends(get_account_repository),
    category_repo: SQLAlchemyCategoryRepository = Depends(get_category_repository),
) -> GetRecurringIncomesHandler:
    return GetRecurringIncomesHandler(income_repo, account_repo, category_repo)


def get_recurring_income_by_id_handler(
    income_repo: SQLAlchemyRecurringIncomeRepository = Depends(
        get_recurring_income_repository
    ),
    account_repo: SQLAlchemyAccountRepository = Depends(get_account_repository),
    category_repo: SQLAlchemyCategoryRepository = Depends(get_category_repository),
) -> GetRecurringIncomeByIdHandler:
    return GetRecurringIncomeByIdHandler(income_repo, account_repo, category_repo)


def get_income_deposits_handler(
    income_repo: SQLAlchemyRecurringIncomeRepository = Depends(
        get_recurring_income_repository
    ),
    deposit_repo: SQLAlchemyIncomeDepositRepository = Depends(
        get_income_deposit_repository
    ),
) -> GetIncomeDepositsHandler:
    return GetIncomeDepositsHandler(income_repo, deposit_repo)

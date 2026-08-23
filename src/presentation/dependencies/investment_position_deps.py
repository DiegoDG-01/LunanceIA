from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.connection import get_db
from infrastructure.database.repositories.sqlalchemy_account_repository import (
    SQLAlchemyAccountRepository,
)
from infrastructure.database.repositories.sqlalchemy_investment_position_repository import (
    SQLAlchemyInvestmentPositionRepository,
)
from infrastructure.database.repositories.sqlalchemy_transaction_repository import (
    SQLAlchemyTransactionRepository,
)
from infrastructure.database.repositories.sqlalchemy_user_repository import (
    SQLAlchemyUserRepository,
)
from infrastructure.database.repositories.sqlalchemy_unit_of_work import (
    SQLAlchemyUnitOfWork,
)

from application.investments.commands.create_position import CreatePositionHandler
from application.investments.commands.deposit_to_position import (
    DepositToPositionHandler,
)
from application.investments.commands.withdraw_from_position import (
    WithdrawFromPositionHandler,
)
from application.investments.commands.liquidate_position import (
    LiquidatePositionHandler,
)
from application.investments.commands.update_position import UpdatePositionHandler
from application.investments.services.position_overflow import PositionOverflowService
from application.investments.queries.list_positions import ListPositionsHandler
from application.investments.queries.get_position import GetPositionHandler
from application.investments.queries.get_position_yields import (
    GetPositionYieldsHandler,
)
from application.investments.queries.get_position_projections import (
    GetPositionProjectionsHandler,
)

from presentation.dependencies.repositories import (
    get_account_repository,
    get_notification_repository,
    get_transaction_repository,
    get_user_repository,
    get_unit_of_work_repository,
)
from infrastructure.database.repositories.sqlalchemy_notification_repository import (
    SQLAlchemyNotificationRepository,
)
from presentation.dependencies.investment_yield_deps import (
    get_investment_yield_repository,
)
from infrastructure.database.repositories.sqlalchemy_investment_yield_repository import (
    SQLAlchemyInvestmentYieldRepository,
)


def get_investment_position_repository(
    db: AsyncSession = Depends(get_db),
) -> SQLAlchemyInvestmentPositionRepository:
    return SQLAlchemyInvestmentPositionRepository(db)


def get_position_overflow_service(
    position_repo: SQLAlchemyInvestmentPositionRepository = Depends(
        get_investment_position_repository
    ),
) -> PositionOverflowService:
    return PositionOverflowService(position_repository=position_repo)


def get_create_position_handler(
    user_repo: SQLAlchemyUserRepository = Depends(get_user_repository),
    account_repo: SQLAlchemyAccountRepository = Depends(get_account_repository),
    position_repo: SQLAlchemyInvestmentPositionRepository = Depends(
        get_investment_position_repository
    ),
    transaction_repo: SQLAlchemyTransactionRepository = Depends(
        get_transaction_repository
    ),
    overflow_service: PositionOverflowService = Depends(get_position_overflow_service),
    uow: SQLAlchemyUnitOfWork = Depends(get_unit_of_work_repository),
) -> CreatePositionHandler:
    return CreatePositionHandler(
        user_repository=user_repo,
        account_repository=account_repo,
        position_repository=position_repo,
        transaction_repository=transaction_repo,
        overflow_service=overflow_service,
        uow=uow,
    )


def get_update_position_handler(
    user_repo: SQLAlchemyUserRepository = Depends(get_user_repository),
    account_repo: SQLAlchemyAccountRepository = Depends(get_account_repository),
    position_repo: SQLAlchemyInvestmentPositionRepository = Depends(
        get_investment_position_repository
    ),
    transaction_repo: SQLAlchemyTransactionRepository = Depends(
        get_transaction_repository
    ),
    overflow_service: PositionOverflowService = Depends(get_position_overflow_service),
    uow: SQLAlchemyUnitOfWork = Depends(get_unit_of_work_repository),
) -> UpdatePositionHandler:
    return UpdatePositionHandler(
        user_repository=user_repo,
        account_repository=account_repo,
        position_repository=position_repo,
        transaction_repository=transaction_repo,
        overflow_service=overflow_service,
        uow=uow,
    )


def get_deposit_to_position_handler(
    user_repo: SQLAlchemyUserRepository = Depends(get_user_repository),
    account_repo: SQLAlchemyAccountRepository = Depends(get_account_repository),
    position_repo: SQLAlchemyInvestmentPositionRepository = Depends(
        get_investment_position_repository
    ),
    transaction_repo: SQLAlchemyTransactionRepository = Depends(
        get_transaction_repository
    ),
    overflow_service: PositionOverflowService = Depends(get_position_overflow_service),
    uow: SQLAlchemyUnitOfWork = Depends(get_unit_of_work_repository),
) -> DepositToPositionHandler:
    return DepositToPositionHandler(
        user_repository=user_repo,
        account_repository=account_repo,
        position_repository=position_repo,
        transaction_repository=transaction_repo,
        overflow_service=overflow_service,
        uow=uow,
    )


def get_withdraw_from_position_handler(
    user_repo: SQLAlchemyUserRepository = Depends(get_user_repository),
    account_repo: SQLAlchemyAccountRepository = Depends(get_account_repository),
    position_repo: SQLAlchemyInvestmentPositionRepository = Depends(
        get_investment_position_repository
    ),
    transaction_repo: SQLAlchemyTransactionRepository = Depends(
        get_transaction_repository
    ),
    overflow_service: PositionOverflowService = Depends(get_position_overflow_service),
    uow: SQLAlchemyUnitOfWork = Depends(get_unit_of_work_repository),
) -> WithdrawFromPositionHandler:
    return WithdrawFromPositionHandler(
        user_repository=user_repo,
        account_repository=account_repo,
        position_repository=position_repo,
        transaction_repository=transaction_repo,
        overflow_service=overflow_service,
        uow=uow,
    )


def get_liquidate_position_handler(
    user_repo: SQLAlchemyUserRepository = Depends(get_user_repository),
    account_repo: SQLAlchemyAccountRepository = Depends(get_account_repository),
    position_repo: SQLAlchemyInvestmentPositionRepository = Depends(
        get_investment_position_repository
    ),
    transaction_repo: SQLAlchemyTransactionRepository = Depends(
        get_transaction_repository
    ),
    notification_repo: SQLAlchemyNotificationRepository = Depends(
        get_notification_repository
    ),
    uow: SQLAlchemyUnitOfWork = Depends(get_unit_of_work_repository),
) -> LiquidatePositionHandler:
    return LiquidatePositionHandler(
        user_repository=user_repo,
        account_repository=account_repo,
        position_repository=position_repo,
        transaction_repository=transaction_repo,
        notification_repository=notification_repo,
        uow=uow,
    )


def get_list_positions_handler(
    account_repo: SQLAlchemyAccountRepository = Depends(get_account_repository),
    position_repo: SQLAlchemyInvestmentPositionRepository = Depends(
        get_investment_position_repository
    ),
) -> ListPositionsHandler:
    return ListPositionsHandler(
        account_repository=account_repo, position_repository=position_repo
    )


def get_position_handler(
    account_repo: SQLAlchemyAccountRepository = Depends(get_account_repository),
    position_repo: SQLAlchemyInvestmentPositionRepository = Depends(
        get_investment_position_repository
    ),
    overflow_service: PositionOverflowService = Depends(get_position_overflow_service),
) -> GetPositionHandler:
    return GetPositionHandler(
        account_repository=account_repo,
        position_repository=position_repo,
        overflow_service=overflow_service,
    )


def get_position_yields_handler(
    position_repo: SQLAlchemyInvestmentPositionRepository = Depends(
        get_investment_position_repository
    ),
    yield_repo: SQLAlchemyInvestmentYieldRepository = Depends(
        get_investment_yield_repository
    ),
) -> GetPositionYieldsHandler:
    return GetPositionYieldsHandler(
        position_repository=position_repo, investment_yield_repository=yield_repo
    )


def get_position_projections_handler(
    position_repo: SQLAlchemyInvestmentPositionRepository = Depends(
        get_investment_position_repository
    ),
) -> GetPositionProjectionsHandler:
    return GetPositionProjectionsHandler(position_repository=position_repo)

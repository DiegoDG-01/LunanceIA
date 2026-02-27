from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.connection import get_db
from application.investments.queries.get_investment_yields import (
    GetInvestmentYieldsHandler,
)
from application.investments.queries.get_investment_projections import (
    GetInvestmentProjectionsHandler,
)

# from domain.entities.investment_yield import InvestmentYield
# from domain.repositories.investment_yield_repository import InvestmentYieldRepository
from infrastructure.database.repositories.sqlalchemy_account_repository import (
    SQLAlchemyAccountRepository,
)
from infrastructure.database.repositories.sqlalchemy_investment_yield_repository import (
    SQLAlchemyInvestmentYieldRepository,
)
from infrastructure.database.repositories.sqlalchemy_investment_card_repository import (
    SQLAlchemyInvestmentSettingsRepository,
)
# from presentation.api.v2.endpoints.investment_yield import get_investment_yields

from presentation.dependencies.repositories import (
    get_account_repository,
    get_investment_settings_repository,
)


def get_investment_yield_repository(
    db: AsyncSession = Depends(get_db),
) -> SQLAlchemyInvestmentYieldRepository:
    return SQLAlchemyInvestmentYieldRepository(db)


def get_investment_yields_handler(
    account_repo: SQLAlchemyAccountRepository = Depends(get_account_repository),
    yield_repo: SQLAlchemyInvestmentYieldRepository = Depends(
        get_investment_yield_repository
    ),
) -> GetInvestmentYieldsHandler:
    return GetInvestmentYieldsHandler(account_repo, yield_repo)


def get_investment_projections_handler(
    account_repo: SQLAlchemyAccountRepository = Depends(get_account_repository),
    settings_repo: SQLAlchemyInvestmentSettingsRepository = Depends(
        get_investment_settings_repository
    ),
) -> GetInvestmentProjectionsHandler:
    return GetInvestmentProjectionsHandler(
        account_repository=account_repo,
        investment_card_settings_repository=settings_repo,
    )

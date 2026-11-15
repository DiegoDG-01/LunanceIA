from fastapi import Depends

from application.dashboard.queries.get_dashboard_summary import (
    GetDashboardSummaryHandler,
)
from application.dashboard.queries.get_mobile_dashboard_summary import (
    GetMobileDashboardSummaryHandler,
)
from application.securities.queries.portfolio import PortfolioQueries
from infrastructure.database.repositories.sqlalchemy_dashboard_repository import (
    SQLAlchemyDashboardRepository,
)
from presentation.dependencies.repositories import get_dashboard_repository
from presentation.dependencies.security_deps import get_portfolio_queries


def get_dashboard_summary_handler(
    dashboard_repository: SQLAlchemyDashboardRepository = Depends(
        get_dashboard_repository
    ),
    portfolio_queries: PortfolioQueries = Depends(get_portfolio_queries),
) -> GetDashboardSummaryHandler:
    return GetDashboardSummaryHandler(dashboard_repository, portfolio_queries)


def get_mobile_dashboard_summary_handler(
    dashboard_mobile_repository: SQLAlchemyDashboardRepository = Depends(
        get_dashboard_repository
    ),
    portfolio_queries: PortfolioQueries = Depends(get_portfolio_queries),
) -> GetMobileDashboardSummaryHandler:
    return GetMobileDashboardSummaryHandler(
        dashboard_mobile_repository, portfolio_queries
    )

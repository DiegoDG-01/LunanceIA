from fastapi import Depends

from application.dashboard.queries.get_dashboard_summary import (
    GetDashboardSummaryHandler,
)
from application.dashboard.queries.get_mobile_dashboard_summary import (
    GetMobileDashboardSummaryHandler,
)
from infrastructure.database.repositories.sqlalchemy_dashboard_repository import (
    SQLAlchemyDashboardRepository,
)
from presentation.dependencies.repositories import get_dashboard_repository


def get_dashboard_summary_handler(
    dashboard_repository: SQLAlchemyDashboardRepository = Depends(
        get_dashboard_repository
    ),
) -> GetDashboardSummaryHandler:
    return GetDashboardSummaryHandler(dashboard_repository)


def get_mobile_dashboard_summary_handler(
    dashboard_mobile_repository: SQLAlchemyDashboardRepository = Depends(
        get_dashboard_repository
    ),
) -> GetMobileDashboardSummaryHandler:
    return GetMobileDashboardSummaryHandler(dashboard_mobile_repository)

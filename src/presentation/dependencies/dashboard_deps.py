from fastapi import Depends

from application.dashboard.queries.get_dashboard_summary import (
    GetDashboardSummaryHandler,
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

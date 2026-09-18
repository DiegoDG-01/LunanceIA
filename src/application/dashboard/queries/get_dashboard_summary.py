from dataclasses import dataclass

from application.dashboard.dashboard_repository import DashboardRepository
from application.dashboard.read_models import DashboardSummary


@dataclass
class GetDashboardSummaryQuery:
    user_id: int


class GetDashboardSummaryHandler:
    def __init__(self, dashboard_repository: DashboardRepository):
        self.dashboard_repository = dashboard_repository

    async def handle(self, query: GetDashboardSummaryQuery) -> DashboardSummary | None:
        return await self.dashboard_repository.get_dashboard_summary(query.user_id)

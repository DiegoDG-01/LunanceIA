from dataclasses import dataclass

from application.dashboard.dashboard_repository import DashboardRepository
from application.dashboard.read_models import MobileDashboardSummary


@dataclass
class GetMobileDashboardSummaryQuery:
    user_id: int


class GetMobileDashboardSummaryHandler:
    def __init__(self, dashboard_repository: DashboardRepository):
        self.dashboard_repository = dashboard_repository

    async def handle(
        self, query: GetMobileDashboardSummaryQuery
    ) -> MobileDashboardSummary | None:
        return await self.dashboard_repository.get_mobile_dashboard_summary(
            query.user_id
        )

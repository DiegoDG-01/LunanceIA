from dataclasses import dataclass

from domain.entities.dashboard import MobileDashboardSummary
from domain.repositories.dashboard_repository import DashboardRepository


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

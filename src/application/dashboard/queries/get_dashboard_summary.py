from dataclasses import dataclass
from typing import Optional
from domain.repositories.dashboard_repository import DashboardRepository
from domain.entities.dashboard import DashboardSummary


@dataclass
class GetDashboardSummaryQuery:
    user_uuid: str
    user_id: int


class GetDashboardSummaryHandler:
    def __init__(self, dashboard_repository: DashboardRepository):
        self.dashboard_repository = dashboard_repository

    async def handle(
        self, query: GetDashboardSummaryQuery
    ) -> Optional[DashboardSummary]:
        return await self.dashboard_repository.get_dashboard_summary(
            query.user_uuid, query.user_id
        )

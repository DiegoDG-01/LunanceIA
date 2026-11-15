from dataclasses import dataclass, replace

from application.dashboard.dashboard_repository import DashboardRepository
from application.dashboard.read_models import DashboardSummary
from application.securities.queries.portfolio import PortfolioQueries


@dataclass
class GetDashboardSummaryQuery:
    user_id: int


class GetDashboardSummaryHandler:
    def __init__(
        self,
        dashboard_repository: DashboardRepository,
        portfolio_queries: PortfolioQueries | None = None,
    ):
        self.dashboard_repository = dashboard_repository
        self.portfolio_queries = portfolio_queries

    async def handle(self, query: GetDashboardSummaryQuery) -> DashboardSummary | None:
        summary = await self.dashboard_repository.get_dashboard_summary(query.user_id)
        if summary is None or self.portfolio_queries is None:
            return summary
        return replace(
            summary, net_worth=await self.portfolio_queries.summary(query.user_id)
        )

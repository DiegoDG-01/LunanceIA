from abc import ABC, abstractmethod

from application.dashboard.read_models import DashboardSummary, MobileDashboardSummary


class DashboardRepository(ABC):
    @abstractmethod
    async def get_dashboard_summary(self, user_id: int) -> DashboardSummary | None:
        """
        Get dashboard summary for a user.
        """

    @abstractmethod
    async def get_mobile_dashboard_summary(
        self, user_id: int
    ) -> MobileDashboardSummary | None:
        """
        Get mobile dashboard summary for a user.
        """

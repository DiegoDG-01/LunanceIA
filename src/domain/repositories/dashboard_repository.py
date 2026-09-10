from abc import ABC, abstractmethod

from domain.entities.dashboard import DashboardSummary


class DashboardRepository(ABC):
    @abstractmethod
    async def get_dashboard_summary(
        self, uuid: str, user_id: int
    ) -> DashboardSummary | None:
        """
        Get dashboard summary for a user.
        """

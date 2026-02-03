from abc import ABC, abstractmethod
from domain.entities.dashboard import DashboardSummary


class DashboardRepository(ABC):
    @abstractmethod
    async def get_dashboard_summary(
        self, user_uuid: str, user_id: int
    ) -> DashboardSummary:
        """
        Get dashboard summary for a user.
        """
        pass

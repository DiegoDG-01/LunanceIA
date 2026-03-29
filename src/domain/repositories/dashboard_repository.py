from abc import ABC, abstractmethod
from typing import Optional
from domain.entities.dashboard import DashboardSummary


class DashboardRepository(ABC):
    @abstractmethod
    async def get_dashboard_summary(
        self, uuid: str, user_id: int
    ) -> Optional[DashboardSummary]:
        """
        Get dashboard summary for a user.
        """
        pass

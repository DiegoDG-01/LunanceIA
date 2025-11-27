from abc import ABC, abstractmethod
from domain.entities.dashboard import DashboardSummary
from typing import List

class DashboardRepository(ABC):

    @abstractmethod
    def get_dashboard_summary(self, user_uuid: str) -> DashboardSummary:
        """
        Get dashboard summary for a user.
        """
        pass
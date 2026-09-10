from abc import ABC, abstractmethod
from datetime import date

from domain.entities.investment_position import InvestmentPosition


class InvestmentPositionRepository(ABC):
    """Investment position (apartado) repository interface"""

    @abstractmethod
    async def create(self, position: InvestmentPosition) -> InvestmentPosition:
        """Create investment position"""

    @abstractmethod
    async def get_by_id(
        self, position_id: int, *, for_update: bool = False
    ) -> InvestmentPosition | None:
        """Get investment position by id"""

    @abstractmethod
    async def get_by_uuid_and_user_id(
        self, position_uuid: str, user_id: int, *, for_update: bool = False
    ) -> InvestmentPosition | None:
        """Get investment position by uuid, scoped to the account owner"""

    @abstractmethod
    async def get_by_account_id(self, account_id: int) -> list[InvestmentPosition]:
        """Get all positions of an account"""

    @abstractmethod
    async def get_active_positions(self) -> list[InvestmentPosition]:
        """Get every active position (daily yield job)"""

    @abstractmethod
    async def get_due_for_maturity(self, as_of: date) -> list[InvestmentPosition]:
        """Get active fixed-term positions with maturity_date <= as_of"""

    @abstractmethod
    async def get_by_overflow_target(
        self, position_id: int, *, for_update: bool = False
    ) -> list[InvestmentPosition]:
        """Get the positions that overflow into this one (liquidation repair)"""

    @abstractmethod
    async def update(self, position: InvestmentPosition) -> InvestmentPosition:
        """Update investment position"""

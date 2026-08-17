from abc import ABC, abstractmethod
from datetime import date
from typing import Optional, List

from domain.entities.investment_position import InvestmentPosition


class InvestmentPositionRepository(ABC):
    """Investment position (apartado) repository interface"""

    @abstractmethod
    async def create(self, position: InvestmentPosition) -> InvestmentPosition:
        """Create investment position"""
        pass

    @abstractmethod
    async def get_by_id(
        self, position_id: int, *, for_update: bool = False
    ) -> Optional[InvestmentPosition]:
        """Get investment position by id"""
        pass

    @abstractmethod
    async def get_by_uuid_and_user_id(
        self, position_uuid: str, user_id: int, *, for_update: bool = False
    ) -> Optional[InvestmentPosition]:
        """Get investment position by uuid, scoped to the account owner"""
        pass

    @abstractmethod
    async def get_by_account_id(self, account_id: int) -> List[InvestmentPosition]:
        """Get all positions of an account"""
        pass

    @abstractmethod
    async def get_active_positions(self) -> List[InvestmentPosition]:
        """Get every active position (daily yield job)"""
        pass

    @abstractmethod
    async def get_due_for_maturity(self, as_of: date) -> List[InvestmentPosition]:
        """Get active fixed-term positions with maturity_date <= as_of"""
        pass

    @abstractmethod
    async def get_by_overflow_target(
        self, position_id: int, *, for_update: bool = False
    ) -> List[InvestmentPosition]:
        """Get the positions that overflow into this one (liquidation repair)"""
        pass

    @abstractmethod
    async def update(self, position: InvestmentPosition) -> InvestmentPosition:
        """Update investment position"""
        pass

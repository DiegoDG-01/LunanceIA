from abc import ABC, abstractmethod

from domain.entities.saving_goal import SavingGoal


class SavingGoalRepository(ABC):
    @abstractmethod
    async def create(self, goal: SavingGoal) -> SavingGoal:
        pass

    @abstractmethod
    async def update(self, goal: SavingGoal) -> SavingGoal:
        pass

    @abstractmethod
    async def delete(self, goal_uuid: str, user_id: int) -> bool:
        pass

    @abstractmethod
    async def get_by_uuid_and_user_id(
        self, goal_uuid: str, user_id: int
    ) -> SavingGoal | None:
        pass

    @abstractmethod
    async def get_by_user(
        self, user_id: int, active_only: bool = True
    ) -> list[SavingGoal]:
        pass

    @abstractmethod
    async def switch_status(self, goal: SavingGoal) -> SavingGoal:
        pass

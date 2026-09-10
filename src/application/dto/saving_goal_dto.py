from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from domain.entities.saving_goal import SavingGoal


@dataclass
class CreateSavingGoalDTO:
    user_id: int
    account_uuid: str
    name: str
    target_amount: Decimal
    target_date: date | None = None
    description: str | None = None


@dataclass
class UpdateSavingGoalDTO:
    name: str | None = None
    target_amount: Decimal | None = None
    target_date: date | None = None
    description: str | None = None


@dataclass
class SavingGoalResponseDTO:
    uuid: str
    account_uuid: str
    account_name: str
    name: str
    target_amount: Decimal
    current_amount: Decimal
    progress_percentage: float
    creation_date: datetime
    target_date: date | None = None
    description: str | None = None
    is_active: bool = True
    completion_date: date | None = None

    @classmethod
    def from_entity(
        cls,
        goal: SavingGoal,
        account_uuid: str,
        account_name: str,
        current_amount: Decimal,
    ):
        return cls(
            uuid=goal.uuid,
            account_uuid=account_uuid,
            account_name=account_name,
            name=goal.name,
            target_amount=goal.target_amount,
            current_amount=current_amount,
            progress_percentage=goal.calculate_progress(current_amount),
            target_date=goal.target_date,
            description=goal.description,
            is_active=goal.is_active,
            completion_date=goal.completion_date,
            creation_date=goal.creation_date,
        )

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from domain.objects.enums import BudgetPeriod


@dataclass
class CreateBudgetDTO:
    user_id: int
    name: str
    limit_amount: Decimal
    period: BudgetPeriod
    start_date: date | None = None
    category_id: int | None = None
    end_date: date | None = None
    alert_percentage: int = 80
    currency: str = "MXN"


@dataclass
class UpdateBudgetDTO:
    name: str | None = None
    limit_amount: Decimal | None = None
    period: BudgetPeriod | None = None
    start_date: date | None = None
    end_date: date | None = None
    alert_percentage: int | None = None
    category_id: int | None = None
    currency: str | None = None


@dataclass
class BudgetResponseDTO:
    uuid: str
    name: str
    category_id: int | None
    category_name: str | None
    limit_amount: Decimal
    currency: str
    period: BudgetPeriod
    start_date: date | None
    end_date: date | None
    is_active: bool
    alert_percentage: int
    creation_date: datetime

    @classmethod
    def from_entity(
        cls, budget, category_name: str | None = None
    ) -> "BudgetResponseDTO":
        return cls(
            uuid=budget.uuid,
            name=budget.name,
            category_id=budget.category_id,
            category_name=category_name,
            limit_amount=budget.limit_amount,
            currency=budget.currency,
            period=budget.period,
            start_date=budget.start_date,
            end_date=budget.end_date,
            is_active=budget.is_active,
            alert_percentage=budget.alert_percentage,
            creation_date=budget.creation_date,
        )


@dataclass
class BudgetProgressDTO:
    uuid: str
    name: str
    category_id: int | None
    category_name: str | None
    limit_amount: Decimal
    currency: str
    spent_amount: Decimal
    remaining_amount: Decimal
    percentage_used: float
    alert_percentage: int
    is_alert_triggered: bool
    is_limit_exceeded: bool
    period: BudgetPeriod
    period_start: date
    period_end: date
    is_active: bool

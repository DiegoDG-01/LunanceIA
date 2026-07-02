from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional, Tuple

from domain.objects.enums import BudgetPeriod


@dataclass
class Budget:
    id: Optional[int]
    uuid: Optional[str]
    user_id: int
    category_id: Optional[int]
    name: str
    limit_amount: Decimal
    period: BudgetPeriod
    start_date: date
    end_date: Optional[date]
    is_active: bool
    alert_percentage: int
    creation_date: Optional[datetime] = None

    @classmethod
    def create_new(
        cls,
        user_id: int,
        category_id: Optional[int],
        name: str,
        limit_amount: Decimal,
        period: BudgetPeriod,
        start_date: date,
        end_date: Optional[date] = None,
        alert_percentage: int = 80,
    ) -> "Budget":
        return cls(
            id=None,
            uuid=None,
            user_id=user_id,
            category_id=category_id,
            name=name,
            limit_amount=limit_amount,
            period=period,
            start_date=start_date,
            end_date=end_date,
            is_active=True,
            alert_percentage=alert_percentage,
            creation_date=datetime.now(timezone.utc),
        )

    def get_current_period_dates(
        self, reference_date: Optional[date] = None
    ) -> Tuple[date, date]:
        """
        Calcula el rango de fechas del periodo actual según el tipo de periodo del presupuesto.

        Returns:
            Tuple[date, date]: (period_start, period_end) — ambas fechas son inclusivas.
        """
        if reference_date is None:
            reference_date = date.today()

        if self.period == BudgetPeriod.MENSUAL:
            period_start = reference_date.replace(day=1)
            if period_start.month == 12:
                period_end = period_start.replace(
                    year=period_start.year + 1, month=1, day=1
                ) - timedelta(days=1)
            else:
                period_end = period_start.replace(
                    month=period_start.month + 1, day=1
                ) - timedelta(days=1)

        elif self.period == BudgetPeriod.SEMANAL:
            period_start = reference_date - timedelta(days=reference_date.weekday())
            period_end = period_start + timedelta(days=6)

        elif self.period == BudgetPeriod.QUINCENAL:
            if reference_date.day <= 15:
                period_start = reference_date.replace(day=1)
                period_end = reference_date.replace(day=15)
            else:
                period_start = reference_date.replace(day=16)
                if period_start.month == 12:
                    period_end = period_start.replace(
                        year=period_start.year + 1, month=1, day=1
                    ) - timedelta(days=1)
                else:
                    period_end = period_start.replace(
                        month=period_start.month + 1, day=1
                    ) - timedelta(days=1)

        elif self.period == BudgetPeriod.TRIMESTRAL:
            quarter = (reference_date.month - 1) // 3
            start_month = quarter * 3 + 1
            end_month = start_month + 2
            period_start = reference_date.replace(month=start_month, day=1)
            if end_month == 12:
                period_end = reference_date.replace(
                    year=reference_date.year + 1, month=1, day=1
                ) - timedelta(days=1)
            else:
                period_end = reference_date.replace(
                    month=end_month + 1, day=1
                ) - timedelta(days=1)

        else:  # BudgetPeriod.ANUAL
            period_start = reference_date.replace(month=1, day=1)
            period_end = reference_date.replace(month=12, day=31)

        return period_start, period_end

    def is_alert_triggered(self, spent_amount: Decimal) -> bool:
        """True si el gasto actual supera el porcentaje de alerta configurado."""
        if self.limit_amount == 0:
            return False
        return (spent_amount / self.limit_amount * 100) >= self.alert_percentage

    def calculate_percentage_used(self, spent_amount: Decimal) -> float:
        """Porcentaje del límite que ya fue utilizado (puede superar 100%)."""
        if self.limit_amount == 0:
            return 0.0
        return float(spent_amount / self.limit_amount * 100)

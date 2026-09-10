import logging
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import cast

from application.dto.investment_position_dto import PositionProjectionResponseDTO
from application.dto.investment_yield_dto import ProjectionDayDTO
from domain.entities.investment_position import InvestmentPosition
from domain.objects.enums import InterestType
from domain.repositories.investment_position_repository import (
    InvestmentPositionRepository,
)
from shared.exceptions.domain import (
    BusinessRuleError,
    FinancialEngineNotAvailableError,
    InvestmentPositionNotFoundError,
    ValidationError,
)

logger = logging.getLogger(__name__)

try:
    from fincore import (  # type: ignore[import]
        FCInvalidDecimalError,
        FinCoreError,
        calculate_projections,  # type: ignore[import]
    )
except ImportError:
    logger.critical(
        "The 'fincore' financial engine is not available. "
        "The application will not be able to calculate projections."
    )
    raise FinancialEngineNotAvailableError()


def project_position(
    position: InvestmentPosition, days: int, today: date
) -> list[ProjectionDayDTO]:
    """Proyección diaria de un apartado usando el motor fincore.

    Proyecta sobre el valor total del apartado (capital + rendimiento
    acumulado); para interés simple usa el capital base como principal.

    Un apartado con tope no crece indefinidamente: la proyección se aplana en
    el tope y el rendimiento que ya no cabe aparece como `overflow_amount` del
    día, que es lo que ese día se va a otro apartado o al saldo disponible.
    """
    if days <= 0:
        return []

    current_value = position.total_value.amount

    base_principal = None
    if position.interest_type == InterestType.SIMPLE:
        base_principal = position.base_principal or current_value

    try:
        rust_results = calculate_projections(
            current_balance=str(current_value),
            annual_rate=str(position.annual_rate),
            interest_type=position.interest_type.value,
            days=days,
            start_year=today.year,
            start_month=today.month,
            start_day=today.day,
            base_principal=str(base_principal) if base_principal is not None else None,
            max_balance=str(position.max_balance)
            if position.max_balance is not None
            else None,
        )
    except FCInvalidDecimalError as e:
        message, field, type = e.args
        raise ValidationError(
            message=message,
            details=[
                {
                    "loc": ["fc", field],
                    "msg": message,
                    "type": type,
                }
            ],
        )
    except FinCoreError as e:
        message, field, type = e.args
        raise BusinessRuleError(
            message=message,
            details=[
                {
                    "loc": ["fc", "business_rule"],
                    "msg": message,
                    "type": type,
                }
            ],
        )

    return [
        ProjectionDayDTO(
            projection_date=date(r.year, r.month, r.day),
            principal_amount=Decimal(r.principal_amount),
            yield_amount=Decimal(r.yield_amount),
            projected_balance=Decimal(r.projected_balance),
            overflow_amount=Decimal(r.overflow_amount),
        )
        for r in rust_results
    ]


@dataclass
class GetPositionProjectionsQuery:
    position_uuid: str
    user_id: int

    project_days: int | None = None


class GetPositionProjectionsHandler:
    def __init__(self, position_repository: InvestmentPositionRepository):
        self.position_repository = position_repository

    async def handle(
        self, query: GetPositionProjectionsQuery
    ) -> PositionProjectionResponseDTO:
        position = await self.position_repository.get_by_uuid_and_user_id(
            position_uuid=query.position_uuid, user_id=query.user_id
        )
        if not position:
            raise InvestmentPositionNotFoundError(query.position_uuid)

        today = date.today()

        if query.project_days:
            days = query.project_days
        elif position.maturity_date:
            days = (position.maturity_date - today).days
        else:
            days = 365  # Default 1 year

        days = min(max(0, days), 3650)  # Limit 10 years

        # Un plazo fijo no rinde después de su vencimiento
        if position.maturity_date:
            days = min(days, max((position.maturity_date - today).days, 0))

        projections = project_position(position, days, today)

        projected_final = (
            projections[-1].projected_balance
            if projections
            else position.total_value.amount
        )

        return PositionProjectionResponseDTO(
            position_uuid=cast(str, position.uuid),
            name=position.name,
            current_value=position.total_value.amount,
            annual_rate=position.annual_rate,
            interest_type=position.interest_type,
            maturity_date=position.maturity_date,
            projected_final_balance=projected_final,
            daily_projections=projections,
            projected_overflow=sum(
                (p.overflow_amount for p in projections), start=Decimal(0)
            ),
            max_balance=position.max_balance,
        )

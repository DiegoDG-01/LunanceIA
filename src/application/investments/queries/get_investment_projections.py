import logging
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import cast

from application.dto.investment_yield_dto import (
    InvestmentProjectionResponseDTO,
    ProjectionDayDTO,
)
from application.investments.queries.get_position_projections import project_position
from domain.entities.investment_position import InvestmentPosition
from domain.objects.enums import PositionStatus
from domain.repositories.account_repository import AccountRepository
from domain.repositories.investment_position_repository import (
    InvestmentPositionRepository,
)
from shared.exceptions.domain import AccountNotFoundError

logger = logging.getLogger(__name__)


@dataclass
class GetInvestmentProjectionsQuery:
    account_uuid: str
    user_id: int

    project_days: int | None = None


class GetInvestmentProjectionsHandler:
    """Proyección agregada de una cuenta: suma día a día las proyecciones de
    todos sus apartados activos.

    Un plazo fijo se proyecta solo hasta su vencimiento y después contribuye
    con su valor final sin crecer (conservador: no se asume renovación).
    """

    def __init__(
        self,
        account_repository: AccountRepository,
        position_repository: InvestmentPositionRepository,
    ):
        self.account_repository = account_repository
        self.position_repository = position_repository

    async def handle(
        self,
        query: GetInvestmentProjectionsQuery,
    ) -> InvestmentProjectionResponseDTO:
        account = await self.account_repository.get_by_uuid_and_user_id(
            account_uuid=query.account_uuid, user_id=query.user_id
        )
        if not account:
            raise AccountNotFoundError(account_uuid=query.account_uuid)

        positions = [
            p
            for p in await self.position_repository.get_by_account_id(
                account_id=cast(int, account.id)
            )
            if p.status == PositionStatus.ACTIVE
        ]

        today = date.today()

        if query.project_days:
            days = query.project_days
        else:
            days_to_maturity = [
                (p.maturity_date - today).days
                for p in positions
                if p.maturity_date and p.maturity_date > today
            ]
            days = max(days_to_maturity) if days_to_maturity else 365

        days = min(max(0, days), 3650)  # Limit 10 years

        per_position: list[tuple[InvestmentPosition, list[ProjectionDayDTO]]] = []
        for position in positions:
            horizon = days
            if position.maturity_date:
                horizon = min(days, max((position.maturity_date - today).days, 0))
            per_position.append((position, project_position(position, horizon, today)))

        daily = self._aggregate(per_position)

        current_total = sum((p.total_value.amount for p in positions), start=Decimal(0))
        projected_final = daily[-1].projected_balance if daily else current_total

        single = positions[0] if len(positions) == 1 else None

        return InvestmentProjectionResponseDTO(
            account_uuid=query.account_uuid,
            current_balance=current_total,
            annual_rate=single.annual_rate if single else None,
            interest_type=single.interest_type if single else None,
            maturity_date=single.maturity_date if single else None,
            projected_final_balance=projected_final,
            daily_projections=daily,
        )

    @staticmethod
    def _aggregate(
        per_position: list[tuple[InvestmentPosition, list[ProjectionDayDTO]]],
    ) -> list[ProjectionDayDTO]:
        longest = max((results for _, results in per_position), key=len, default=[])

        daily: list[ProjectionDayDTO] = []
        for i in range(len(longest)):
            total_principal = Decimal(0)
            total_yield = Decimal(0)
            total_balance = Decimal(0)
            total_overflow = Decimal(0)

            for position, results in per_position:
                if i < len(results):
                    total_principal += results[i].principal_amount
                    total_yield += results[i].yield_amount
                    total_balance += results[i].projected_balance
                    total_overflow += results[i].overflow_amount
                else:
                    # Después de su vencimiento el apartado ya no crece:
                    # contribuye con su valor final constante.
                    flat = (
                        results[-1].projected_balance
                        if results
                        else position.total_value.amount
                    )
                    total_principal += flat
                    total_balance += flat

            daily.append(
                ProjectionDayDTO(
                    projection_date=longest[i].projection_date,
                    principal_amount=total_principal,
                    yield_amount=total_yield,
                    projected_balance=total_balance,
                    overflow_amount=total_overflow,
                )
            )

        return daily

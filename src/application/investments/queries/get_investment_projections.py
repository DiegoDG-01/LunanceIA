from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from domain.objects.enums import InterestType
from domain.repositories.account_repository import AccountRepository
from domain.repositories.investment_card_repository import (
    InvestmentCardSettingsRepository,
)
from domain.repositories.investment_yield_repository import InvestmentYieldRepository
from application.dto.investment_yield_dto import (
    InvestmentProjectionResponseDTO,
    ProjectionDayDTO,
)
from shared.exceptions.domain import AccountNotFoundError


@dataclass
class GetInvestmentProjectionsQuery:
    account_uuid: str
    user_id: int
    project_days: Optional[int] = None


class GetInvestmentProjectionsHandler:
    def __init__(
        self,
        account_repository: AccountRepository,
        investment_yield_repository: InvestmentYieldRepository,
        investment_card_settings_repository: InvestmentCardSettingsRepository,
    ):
        self.account_repository = account_repository
        self.investment_yield_repository = investment_yield_repository
        self.investment_card_settings_repository = investment_card_settings_repository

    async def handle(
        self,
        query: GetInvestmentProjectionsQuery,
    ) -> InvestmentProjectionResponseDTO:
        account = await self.account_repository.get_by_uuid_and_user_id(
            account_uuid=query.account_uuid, user_id=query.user_id
        )
        if not account:
            raise AccountNotFoundError(account_uuid=query.account_uuid)

        settings = await self.investment_card_settings_repository.get_by_account_id(
            account_id=account.id
        )

        today = date.today()
        current_balance = account.current_balance.amount

        if query.project_days:
            days = query.project_days
        elif settings and settings.maturity_date:
            days = (settings.maturity_date - today).days
        else:
            days = 365  # Default 1 year

        days = min(max(0, days), 365)  # Limit 10 years

        original_principal = current_balance
        if settings and settings.interest_type == InterestType.SIMPLE:
            original_principal = settings.base_principal or current_balance

        annual_rate = settings.interest_rate if settings else Decimal("0")
        interest_type = settings.interest_type if settings else InterestType.COMPOUND

        projections = []
        balance = current_balance

        for i in range(1, days + 1):
            projection_date = today + timedelta(days=i)

            if interest_type == InterestType.COMPOUND:
                daily_rate = (1 + annual_rate / Decimal("100")) ** (
                    Decimal("1") / Decimal("365")
                ) - Decimal("1")
                principal = balance
            else:
                daily_rate = annual_rate / Decimal("100") / Decimal("365")
                principal = original_principal

            yield_amount = (principal * daily_rate).quantize(Decimal("0.01"))
            balance = balance + yield_amount

            projections.append(
                ProjectionDayDTO(
                    projection_date=projection_date,
                    principal_amount=principal,
                    yield_amount=yield_amount,
                    projected_balance=balance,
                )
            )

        projected_final = (
            projections[-1].projected_balance if projections else current_balance
        )

        return InvestmentProjectionResponseDTO(
            account_uuid=query.account_uuid,
            current_balance=current_balance,
            annual_rate=annual_rate,
            interest_type=interest_type,
            maturity_date=settings.maturity_date if settings else None,
            projected_final_balance=projected_final,
            daily_projections=projections,
        )

import logging
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional

from domain.objects.enums import InterestType
from domain.repositories.account_repository import AccountRepository
from domain.repositories.investment_card_repository import (
    InvestmentCardSettingsRepository,
)
from application.dto.investment_yield_dto import (
    InvestmentProjectionResponseDTO,
    ProjectionDayDTO,
)
from shared.exceptions.domain import (
    AccountNotFoundError,
    FinancialEngineNotAvailableError,
    BusinessRuleError,
    ValidationError
)

logger = logging.getLogger(__name__)

try:
    from fincore import calculate_projections
    from fincore import FinCoreError, FCInvalidDecimalError
except ImportError:
    logger.critical(
        "The 'fincore' financial engine is not available. "
        "The application will not be able to calculate projections."
    )
    raise FinancialEngineNotAvailableError()


@dataclass
class GetInvestmentProjectionsQuery:
    account_uuid: str
    user_id: int
    project_days: Optional[int] = None


class GetInvestmentProjectionsHandler:
    def __init__(
            self,
            account_repository: AccountRepository,
            investment_card_settings_repository: InvestmentCardSettingsRepository,
    ):
        self.account_repository = account_repository
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

        days = min(max(0, days), 3650)  # Limit 10 years

        original_principal = current_balance
        if settings and settings.interest_type == InterestType.SIMPLE:
            original_principal = settings.base_principal or current_balance

        annual_rate = settings.interest_rate if settings else Decimal("0")
        interest_type = settings.interest_type if settings else InterestType.COMPOUND

        try:
            rust_results = calculate_projections(
                current_balance=str(current_balance),
                annual_rate=str(annual_rate),
                interest_type=interest_type.value,
                days=days,
                start_year=today.year,
                start_month=today.month,
                start_day=today.day,
                base_principal=str(original_principal) if interest_type == InterestType.SIMPLE else None,
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
                ]
            )

        projections = [
            ProjectionDayDTO(
                projection_date=date(r.year, r.month, r.day),
                principal_amount=Decimal(r.principal_amount),
                yield_amount=Decimal(r.yield_amount),
                projected_balance=Decimal(r.projected_balance),
            )
            for r in rust_results
        ]

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

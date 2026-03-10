import logging
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from domain.objects.enums import InterestType
from domain.objects.money import Money
from domain.entities.investment_yield import InvestmentYield
from domain.repositories.investment_card_repository import (
    InvestmentCardSettingsRepository,
)
from domain.repositories.account_repository import AccountRepository
from domain.repositories.investment_yield_repository import InvestmentYieldRepository
from domain.repositories.unit_of_work import AbstractUnitOfWork
from shared.utils.date import get_year_day_basis


logger = logging.getLogger(__name__)

# Investment excluded because it is non-deterministic
EXCLUDED_INVESTMENT_TYPES = {"stocks", "etf", "mutual_fund"}


@dataclass
class GenerateDailyYieldCommand:
    target_date: date


class GenerateDailyYieldHandler:
    def __init__(
        self,
        account_repository: AccountRepository,
        investment_yield_repository: InvestmentYieldRepository,
        investment_settings_repository: InvestmentCardSettingsRepository,
        uow: AbstractUnitOfWork,
    ):
        self.account_repository = account_repository
        self.investment_yield_repository = investment_yield_repository
        self.investment_settings_repository = investment_settings_repository
        self.uow = uow

    async def handle(self, command: GenerateDailyYieldCommand) -> dict:
        today = command.target_date
        processed = 0
        skipped = 0
        errors = 0

        accounts = await self.account_repository.get_active_investment_accounts()

        async with self.uow:
            for account in accounts:
                try:
                    settings = await self.investment_settings_repository.get_by_account_id(
                        account_id=account.id
                    )
                    if not settings:
                        skipped += 1
                        continue

                    if settings.investment_type in EXCLUDED_INVESTMENT_TYPES:
                        skipped += 1
                        continue

                    if settings.maturity_date and today > settings.maturity_date:
                        skipped += 1
                        continue

                    # Idempotency: Does today's performance already exist?
                    existing = (
                        await self.investment_yield_repository.get_by_account_and_date(
                            account_id=account.id, yield_date=today
                        )
                    )
                    if existing:
                        skipped += 1
                        continue

                    annual_rate = settings.investment_rate
                    year_basis = Decimal(get_year_day_basis(today))

                    if settings.interest_type == InterestType.COMPOUND:
                        principal = account.current_balance.amount
                        daily_rate = (1 + annual_rate / Decimal(100)) ** (
                            Decimal(1) / year_basis
                        ) - Decimal(1)
                    else:
                        principal = (
                            settings.base_principal or account.current_balance.amount
                        )
                        daily_rate = annual_rate / Decimal(100) / year_basis

                    yield_amount = (principal * daily_rate).quantize(Decimal("0.01"))
                    cumulative_balance = account.current_balance.amount + yield_amount

                    yield_record = InvestmentYield.create_new(
                        account_id=account.id,
                        yield_date=today,
                        principal_amount=principal,
                        yield_amount=yield_amount,
                        cumulative_balance=cumulative_balance,
                        annual_rate=annual_rate,
                        interest_type=settings.interest_type,
                    )

                    await self.investment_yield_repository.create(yield_record)

                    new_balance = Money(
                        amount=cumulative_balance,
                        currency=account.current_balance.currency,
                    )
                    account.update_balance(new_balance)
                    await self.account_repository.update(account)

                    processed += 1
                    logger.info(f"generated daily yield for account {account.id}")

                except Exception as e:
                    errors += 1
                    logger.error(
                        f"failed to generate daily yield for account {account.id}: {e}",
                        exc_info=True,
                    )

            await self.uow.commit()

        return {
            "processed": processed,
            "skipped": skipped,
            "errors": errors,
        }

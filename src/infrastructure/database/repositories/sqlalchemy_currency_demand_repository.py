from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from application.securities.currency_demand import CurrencyDemandRepository
from domain.objects.enums import Currency
from infrastructure.database.models import AccountModel, InvestmentPositionModel

BASE = Currency.MXN.value


class SQLAlchemyCurrencyDemandRepository(CurrencyDemandRepository):
    def __init__(self, db: AsyncSession):
        self.db = db

    async def since(self) -> dict[str, date | None]:
        demand: dict[str, date | None] = {
            currency: None
            for currency in (
                await self.db.execute(
                    select(AccountModel.currency)
                    .where(
                        AccountModel.is_active.is_(True), AccountModel.currency != BASE
                    )
                    .distinct()
                )
            ).scalars()
        }
        for currency, start in await self.db.execute(
            select(
                InvestmentPositionModel.currency,
                func.min(InvestmentPositionModel.start_date),
            )
            .where(InvestmentPositionModel.currency != BASE)
            .group_by(InvestmentPositionModel.currency)
        ):
            demand[currency] = start
        return demand

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from domain.repositories.investment_card_repository import (
    InvestmentCardSettingsRepository,
)
from domain.objects.investment_settings import InvestmentCardSettings
from infrastructure.database.models.investment_account import (
    InvestmentCardSettingsModel,
)
from shared.exceptions.domain import InvestmentSettingsNotFoundError


class SQLAlchemyInvestmentSettingsRepository(InvestmentCardSettingsRepository):
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _model_to_vo(model: InvestmentCardSettingsModel) -> InvestmentCardSettings:
        return InvestmentCardSettings(
            investment_type=model.investment_type,
            investment_rate=model.investment_rate,
            interest_type=model.interest_type,
            lock_period_end_date=model.lock_period_end_date,
            maturity_date=model.maturity_date,
            early_withdrawal_penalty=model.early_withdrawal_penalty,
            base_principal=model.base_principal,
        )

    @staticmethod
    def _vo_to_model(vo: InvestmentCardSettings) -> InvestmentCardSettingsModel:
        return InvestmentCardSettingsModel(
            investment_type=vo.investment_type,
            investment_rate=vo.investment_rate,
            interest_type=vo.interest_type,
            maturity_date=vo.maturity_date,
            lock_period_end_date=vo.lock_period_end_date,
            early_withdrawal_penalty=vo.early_withdrawal_penalty,
        )

    async def create(
        self, account_id: int, settings: InvestmentCardSettings
    ) -> InvestmentCardSettings:
        model = self._vo_to_model(settings)
        model.account_id = account_id
        self.db.add(model)
        await self.db.flush()
        await self.db.refresh(model)
        return self._model_to_vo(model)

    async def get_by_account_id(
        self, account_id: int
    ) -> Optional[InvestmentCardSettings]:
        stmt = select(InvestmentCardSettingsModel).where(
            InvestmentCardSettingsModel.account_id == account_id
        )
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()

        return self._model_to_vo(model) if model else None

    async def update(
        self, account_id: int, settings: InvestmentCardSettings
    ) -> InvestmentCardSettings:
        stmt = select(InvestmentCardSettingsModel).where(
            InvestmentCardSettingsModel.account_id == account_id
        )
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            raise InvestmentSettingsNotFoundError(account_id)

        model.investment_type = settings.investment_type
        model.investment_rate = settings.investment_rate
        model.interest_type = settings.interest_type
        model.lock_period_end_date = settings.lock_period_end_date
        model.maturity_date = settings.maturity_date
        model.early_withdrawal_penalty = settings.early_withdrawal_penalty
        model.base_principal = settings.base_principal

        await self.db.flush()
        await self.db.refresh(model)
        return self._model_to_vo(model)

    async def delete(self, account_id: int) -> None:
        stmt = select(InvestmentCardSettingsModel).where(
            InvestmentCardSettingsModel.account_id == account_id
        )
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()

        if model:
            await self.db.delete(model)
            await self.db.flush()
            return True
        return False

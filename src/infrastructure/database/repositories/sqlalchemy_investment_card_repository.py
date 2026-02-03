from typing import Optional
from sqlalchemy.orm import Session
from domain.repositories.investment_card_repository import (
    InvestmentCardSettingsRepository,
)
from domain.objects.investment_settings import InvestmentCardSettings
from infrastructure.database.models.investment_account import (
    InvestmentCardSettingsModel,
)


class SQLAlchemyInvestmentSettingsRepository(InvestmentCardSettingsRepository):
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _model_to_vo(model: InvestmentCardSettingsModel) -> InvestmentCardSettings:
        return InvestmentCardSettings(
            investment_type=model.investment_type,
            interest_rate=model.investment_rate,
            lock_period_end_date=model.lock_period_end_date,
            maturity_date=model.maturity_date,
            early_withdrawal_penalty=model.early_withdrawal_penalty,
        )

    @staticmethod
    def _vo_to_model(vo: InvestmentCardSettings) -> InvestmentCardSettingsModel:
        return InvestmentCardSettingsModel(
            investment_type=vo.investment_type,
            investment_rate=vo.interest_rate,
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
        self.db.commit()
        self.db.refresh(model)
        return self._model_to_vo(model)

    async def get_by_account_id(
        self, account_id: int
    ) -> Optional[InvestmentCardSettings]:
        model = (
            self.db.query(InvestmentCardSettingsModel)
            .filter(InvestmentCardSettingsModel.account_id == account_id)
            .first()
        )
        return self._model_to_vo(model) if model else None

    async def update(
        self, account_id: int, settings: InvestmentCardSettings
    ) -> InvestmentCardSettings:
        model = (
            self.db.query(InvestmentCardSettingsModel)
            .filter(InvestmentCardSettingsModel.account_id == account_id)
            .first()
        )

        if model is None:
            raise ValueError("Credit card settings no encontrada")

        model.investment_type = settings.investment_type
        model.investment_rate = settings.interest_rate
        model.lock_period_end_date = settings.lock_period_end_date
        model.maturity_date = settings.maturity_date
        model.early_withdrawal_penalty = settings.early_withdrawal_penalty

        self.db.commit()
        self.db.refresh(model)
        return self._model_to_vo(model)

    async def delete(self, account_id: int) -> None:
        model = (
            self.db.query(InvestmentCardSettingsModel)
            .filter(InvestmentCardSettingsModel.account_id == account_id)
            .first()
        )

        if model:
            self.db.delete(model)
            self.db.commit()
            return True
        return False

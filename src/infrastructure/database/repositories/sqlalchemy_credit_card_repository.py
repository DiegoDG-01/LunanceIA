from typing import Optional

from sqlalchemy.orm import Session
from domain.repositories.credit_card_repository import CreditCardSettingsRepository
from domain.objects.credit_card_settings import CreditCardSettings
from infrastructure.database.models.credit_card import CreditCardSettingsModel


class SQLAlchemyCreditCardSettingsRepository(CreditCardSettingsRepository):
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _model_to_vo(model: CreditCardSettingsModel) -> CreditCardSettings:
        return CreditCardSettings(
            billing_cycle_day=model.billing_cycle_day,
            payment_due_day=model.payment_due_day,
            credit_limit=model.credit_limit,
            minimum_payment_percentage=model.minimum_payment_percentage,
        )

    @staticmethod
    def _vo_to_model(vo: CreditCardSettings) -> CreditCardSettingsModel:
        return CreditCardSettingsModel(
            billing_cycle_day=vo.billing_cycle_day,
            payment_due_day=vo.payment_due_day,
            credit_limit=vo.credit_limit,
            minimum_payment_percentage=vo.minimum_payment_percentage,
        )

    async def create(
        self, account_id: int, settings: CreditCardSettings
    ) -> CreditCardSettings:
        model = self._vo_to_model(settings)
        model.account_id = account_id
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return self._model_to_vo(model)

    async def get_by_account_id(self, account_id: int) -> Optional[CreditCardSettings]:
        model = (
            self.db.query(CreditCardSettingsModel)
            .filter(CreditCardSettingsModel.account_id == account_id)
            .first()
        )
        return self._model_to_vo(model) if model else None

    async def update(
        self, account_id: int, settings: CreditCardSettings
    ) -> CreditCardSettings:
        model = (
            self.db.query(CreditCardSettingsModel)
            .filter(CreditCardSettingsModel.account_id == account_id)
            .first()
        )

        if model is None:
            raise ValueError("Credit card settings no encontrada")

        model.billing_cycle_day = settings.billing_cycle_day
        model.payment_due_day = settings.payment_due_day
        model.credit_limit = settings.credit_limit
        model.minimum_payment_percentage = settings.minimum_payment_percentage

        self.db.commit()
        self.db.refresh(model)
        return self._model_to_vo(model)

    async def delete(self, account_id: int) -> None:
        model = (
            self.db.query(CreditCardSettingsModel)
            .filter(CreditCardSettingsModel.account_id == account_id)
            .first()
        )

        if model:
            self.db.delete(model)
            self.db.commit()
            return True
        return False

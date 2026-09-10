from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.objects.credit_card_settings import CreditCardSettings
from domain.repositories.credit_card_repository import CreditCardSettingsRepository
from infrastructure.database.models.credit_card import CreditCardSettingsModel
from shared.exceptions.domain import CreditCardSettingsNotFoundError


class SQLAlchemyCreditCardSettingsRepository(CreditCardSettingsRepository):
    def __init__(self, db: AsyncSession):
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
        await self.db.flush()
        await self.db.refresh(model)
        return self._model_to_vo(model)

    async def get_by_account_id(self, account_id: int) -> CreditCardSettings | None:
        stmt = select(CreditCardSettingsModel).where(
            CreditCardSettingsModel.account_id == account_id
        )
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()
        return self._model_to_vo(model) if model else None

    async def update(
        self, account_id: int, settings: CreditCardSettings
    ) -> CreditCardSettings:
        stmt = select(CreditCardSettingsModel).where(
            CreditCardSettingsModel.account_id == account_id
        )
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            raise CreditCardSettingsNotFoundError(str(account_id))

        model.billing_cycle_day = settings.billing_cycle_day
        model.payment_due_day = settings.payment_due_day
        model.credit_limit = settings.credit_limit
        model.minimum_payment_percentage = settings.minimum_payment_percentage

        await self.db.flush()
        await self.db.refresh(model)
        return self._model_to_vo(model)

    async def delete(self, account_id: int) -> bool:
        stmt = select(CreditCardSettingsModel).where(
            CreditCardSettingsModel.account_id == account_id
        )
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()

        if model:
            await self.db.delete(model)
            await self.db.flush()
            return True
        return False

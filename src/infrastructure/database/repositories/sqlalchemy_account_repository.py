from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.account import Account
from domain.objects.credit_card_settings import CreditCardSettings
from domain.objects.money import Money
from domain.repositories.account_repository import AccountRepository
from infrastructure.database.models import (
    BankModel,
    CreditCardSettingsModel,
)
from infrastructure.database.models.account import AccountModel
from shared.exceptions.domain import AccountNotFoundError


class SQLAlchemyAccountRepository(AccountRepository):
    """
    Implementation of AccountRepository using SQLAlchemy
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _model_to_entity(model: AccountModel) -> Account:
        """
        Convert a SQLAlchemy AccountModel to a domain Account entity
        """
        return Account(
            id=model.id,
            uuid=model.uuid,
            user_id=model.user_id,
            name=model.name,
            account_type=model.type,
            bank_id=model.bank_id,
            current_balance=Money(
                amount=model.current_balance, currency=model.currency
            ),
            is_active=model.is_active,
            creation_date=model.creation_date,
        )

    @staticmethod
    def _entity_to_model(entity: Account) -> AccountModel:
        """
        Convert a domain Account entity to a SQLAlchemy AccountModel
        """
        return AccountModel(
            user_id=entity.user_id,
            name=entity.name,
            type=entity.account_type,
            bank_id=entity.bank_id,
            current_balance=entity.current_balance.amount,
            currency=entity.current_balance.currency,
            is_active=entity.is_active,
            creation_date=entity.creation_date,
        )

    async def create(self, account: Account) -> Account:
        model = self._entity_to_model(account)
        self.db.add(model)
        await self.db.flush()
        await self.db.refresh(model)
        return self._model_to_entity(model)

    async def get_by_id(
        self, account_id: int, for_update: bool = False
    ) -> Account | None:
        stmt = select(AccountModel).where(AccountModel.id == account_id)

        if for_update:
            stmt = stmt.with_for_update()

        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._model_to_entity(model)

    async def get_bulk_by_ids(self, account_ids: list[int]) -> list[Account]:
        stmt = select(AccountModel).where(AccountModel.id.in_(account_ids))
        result = await self.db.execute(stmt)
        models = result.scalars().all()
        return [self._model_to_entity(model) for model in models]

    async def get_by_uuid_and_user_id(
        self, account_uuid: str, user_id: int, *, for_update: bool = False
    ) -> Account | None:
        stmt = select(AccountModel).where(
            and_(
                AccountModel.uuid == account_uuid,
                AccountModel.user_id == user_id,
            )
        )

        if for_update:
            stmt = stmt.with_for_update()

        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._model_to_entity(model)

    async def get_by_user_id(
        self, user_id: int, limit: int, offset: int
    ) -> list[Account]:
        stmt = (
            select(
                AccountModel,
                BankModel,
                CreditCardSettingsModel,
            )
            .outerjoin(BankModel, AccountModel.bank_id == BankModel.id)
            .outerjoin(
                CreditCardSettingsModel,
                AccountModel.id == CreditCardSettingsModel.account_id,
            )
            .where(AccountModel.user_id == user_id)
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(stmt)
        rows = result.all()

        accounts = []
        for account_model, bank_model, cc_model in rows:
            account = self._model_to_entity(account_model)
            if bank_model:
                account.bank_code = bank_model.code
                account.bank_name = bank_model.name

            if cc_model:
                account.credit_card_settings = CreditCardSettings(
                    billing_cycle_day=cc_model.billing_cycle_day,
                    payment_due_day=cc_model.payment_due_day,
                    credit_limit=cc_model.credit_limit,
                    minimum_payment_percentage=cc_model.minimum_payment_percentage,
                )

            accounts.append(account)
        return accounts

    async def get_active_by_user(
        self, user_id: int, limit: int, offset: int
    ) -> list[Account]:
        stmt = (
            select(
                AccountModel,
                BankModel,
                CreditCardSettingsModel,
            )
            .outerjoin(BankModel, AccountModel.bank_id == BankModel.id)
            .outerjoin(
                CreditCardSettingsModel,
                AccountModel.id == CreditCardSettingsModel.account_id,
            )
            .where(
                and_(
                    AccountModel.user_id == user_id,
                    AccountModel.is_active,
                )
            )
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(stmt)
        rows = result.all()

        accounts = []
        for account_model, bank_model, cc_model in rows:
            account = self._model_to_entity(account_model)

            if bank_model:
                account.bank_code = bank_model.code
                account.bank_name = bank_model.name

            if cc_model:
                account.credit_card_settings = CreditCardSettings(
                    billing_cycle_day=cc_model.billing_cycle_day,
                    payment_due_day=cc_model.payment_due_day,
                    credit_limit=cc_model.credit_limit,
                    minimum_payment_percentage=cc_model.minimum_payment_percentage,
                )

            accounts.append(account)
        return accounts

    async def update(self, account: Account) -> Account:
        stmt = select(AccountModel).where(AccountModel.uuid == account.uuid)
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            raise AccountNotFoundError(str(account.uuid))

        model.name = account.name
        model.type = account.account_type
        model.bank_id = account.bank_id
        model.current_balance = account.current_balance.amount
        model.currency = account.current_balance.currency
        model.is_active = account.is_active

        await self.db.flush()
        await self.db.refresh(model)

        return self._model_to_entity(model)

    async def delete(self, account: Account) -> bool:
        """Elimina completamente una cuenta de la base de datos."""
        stmt = select(AccountModel).where(AccountModel.uuid == account.uuid)
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            raise AccountNotFoundError(str(account.uuid))

        await self.db.delete(model)
        await self.db.flush()
        return True

    async def switch_status(self, account: Account) -> Account:
        account.is_active = not account.is_active
        return await self.update(account)

    async def get_by_uuid_and_user_id_with_settings(
        self, uuid: str, user_id: int
    ) -> Account | None:
        stmt = (
            select(
                AccountModel,
                CreditCardSettingsModel,
                BankModel,
            )
            .outerjoin(
                CreditCardSettingsModel,
                AccountModel.id == CreditCardSettingsModel.account_id,
            )
            .outerjoin(
                BankModel,
                AccountModel.bank_id == BankModel.id,
            )
            .where(AccountModel.uuid == uuid, AccountModel.user_id == user_id)
        )
        result = await self.db.execute(stmt)
        row = result.first()

        if not row:
            return None

        account_model, cc_settings_model, bank_model = row

        account = self._model_to_entity(account_model)

        if cc_settings_model:
            account.credit_card_settings = CreditCardSettings(
                billing_cycle_day=cc_settings_model.billing_cycle_day,
                payment_due_day=cc_settings_model.payment_due_day,
                credit_limit=cc_settings_model.credit_limit,
                minimum_payment_percentage=cc_settings_model.minimum_payment_percentage,
            )

        account.bank_name = bank_model.name
        account.bank_code = bank_model.code

        return account

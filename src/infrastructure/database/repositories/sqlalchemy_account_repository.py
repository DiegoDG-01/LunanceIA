from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, select

from domain.entities.account import Account
from domain.objects.enums import AccountType
from domain.repositories.account_repository import AccountRepository
from domain.objects.money import Money
from domain.objects.credit_card_settings import CreditCardSettings
from domain.objects.investment_settings import InvestmentCardSettings
from infrastructure.database.models import (
    CreditCardSettingsModel,
    InvestmentCardSettingsModel,
    BankModel,
)
from infrastructure.database.models.account import AccountModel


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

    async def get_by_id(self, account_id: int) -> Optional[Account]:
        stmt = select(AccountModel).where(AccountModel.id == account_id)
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._model_to_entity(model)

    async def get_by_uuid_and_user_id(
        self, account_uuid: str, user_id: int
    ) -> Optional[Account]:
        stmt = select(AccountModel).where(
            and_(
                AccountModel.uuid == account_uuid,
                AccountModel.user_id == user_id,
            )
        )
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._model_to_entity(model)

    async def get_by_user_id(
        self, user_id: int, limit: int, offset: int
    ) -> List[Account]:
        stmt = (
            select(
                AccountModel,
                BankModel,
                CreditCardSettingsModel,
                InvestmentCardSettingsModel,
            )
            .outerjoin(BankModel, AccountModel.bank_id == BankModel.id)
            .outerjoin(
                CreditCardSettingsModel,
                AccountModel.id == CreditCardSettingsModel.account_id,
            )
            .outerjoin(
                InvestmentCardSettingsModel,
                AccountModel.id == InvestmentCardSettingsModel.account_id,
            )
            .where(AccountModel.user_id == user_id)
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(stmt)
        rows = result.all()

        accounts = []
        for account_model, bank_model, cc_model, inv_model in rows:
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

            if inv_model:
                account.investment_settings = InvestmentCardSettings(
                    investment_type=inv_model.investment_type,
                    investment_rate=inv_model.investment_rate,
                    interest_type=inv_model.interest_type,
                    lock_period_end_date=inv_model.lock_period_end_date,
                    maturity_date=inv_model.maturity_date,
                    early_withdrawal_penalty=inv_model.early_withdrawal_penalty,
                )

            accounts.append(account)
        return accounts

    async def get_active_by_user(
        self, user_id: int, limit: int, offset: int
    ) -> List[Account]:
        stmt = (
            select(
                AccountModel,
                BankModel,
                CreditCardSettingsModel,
                InvestmentCardSettingsModel,
            )
            .outerjoin(BankModel, AccountModel.bank_id == BankModel.id)
            .outerjoin(
                CreditCardSettingsModel,
                AccountModel.id == CreditCardSettingsModel.account_id,
            )
            .outerjoin(
                InvestmentCardSettingsModel,
                AccountModel.id == InvestmentCardSettingsModel.account_id,
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
        for account_model, bank_model, cc_model, inv_model in rows:
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

            if inv_model:
                account.investment_settings = InvestmentCardSettings(
                    investment_type=inv_model.investment_type,
                    investment_rate=inv_model.investment_rate,
                    interest_type=inv_model.interest_type,
                    lock_period_end_date=inv_model.lock_period_end_date,
                    maturity_date=inv_model.maturity_date,
                    early_withdrawal_penalty=inv_model.early_withdrawal_penalty,
                    base_principal=inv_model.base_principal,
                )

            accounts.append(account)
        return accounts

    async def update(self, account: Account) -> Account:
        stmt = select(AccountModel).where(AccountModel.uuid == account.uuid)
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            raise Exception("Account not found")

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
            raise Exception("Account not found")

        await self.db.delete(model)
        await self.db.flush()
        return True

    async def switch_status(self, account: Account) -> Account:
        account.is_active = not account.is_active
        return await self.update(account)

    async def get_by_uuid_and_user_id_with_settings(
        self, uuid: str, user_id: int
    ) -> Account:
        stmt = (
            select(
                AccountModel,
                CreditCardSettingsModel,
                InvestmentCardSettingsModel,
                BankModel,
            )
            .outerjoin(
                CreditCardSettingsModel,
                AccountModel.id == CreditCardSettingsModel.account_id,
            )
            .outerjoin(
                InvestmentCardSettingsModel,
                AccountModel.id == InvestmentCardSettingsModel.account_id,
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

        account_model, cc_settings_model, inv_settings_model, bank_model = row

        account = self._model_to_entity(account_model)

        if cc_settings_model:
            account.credit_card_settings = CreditCardSettings(
                billing_cycle_day=cc_settings_model.billing_cycle_day,
                payment_due_day=cc_settings_model.payment_due_day,
                credit_limit=cc_settings_model.credit_limit,
                minimum_payment_percentage=cc_settings_model.minimum_payment_percentage,
            )

        if inv_settings_model:
            account.investment_card_settings = InvestmentCardSettings(
                investment_type=inv_settings_model.investment_type,
                investment_rate=inv_settings_model.investment_rate,
                interest_type=inv_settings_model.interest_type,
                lock_period_end_date=inv_settings_model.lock_period_end_date,
                maturity_date=inv_settings_model.maturity_date,
                early_withdrawal_penalty=inv_settings_model.early_withdrawal_penalty,
                base_principal=inv_settings_model.base_principal,
            )

        account.bank_name = bank_model.name
        account.bank_code = bank_model.code

        return account

    async def get_active_investment_accounts(self) -> List[Account]:
        stmt = (
            select(AccountModel, InvestmentCardSettingsModel)
            .outerjoin(
                InvestmentCardSettingsModel,
                AccountModel.id == InvestmentCardSettingsModel.account_id,
            )
            .where(
                and_(
                    AccountModel.type == AccountType.INVESTMENT,
                    AccountModel.is_active,
                )
            )
        )
        result = await self.db.execute(stmt)
        rows = result.all()

        accounts = []
        for account_model, inv_model in rows:
            account = self._model_to_entity(account_model)

            if inv_model:
                account.investment_settings = InvestmentCardSettings(
                    investment_type=inv_model.investment_type,
                    investment_rate=inv_model.investment_rate,
                    interest_type=inv_model.interest_type,
                    lock_period_end_date=inv_model.lock_period_end_date,
                    maturity_date=inv_model.maturity_date,
                    early_withdrawal_penalty=inv_model.early_withdrawal_penalty,
                    base_principal=inv_model.base_principal,
                )
            accounts.append(account)
        return accounts

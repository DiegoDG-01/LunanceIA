from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_

from domain.entities.account import Account
from domain.repositories.account_repository import AccountRepository
from domain.objects.money import Money
from domain.objects.credit_card_settings import CreditCardSettings
from domain.objects.investment_settings import InvestmentCardSettings
from infrastructure.database.models import (
    CreditCardSettingsModel,
    InvestmentCardSettingsModel,
)
from infrastructure.database.models.account import AccountModel


class SQLAlchemyAccountRepository(AccountRepository):
    """
    Implementation of AccountRepository using SQLAlchemy
    """

    def __init__(self, db: Session):
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
            bank=model.bank,
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
            bank=entity.bank,
            current_balance=entity.current_balance.amount,
            currency=entity.current_balance.currency,
            is_active=entity.is_active,
            creation_date=entity.creation_date,
        )

    async def create(self, account: Account) -> Account:
        model = self._entity_to_model(account)
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return self._model_to_entity(model)

    async def get_by_id(self, account_id: int) -> Optional[Account]:
        model = (
            self.db.query(AccountModel).filter(AccountModel.id == account_id).first()
        )
        if model is None:
            return None
        return self._model_to_entity(model)

    async def get_by_uuid_and_user_id(
        self, account_uuid: str, user_id: int
    ) -> Optional[Account]:
        model = (
            self.db.query(AccountModel)
            .filter(
                and_(
                    AccountModel.uuid == account_uuid,
                    AccountModel.user_id == user_id,
                )
            )
            .first()
        )
        if model is None:
            return None
        return self._model_to_entity(model)

    async def get_by_user_id(self, user_id: int) -> List[Account]:
        models = (
            self.db.query(AccountModel).filter(AccountModel.user_id == user_id).all()
        )
        return [self._model_to_entity(model) for model in models]

    async def get_active_by_user(self, user_uuid: str) -> List[Account]:
        models = (
            self.db.query(AccountModel)
            .filter(
                and_(
                    AccountModel.user_uuid == user_uuid, AccountModel.is_active is True
                )
            )
            .all()
        )
        return [self._model_to_entity(model) for model in models]

    async def update(self, account: Account) -> Account:
        model = (
            self.db.query(AccountModel)
            .filter(AccountModel.uuid == account.uuid)
            .first()
        )

        if not model:
            raise Exception("Account not found")

        model.name = account.name
        model.type = account.account_type
        model.bank = account.bank
        model.current_balance = account.current_balance.amount
        model.currency = account.current_balance.currency
        model.is_active = account.is_active

        self.db.commit()
        self.db.refresh(model)

        return self._model_to_entity(model)

    async def delete(self, account: Account) -> bool:
        """Elimina completamente una cuenta de la base de datos."""
        result = (
            self.db.query(AccountModel)
            .filter(AccountModel.uuid == account.uuid)
            .delete()
        )
        if not result:
            raise Exception("Account not found")
        self.db.commit()
        return result > 0

    async def switch_status(self, account: Account) -> Account:
        account.is_active = not account.is_active
        return await self.update(account)

    async def get_by_uuid_and_user_id_with_settings(
        self, account_uuid: str, user_id: int
    ) -> tuple:
        result = (
            self.db.query(
                AccountModel, CreditCardSettingsModel, InvestmentCardSettingsModel
            )
            .outerjoin(
                CreditCardSettingsModel,
                AccountModel.id == CreditCardSettingsModel.account_id,
            )
            .outerjoin(
                InvestmentCardSettingsModel,
                AccountModel.id == InvestmentCardSettingsModel.account_id,
            )
            .filter(AccountModel.uuid == account_uuid, AccountModel.user_id == user_id)
            .first()
        )

        if not result:
            return None

        account_model, cc_settings_model, inv_settings_model = result

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
                interest_rate=inv_settings_model.interest_rate,
                lock_period_end_date=inv_settings_model.lock_period_end_date,
                maturity_date=inv_settings_model.maturity_date,
                early_withdrawal_penalty=inv_settings_model.early_withdrawal_penalty,
            )

        return account

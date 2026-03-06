from dataclasses import dataclass
from typing import Optional

from domain.repositories.account_repository import AccountRepository
from domain.repositories.bank_repository import BankRepository
from application.dto.account_dto import (
    AccountResponseDTO,
    CreditCardSettingsDTO,
    InvestmentCardSettingsDTO,
)

from shared.exceptions.domain import AccountNotFoundError


@dataclass
class GetAccountByIdQuery:
    """Query para obtener cuenta por ID."""

    account_uuid: str
    user_id: int
    limit: int
    offset: int


class GetAccountByIdHandler:
    """Handler para obtener cuenta por ID."""

    def __init__(
        self, account_repository: AccountRepository, bank_repository: BankRepository
    ):
        self.account_repository = account_repository
        self.bank_repository = bank_repository

    async def handle(self, query: GetAccountByIdQuery) -> Optional[AccountResponseDTO]:
        """Ejecuta la query de obtener cuenta por ID."""
        account = await self.account_repository.get_by_uuid_and_user_id_with_settings(
            uuid=query.account_uuid,
            user_id=query.user_id,
            limit=query.limit,
            offset=query.offset,
        )

        if not account:
            raise AccountNotFoundError(account_uuid=query.account_uuid)

        cc_settings_dto = None
        inv_settings_dto = None

        if account.credit_card_settings:
            cc_settings_dto = CreditCardSettingsDTO(
                billing_cycle_day=account.credit_card_settings.billing_cycle_day,
                payment_due_day=account.credit_card_settings.payment_due_day,
                credit_limit=account.credit_card_settings.credit_limit,
                minimum_payment_percentage=account.credit_card_settings.minimum_payment_percentage,
            )

        if account.investment_settings:
            inv_settings_dto = InvestmentCardSettingsDTO(
                investment_type=account.investment_settings.investment_type,
                interest_rate=account.investment_settings.interest_rate,
                lock_period_end_date=account.investment_settings.lock_period_end_date,
                maturity_date=account.investment_settings.maturity_date,
                early_withdrawal_penalty=account.investment_settings.early_withdrawal_penalty,
            )

        bank_name = None
        bank_code = None
        if account.bank_id:
            bank = await self.bank_repository.get_by_id(account.bank_id)
            if bank:
                bank_name = bank.name
                bank_code = bank.code

        return AccountResponseDTO(
            account_uuid=account.uuid,
            name=account.name,
            account_type=account.account_type,
            bank_id=account.bank_id,
            bank_name=bank_name,
            bank_code=bank_code,
            current_balance=account.current_balance.amount,
            currency=account.current_balance.currency,
            is_active=account.is_active,
            credit_card_settings=cc_settings_dto,
            investment_settings=inv_settings_dto,
        )

from dataclasses import dataclass
from typing import List

from domain.objects.enums import AccountType
from domain.repositories.account_repository import AccountRepository
from application.dto.account_dto import AccountResponseDTO
from domain.repositories.bank_repository import BankRepository
from domain.repositories.credit_card_repository import CreditCardSettingsRepository
from domain.repositories.investment_card_repository import (
    InvestmentCardSettingsRepository,
)


@dataclass
class GetUserAccountsQuery:
    """Query para obtener cuentas de usuario."""

    user_id: int
    only_active: bool = False
    limit: int = 50
    offset: int = 0


class GetUserAccountsHandler:
    """Handler para obtener cuentas de usuario."""

    def __init__(
        self,
        account_repository: AccountRepository,
        bank_repository: BankRepository,
        credit_card_repository: CreditCardSettingsRepository,
        investment_card_repository: InvestmentCardSettingsRepository,
    ):
        self.account_repository = account_repository
        self.bank_repository = bank_repository
        self.credit_card_repository = credit_card_repository
        self.investment_card_repository = investment_card_repository

    async def handle(self, query: GetUserAccountsQuery) -> List[AccountResponseDTO]:
        """Ejecuta la query de obtener cuentas."""
        if query.only_active:
            accounts = await self.account_repository.get_active_by_user(
                user_id=query.user_id,
                limit=query.limit,
                offset=query.offset,
            )
        else:
            accounts = await self.account_repository.get_by_user_id(
                user_id=query.user_id,
                limit=query.limit,
                offset=query.offset,
            )

        for account in accounts:
            if account.bank_id:
                bank = await self.bank_repository.get_by_id(account.bank_id)
                account.bank_name = bank.name if bank else None
                account.bank_code = bank.code if bank else None

            if account.account_type == AccountType.CREDIT_CARD:
                data = await self.credit_card_repository.get_by_account_id(account.id)
                account.credit_card_settings = data

            if account.account_type == AccountType.INVESTMENT:
                data = await self.investment_card_repository.get_by_account_id(
                    account.id
                )
                account.investment_settings = data

        # Convertir a DTOs
        return [
            AccountResponseDTO(
                account_uuid=account.uuid,
                name=account.name,
                account_type=account.account_type,
                bank_id=account.bank_id,
                bank_name=account.bank_name,
                bank_code=account.bank_code,
                current_balance=account.current_balance.amount,
                currency=account.current_balance.currency,
                is_active=account.is_active,
                credit_card_settings=account.credit_card_settings,
                investment_settings=account.investment_settings,
            )
            for account in accounts
        ]

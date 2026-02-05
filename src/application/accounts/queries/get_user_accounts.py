from dataclasses import dataclass
from typing import List

from domain.repositories.account_repository import AccountRepository
from application.dto.account_dto import AccountResponseDTO
from domain.repositories.bank_repository import BankRepository


@dataclass
class GetUserAccountsQuery:
    """Query para obtener cuentas de usuario."""

    user_id: int
    only_active: bool = False


class GetUserAccountsHandler:
    """Handler para obtener cuentas de usuario."""

    def __init__(
        self,
        account_repository: AccountRepository,
        bank_repository: BankRepository,
    ):
        self.account_repository = account_repository
        self.bank_repository = bank_repository

    async def handle(self, query: GetUserAccountsQuery) -> List[AccountResponseDTO]:
        """Ejecuta la query de obtener cuentas."""
        if query.only_active:
            accounts = await self.account_repository.get_active_by_user(query.user_uuid)
        else:
            accounts = await self.account_repository.get_by_user_id(query.user_id)

        for account in accounts:
            bank = await self.bank_repository.get_by_id(account.bank_id)
            account.bank_name = bank.name
            account.bank_code = bank.code
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
            )
            for account in accounts
        ]

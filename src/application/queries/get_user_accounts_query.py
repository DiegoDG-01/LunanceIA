from dataclasses import dataclass
from typing import List

from domain.repositories.account_repository import AccountRepository
from application.dto.account_dto import AccountResponseDTO


@dataclass
class GetUserAccountsQuery:
    """Query para obtener cuentas de usuario."""

    user_uuid: str
    only_active: bool = False


class GetUserAccountsHandler:
    """Handler para obtener cuentas de usuario."""

    def __init__(self, account_repository: AccountRepository):
        self.account_repository = account_repository

    async def handle(self, query: GetUserAccountsQuery) -> List[AccountResponseDTO]:
        """Ejecuta la query de obtener cuentas."""
        if query.only_active:
            accounts = await self.account_repository.get_active_by_user(query.user_uuid)
        else:
            accounts = await self.account_repository.get_by_user_uuid(query.user_uuid)

        # Convertir a DTOs
        return [
            AccountResponseDTO(
                account_id=account.account_id,
                user_uuid=account.user_uuid,
                name=account.name,
                account_type=account.account_type,
                bank=account.bank,
                current_balance=account.current_balance.amount,
                currency=account.current_balance.currency,
                is_active=account.is_active,
                creation_date=account.creation_date,
            )
            for account in accounts
        ]

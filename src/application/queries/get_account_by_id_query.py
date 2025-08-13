from dataclasses import dataclass
from typing import Optional

from domain.repositories.account_repository import AccountRepository
from application.dto.account_dto import AccountResponseDTO


@dataclass
class GetAccountByIdQuery:
    """Query para obtener cuenta por ID."""

    account_uuid: str
    user_id: int


class GetAccountByIdHandler:
    """Handler para obtener cuenta por ID."""

    def __init__(self, account_repository: AccountRepository):
        self.account_repository = account_repository

    async def handle(self, query: GetAccountByIdQuery) -> Optional[AccountResponseDTO]:
        """Ejecuta la query de obtener cuenta por ID."""
        account = await self.account_repository.get_by_uuid_and_user_id(
            query.account_uuid, query.user_id
        )

        if not account:
            return None

        return AccountResponseDTO(
            account_uuid=account.uuid,
            name=account.name,
            account_type=account.account_type,
            bank=account.bank,
            current_balance=account.current_balance.amount,
            currency=account.current_balance.currency,
            is_active=account.is_active,
        )

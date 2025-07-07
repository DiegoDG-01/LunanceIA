from dataclasses import dataclass
from typing import Optional

from domain.repositories.account_repository import AccountRepository
from application.dto.account_dto import AccountResponseDTO


@dataclass
class GetAccountByIdQuery:
    """Query para obtener cuenta por ID."""

    account_id: int
    user_uuid: str


class GetAccountByIdHandler:
    """Handler para obtener cuenta por ID."""

    def __init__(self, account_repository: AccountRepository):
        self.account_repository = account_repository

    async def handle(self, query: GetAccountByIdQuery) -> Optional[AccountResponseDTO]:
        """Ejecuta la query de obtener cuenta por ID."""
        account = await self.account_repository.get_by_id_and_user_uuid(
            query.account_id, query.user_uuid
        )

        if not account:
            return None

        return AccountResponseDTO(
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

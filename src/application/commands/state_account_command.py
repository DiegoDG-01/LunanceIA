from dataclasses import dataclass

from domain.repositories.account_repository import AccountRepository
from domain.services.account_service import AccountService


@dataclass
class StateAccountCommand:
    account_uuid: str
    user_id: int


class StateAccountHandler:
    def __init__(
        self, account_repository: AccountRepository, account_service: AccountService
    ):
        self.account_repository = account_repository
        self.account_service = account_service

    async def handle(self, command: StateAccountCommand) -> bool:
        account = await self.account_repository.get_by_uuid_and_user_id(
            command.account_uuid, command.user_id
        )
        if not account:
            raise ValueError("Cuenta no encontrada")

        return await self.account_repository.switch_status(account)

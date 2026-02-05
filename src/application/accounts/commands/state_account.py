from dataclasses import dataclass

from domain.repositories.account_repository import AccountRepository
from domain.services.account_service import AccountService
from domain.repositories.bank_repository import BankRepository

from shared.exceptions.domain import AccountNotFoundError


@dataclass
class StateAccountCommand:
    account_uuid: str
    user_id: int


class StateAccountHandler:
    def __init__(
        self,
        account_repository: AccountRepository,
        account_service: AccountService,
        bank_repository: BankRepository,
    ):
        self.account_repository = account_repository
        self.account_service = account_service
        self.bank_repository = bank_repository

    async def handle(self, command: StateAccountCommand) -> bool:
        account = await self.account_repository.get_by_uuid_and_user_id(
            command.account_uuid, command.user_id
        )
        if not account:
            raise AccountNotFoundError(account_uuid=command.account_uuid)

        account_updated = await self.account_repository.switch_status(account)
        bank = await self.bank_repository.get_by_id(account.bank_id)

        account_updated.bank_name = bank.name
        account_updated.bank_code = bank.code

        return account_updated

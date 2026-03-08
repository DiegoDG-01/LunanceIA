from dataclasses import dataclass

from domain.repositories.account_repository import AccountRepository
from domain.repositories.unit_of_work import AbstractUnitOfWork
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
        uow: AbstractUnitOfWork,
    ):
        self.account_repository = account_repository
        self.account_service = account_service
        self.bank_repository = bank_repository
        self.uow = uow

    async def handle(self, command: StateAccountCommand) -> bool:
        account = await self.account_repository.get_by_uuid_and_user_id(
            command.account_uuid, command.user_id
        )
        if not account:
            raise AccountNotFoundError(account_uuid=command.account_uuid)

        async with self.uow:
            account_updated = await self.account_repository.switch_status(account)
            await self.uow.commit()

        if account.bank_id:
            bank = await self.bank_repository.get_by_id(account.bank_id)
            account_updated.bank_name = bank.name if bank else None
            account_updated.bank_code = bank.code if bank else None
        else:
            account_updated.bank_name = None
            account_updated.bank_code = None

        return account_updated

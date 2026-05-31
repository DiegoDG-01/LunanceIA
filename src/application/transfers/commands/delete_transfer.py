from typing import cast
from dataclasses import dataclass

from domain.repositories.account_repository import AccountRepository
from domain.repositories.transaction_repository import TransactionRepository
from domain.repositories.unit_of_work import AbstractUnitOfWork
from shared.exceptions.domain import TransactionNotFoundError


@dataclass
class DeleteTransferCommand:
    transfer_uuid: str
    user_id: int


class DeleteTransferHandler:
    def __init__(
        self,
        transaction_repository: TransactionRepository,
        account_repository: AccountRepository,
        uow: AbstractUnitOfWork,
    ):
        self.transaction_repository = transaction_repository
        self.account_repository = account_repository
        self.uow = uow

    async def handle(self, command: DeleteTransferCommand) -> bool:
        transactions = await self.transaction_repository.get_by_transfer_uuid(
            transfer_uuid=command.transfer_uuid, user_id=command.user_id
        )

        if len(transactions) != 2:
            raise TransactionNotFoundError(command.transfer_uuid)

        outgoing, incoming = transactions[0], transactions[1]

        source_account = await self.account_repository.get_by_id(account_id=outgoing.account_id)
        destination_account = await self.account_repository.get_by_id(account_id=incoming.account_id)

        async with self.uow:
            if source_account:
                source_account.update_balance(
                    source_account.current_balance.add(outgoing.amount)
                )
            if destination_account:
                destination_account.update_balance(
                    destination_account.current_balance.subtract(incoming.amount)
                )

            await self.account_repository.update(source_account)
            await self.account_repository.update(destination_account)
            await self.transaction_repository.delete_by_uuid(
                outgoing.uuid, command.user_id
            )
            await self.transaction_repository.delete_by_uuid(
                incoming.uuid, command.user_id
            )
            await self.uow.commit()

        return True


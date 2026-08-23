from typing import cast
from dataclasses import dataclass

from domain.repositories.account_repository import AccountRepository
from domain.repositories.installment_charge_repository import (
    InstallmentChargeRepository,
)
from domain.repositories.transaction_repository import TransactionRepository
from domain.repositories.unit_of_work import AbstractUnitOfWork
from shared.exceptions.domain import (
    AccountNotFoundError,
    TransactionNotFoundError,
    TransferNotAllowedError,
)


@dataclass
class DeleteTransferCommand:
    transfer_uuid: str
    user_id: int


class DeleteTransferHandler:
    def __init__(
        self,
        transaction_repository: TransactionRepository,
        account_repository: AccountRepository,
        installment_charge_repository: InstallmentChargeRepository,
        uow: AbstractUnitOfWork,
    ):
        self.transaction_repository = transaction_repository
        self.account_repository = account_repository
        self.installment_charge_repository = installment_charge_repository
        self.uow = uow

    async def handle(self, command: DeleteTransferCommand) -> bool:
        async with self.uow:
            transactions = await self.transaction_repository.get_by_transfer_uuid(
                transfer_uuid=command.transfer_uuid,
                user_id=command.user_id,
                for_update=True,
            )

            if len(transactions) != 2:
                raise TransactionNotFoundError(command.transfer_uuid)

            for transaction in transactions:
                charge = await self.installment_charge_repository.get_by_transaction_id(
                    cast(int, transaction.id)
                )
                if charge:
                    raise TransferNotAllowedError(
                        "el movimiento pertenece a una cuota; elimina la compra a meses"
                    )

            outgoing, incoming = transactions[0], transactions[1]

            locked_accounts = {}
            for account_id in sorted({outgoing.account_id, incoming.account_id}):
                account = await self.account_repository.get_by_id(
                    account_id, for_update=True
                )

                if not account or account.user_id != command.user_id:
                    raise AccountNotFoundError(str(account_id))

                locked_accounts[account_id] = account

            source_account = locked_accounts[outgoing.account_id]
            destination_account = locked_accounts[incoming.account_id]

            source_account.update_balance(
                source_account.current_balance.add(outgoing.amount)
            )
            destination_account.update_balance(
                destination_account.current_balance.subtract(incoming.amount)
            )

            await self.account_repository.update(source_account)
            await self.account_repository.update(destination_account)
            await self.transaction_repository.delete_by_uuid(
                cast(str, outgoing.uuid), command.user_id
            )
            await self.transaction_repository.delete_by_uuid(
                cast(str, incoming.uuid), command.user_id
            )
            await self.uow.commit()

        return True

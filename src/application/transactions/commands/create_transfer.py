import uuid
from ctypes import cast
from dataclasses import dataclass
from datetime import date

from sqlalchemy.engine import create

from application.dto.transaction_dto import CreateTransferDTO, TransferResponseDTO
from domain.entities.transaction import Transaction
from domain.objects.enums import TransactionType
from domain.objects.money import Money
from domain.repositories.account_repository import AccountRepository
from domain.repositories.transaction_repository import TransactionRepository
from domain.repositories.unit_of_work import AbstractUnitOfWork
from domain.repositories.user_repository import UserRepository
from shared.exceptions.domain import (
    SameAccountTransferError,
    UserNotFoundError,
    AccountNotFoundError,
    InsufficientFundsError,
)


@dataclass
class CreateTransferCommand:
    dto: CreateTransferDTO


class CreateTransferHandler:
    def __init__(
        self,
        user_repository: UserRepository,
        account_repository: AccountRepository,
        transaction_repository: TransactionRepository,
        uow: AbstractUnitOfWork,
    ):
        self.user_repository = user_repository
        self.account_repository = account_repository
        self.transaction_repository = transaction_repository
        self.uow = uow

    async def handle(self, command: CreateTransferCommand):
        dto = command.dto

        if dto.source_account_uuid == dto.target_account_uuid:
            raise SameAccountTransferError()

        user = await self.user_repository.get_by_id(dto.user_id)
        if not user or not user.is_active:
            raise UserNotFoundError()

        source = await self.account_repository.get_by_uuid_and_user_id(
            account_uuid=dto.source_account_uuid, user_id=dto.user_id
        )
        if not source:
            raise AccountNotFoundError(account_uuid=dto.source_account_uuid)

        target = await self.account_repository.get_by_uuid_and_user_id(
            account_uuid=dto.target_account_uuid, user_id=dto.user_id
        )
        if not target:
            raise AccountNotFoundError(account_uuid=dto.target_account_uuid)

        money = Money(dto.amount, dto.currency)
        transfer_date = dto.transfer_date or date.today()

        if not source.can_withdraw(money):
            raise InsufficientFundsError(
                required_amount=float(money.amount),
                available_amount=float(source.current_balance.amount),
            )

        shared_transfer_uuid = str(uuid.uuid4())

        outgoing = Transaction.create_new(
            user_id=cast(int, user.id),
            account_id=cast(int, source.id),
            category_id=None,
            transaction_type=TransactionType.TRANSFER,
            amount=money,
            transaction_date=transfer_date,
            description=dto.description or f"Transferencia a {target.name}",
            notes=dto.notes,
        )
        outgoing.transfer_uuid = shared_transfer_uuid

        incoming = Transaction.create_new(
            user_id=cast(int, user.id),
            account_id=cast(int, target.id),
            category_id=None,
            transaction_type=TransactionType.TRANSFER,
            amount=money,
            transaction_date=transfer_date,
            description=dto.description or f"Transferencia de {source.name}",
        )
        incoming.transfer_uuid = shared_transfer_uuid

        source_new_balance = source.current_balance.subtract(money)
        target_new_balance = target.current_balance.add(money)

        async with self.uow:
            source.update_balance(source_new_balance)
            target.update_balance(target_new_balance)

            await self.account_repository.update(source)
            await self.account_repository.update(target)

            saved_outgoing = await self.transaction_repository.create(outgoing)
            await self.transaction_repository.create(incoming)

            await self.uow.commit()

        return TransferResponseDTO(
            transfer_uuid=shared_transfer_uuid,
            amount=money.amount,
            transfer_date=transfer_date,
            source_account_name=source.name,
            source_account_uuid=source.uuid,
            target_account_name=target.name,
            target_account_uuid=target.uuid,
            creation_date=saved_outgoing.creation_date,
        )

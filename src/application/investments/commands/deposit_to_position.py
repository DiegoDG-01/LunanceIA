from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import cast

from domain.entities.transaction import Transaction
from domain.objects.enums import TransactionType
from domain.objects.money import Money
from domain.repositories.account_repository import AccountRepository
from domain.repositories.investment_position_repository import (
    InvestmentPositionRepository,
)
from domain.repositories.transaction_repository import TransactionRepository
from domain.repositories.unit_of_work import AbstractUnitOfWork
from domain.repositories.user_repository import UserRepository
from application.dto.investment_position_dto import (
    PositionMovementDTO,
    PositionResponseDTO,
)
from application.investments.services.position_overflow import PositionOverflowService
from shared.exceptions.domain import (
    AccountNotFoundError,
    InsufficientFundsError,
    InvestmentPositionNotFoundError,
    UserNotFoundError,
)


@dataclass
class DepositToPositionCommand:
    dto: PositionMovementDTO


class DepositToPositionHandler:
    """Mueve dinero del saldo disponible de la cuenta hacia un apartado.

    Si el apartado tiene tope, lo que no cabe sigue por su cadena de destinos
    y lo que ningún apartado absorbe regresa al disponible. La transacción se
    registra por el neto que realmente salió del disponible: depositar 500 en
    un apartado que rebota 200 mueve 300, y eso es lo que ve el usuario.
    """

    def __init__(
        self,
        user_repository: UserRepository,
        account_repository: AccountRepository,
        position_repository: InvestmentPositionRepository,
        transaction_repository: TransactionRepository,
        overflow_service: PositionOverflowService,
        uow: AbstractUnitOfWork,
    ):
        self.user_repository = user_repository
        self.account_repository = account_repository
        self.position_repository = position_repository
        self.transaction_repository = transaction_repository
        self.overflow_service = overflow_service
        self.uow = uow

    async def handle(self, command: DepositToPositionCommand) -> PositionResponseDTO:
        dto = command.dto

        user = await self.user_repository.get_by_id(dto.user_id)
        if not user or not user.is_active:
            raise UserNotFoundError()

        async with self.uow:
            preview = await self.position_repository.get_by_uuid_and_user_id(
                dto.position_uuid, dto.user_id
            )
            if not preview:
                raise InvestmentPositionNotFoundError(dto.position_uuid)

            # Orden de bloqueo consistente en todos los flujos: cuenta -> apartado
            account = await self.account_repository.get_by_id(
                account_id=preview.account_id, for_update=True
            )
            if not account or account.user_id != dto.user_id:
                raise AccountNotFoundError(str(preview.account_id))

            position = await self.position_repository.get_by_id(
                position_id=cast(int, preview.id), for_update=True
            )
            if not position:
                raise InvestmentPositionNotFoundError(dto.position_uuid)

            money = Money(dto.amount, dto.currency)

            if not account.can_withdraw(money):
                raise InsufficientFundsError(
                    required_amount=float(dto.amount),
                    available_amount=float(account.current_balance.amount),
                )

            overflow = position.deposit(money)
            await self.position_repository.update(position)

            returned = Money(Decimal(0), money.currency)
            if overflow.amount > 0:
                returned = await self.overflow_service.spill(position, overflow)

            moved = Money(money.amount - returned.amount, money.currency)
            if moved.amount > 0:
                account.update_balance(account.current_balance.subtract(moved))
                await self.account_repository.update(account)

                movement = Transaction.create_new(
                    user_id=cast(int, user.id),
                    account_id=cast(int, account.id),
                    category_id=None,
                    transaction_type=TransactionType.TRANSFER,
                    amount=moved,
                    transaction_date=date.today(),
                    description=f"Apartado a {position.name}",
                )
                movement.position_id = position.id
                await self.transaction_repository.create(movement)

            target_uuid = await self.overflow_service.target_uuid(position)

            await self.uow.commit()

        return PositionResponseDTO.from_entity(
            position,
            account_uuid=cast(str, account.uuid),
            account_available_balance=account.current_balance.amount,
            overflow_position_uuid=target_uuid,
        )

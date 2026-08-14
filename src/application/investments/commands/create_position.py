from dataclasses import dataclass
from datetime import date
from typing import cast

from domain.entities.investment_position import InvestmentPosition
from domain.entities.transaction import Transaction
from domain.objects.enums import AccountType, TransactionType
from domain.objects.money import Money
from domain.repositories.account_repository import AccountRepository
from domain.repositories.investment_position_repository import (
    InvestmentPositionRepository,
)
from domain.repositories.transaction_repository import TransactionRepository
from domain.repositories.unit_of_work import AbstractUnitOfWork
from domain.repositories.user_repository import UserRepository
from application.dto.investment_position_dto import (
    CreatePositionDTO,
    PositionResponseDTO,
)
from shared.exceptions.domain import (
    AccountInactiveError,
    AccountNotFoundError,
    InsufficientFundsError,
    PositionAccountTypeNotAllowedError,
    UserNotFoundError,
)


@dataclass
class CreatePositionCommand:
    dto: CreatePositionDTO


class CreatePositionHandler:
    """Crea un apartado de inversión moviendo dinero del saldo disponible.

    El monto sale de current_balance de la cuenta y queda dentro del apartado;
    a partir de aquí no es transferible hasta regresarlo al disponible.
    """

    def __init__(
        self,
        user_repository: UserRepository,
        account_repository: AccountRepository,
        position_repository: InvestmentPositionRepository,
        transaction_repository: TransactionRepository,
        uow: AbstractUnitOfWork,
    ):
        self.user_repository = user_repository
        self.account_repository = account_repository
        self.position_repository = position_repository
        self.transaction_repository = transaction_repository
        self.uow = uow

    async def handle(self, command: CreatePositionCommand) -> PositionResponseDTO:
        dto = command.dto

        user = await self.user_repository.get_by_id(dto.user_id)
        if not user or not user.is_active:
            raise UserNotFoundError()

        async with self.uow:
            preview = await self.account_repository.get_by_uuid_and_user_id(
                dto.account_uuid, dto.user_id
            )
            if not preview:
                raise AccountNotFoundError(dto.account_uuid)

            account = await self.account_repository.get_by_id(
                account_id=cast(int, preview.id), for_update=True
            )
            if not account or account.user_id != dto.user_id:
                raise AccountNotFoundError(dto.account_uuid)

            if account.account_type == AccountType.CREDIT_CARD:
                raise PositionAccountTypeNotAllowedError(account.account_type.value)

            if not account.is_active:
                raise AccountInactiveError(cast(int, account.id))

            money = Money(dto.amount, dto.currency)

            if not account.can_withdraw(money):
                raise InsufficientFundsError(
                    required_amount=float(dto.amount),
                    available_amount=float(account.current_balance.amount),
                )

            position = InvestmentPosition.create_new(
                account_id=cast(int, account.id),
                name=dto.name,
                position_type=dto.position_type,
                initial_balance=money,
                annual_rate=dto.annual_rate,
                interest_type=dto.interest_type,
                term_days=dto.term_days,
                maturity_date=dto.maturity_date,
                lock_period_end_date=dto.lock_period_end_date,
                early_withdrawal_penalty=dto.early_withdrawal_penalty,
                on_maturity=dto.on_maturity,
            )

            account.update_balance(account.current_balance.subtract(money))

            saved_position = await self.position_repository.create(position)
            await self.account_repository.update(account)

            movement = Transaction.create_new(
                user_id=cast(int, user.id),
                account_id=cast(int, account.id),
                category_id=None,
                transaction_type=TransactionType.TRANSFER,
                amount=money,
                transaction_date=date.today(),
                description=f"Apartado a {saved_position.name}",
            )
            movement.position_id = saved_position.id
            await self.transaction_repository.create(movement)

            await self.uow.commit()

        return PositionResponseDTO.from_entity(
            saved_position,
            account_uuid=cast(str, account.uuid),
            account_available_balance=account.current_balance.amount,
        )

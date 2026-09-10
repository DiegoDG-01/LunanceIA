from dataclasses import dataclass
from datetime import date
from typing import cast

from application.dto.investment_position_dto import (
    PositionResponseDTO,
    UpdatePositionDTO,
)
from application.investments.services.position_overflow import PositionOverflowService
from domain.entities.transaction import Transaction
from domain.objects.enums import OverflowAction, TransactionType
from domain.repositories.account_repository import AccountRepository
from domain.repositories.investment_position_repository import (
    InvestmentPositionRepository,
)
from domain.repositories.transaction_repository import TransactionRepository
from domain.repositories.unit_of_work import AbstractUnitOfWork
from domain.repositories.user_repository import UserRepository
from shared.exceptions.domain import (
    AccountNotFoundError,
    InvalidOverflowTargetError,
    InvestmentPositionNotFoundError,
    UserNotFoundError,
)


@dataclass
class UpdatePositionCommand:
    dto: UpdatePositionDTO


class UpdatePositionHandler:
    """Actualiza el nombre y la configuración de tope de un apartado.

    Es el único camino para armar una cadena de desbordamiento: el apartado
    destino tiene que existir antes de que otro lo apunte, así que no se puede
    configurar al crear. Bajar el tope por debajo del saldo actual no espera al
    job del día siguiente — el excedente sale en el momento.
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

    async def handle(self, command: UpdatePositionCommand) -> PositionResponseDTO:
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

            if dto.name is not None:
                position.name = dto.name

            excess = None
            if dto.cap_provided:
                target_id = await self._resolve_target(dto, position)
                excess = position.configure_cap(
                    max_balance=dto.max_balance,
                    overflow_action=dto.overflow_action,
                    overflow_position_id=target_id,
                )

            await self.position_repository.update(position)

            if excess is not None and excess.amount > 0:
                to_available = await self.overflow_service.spill(position, excess)
                if to_available.amount > 0:
                    account.update_balance(account.current_balance.add(to_available))
                    await self.account_repository.update(account)

                    movement = Transaction.create_new(
                        user_id=cast(int, user.id),
                        account_id=cast(int, account.id),
                        category_id=None,
                        transaction_type=TransactionType.TRANSFER,
                        amount=to_available,
                        transaction_date=date.today(),
                        description=f"Excedente del apartado {position.name}",
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

    async def _resolve_target(self, dto: UpdatePositionDTO, position) -> int | None:
        """Traduce el uuid del apartado destino a su id y valida la cadena."""
        if dto.overflow_action != OverflowAction.TO_POSITION:
            return None

        if not dto.overflow_position_uuid:
            raise InvalidOverflowTargetError(
                "desbordar a un apartado requiere indicar cuál"
            )

        target = await self.position_repository.get_by_uuid_and_user_id(
            dto.overflow_position_uuid, dto.user_id
        )
        if not target:
            raise InvalidOverflowTargetError(
                f"el apartado {dto.overflow_position_uuid} no existe"
            )

        await self.overflow_service.validate_target(position, cast(int, target.id))
        return cast(int, target.id)

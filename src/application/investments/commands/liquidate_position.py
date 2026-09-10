from dataclasses import dataclass
from datetime import date
from typing import cast

from application.dto.investment_position_dto import (
    LiquidatePositionDTO,
    LiquidatePositionResponseDTO,
)
from domain.entities.notification import Notification, NotificationType
from domain.entities.transaction import Transaction
from domain.objects.enums import TransactionType
from domain.repositories.account_repository import AccountRepository
from domain.repositories.investment_position_repository import (
    InvestmentPositionRepository,
)
from domain.repositories.notification_repository import NotificationRepository
from domain.repositories.transaction_repository import TransactionRepository
from domain.repositories.unit_of_work import AbstractUnitOfWork
from domain.repositories.user_repository import UserRepository
from shared.exceptions.domain import (
    AccountNotFoundError,
    InvestmentPositionNotFoundError,
    UserNotFoundError,
)


@dataclass
class LiquidatePositionCommand:
    dto: LiquidatePositionDTO


class LiquidatePositionHandler:
    """Cierra un apartado y regresa capital + rendimiento al saldo disponible.

    Liquidar un plazo fijo antes del vencimiento aplica la penalización sobre
    el rendimiento acumulado; durante el periodo de permanencia no se permite.

    Si otros apartados desbordaban hacia este, su excedente pasa a ir al saldo
    disponible: no heredan la cadena del apartado liquidado, para no alargar
    cadenas que el usuario nunca configuró.
    """

    def __init__(
        self,
        user_repository: UserRepository,
        account_repository: AccountRepository,
        position_repository: InvestmentPositionRepository,
        transaction_repository: TransactionRepository,
        notification_repository: NotificationRepository,
        uow: AbstractUnitOfWork,
    ):
        self.user_repository = user_repository
        self.account_repository = account_repository
        self.position_repository = position_repository
        self.transaction_repository = transaction_repository
        self.notification_repository = notification_repository
        self.uow = uow

    async def handle(
        self, command: LiquidatePositionCommand
    ) -> LiquidatePositionResponseDTO:
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

            payout = position.liquidate(date.today())
            account.update_balance(account.current_balance.add(payout))

            await self.position_repository.update(position)
            await self.account_repository.update(account)

            movement = Transaction.create_new(
                user_id=cast(int, user.id),
                account_id=cast(int, account.id),
                category_id=None,
                transaction_type=TransactionType.TRANSFER,
                amount=payout,
                transaction_date=date.today(),
                description=f"Liquidación del apartado {position.name}",
            )
            movement.position_id = position.id
            await self.transaction_repository.create(movement)

            await self._repoint_sources_to_available(position, account.user_id)

            await self.uow.commit()

        return LiquidatePositionResponseDTO(
            position_uuid=cast(str, position.uuid),
            name=position.name,
            payout_amount=payout.amount,
            currency=payout.currency,
            status=position.status,
            account_uuid=cast(str, account.uuid),
            account_available_balance=account.current_balance.amount,
        )

    async def _repoint_sources_to_available(self, position, user_id: int) -> None:
        """Corta las cadenas que apuntaban al apartado recién liquidado.

        Solo un apartado a la vista puede ser destino, así que esto únicamente
        tiene efecto aquí: el job de vencimientos liquida plazos fijos, que
        nadie puede estar apuntando.
        """
        sources = await self.position_repository.get_by_overflow_target(
            position_id=cast(int, position.id), for_update=True
        )
        for source in sources:
            source.clear_overflow_target()
            await self.position_repository.update(source)

            notification = Notification.create_new(
                user_id=user_id,
                title=f"El excedente de {source.name} cambió de destino",
                message=(
                    f"Liquidaste el apartado {position.name}, así que el "
                    f"excedente de {source.name} ahora va a tu saldo disponible."
                ),
                type=NotificationType.PUSH,
                is_read=False,
            )
            await self.notification_repository.create(notification)

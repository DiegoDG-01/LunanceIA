import logging
from dataclasses import dataclass
from datetime import date
from typing import cast

from domain.entities.notification import Notification, NotificationType
from domain.entities.transaction import Transaction
from domain.objects.enums import MaturityAction, TransactionType
from domain.repositories.account_repository import AccountRepository
from domain.repositories.investment_position_repository import (
    InvestmentPositionRepository,
)
from domain.repositories.notification_repository import NotificationRepository
from domain.repositories.transaction_repository import TransactionRepository
from domain.repositories.unit_of_work import AbstractUnitOfWork


logger = logging.getLogger(__name__)


@dataclass
class ProcessMaturedPositionsCommand:
    target_date: date


class ProcessMaturedPositionsHandler:
    """Procesa los plazos fijos vencidos según su acción configurada.

    AUTO_RENEW reinvierte capital + rendimiento por el mismo plazo;
    LIQUIDATE regresa capital + rendimiento al saldo disponible;
    HOLD deja el apartado en estado MATURED (sin rendir) esperando al usuario.

    Debe correr después del job de rendimientos: el día del vencimiento
    todavía genera rendimiento y este job lo entrega completo.
    """

    def __init__(
        self,
        position_repository: InvestmentPositionRepository,
        account_repository: AccountRepository,
        transaction_repository: TransactionRepository,
        notification_repository: NotificationRepository,
        uow: AbstractUnitOfWork,
    ):
        self.position_repository = position_repository
        self.account_repository = account_repository
        self.transaction_repository = transaction_repository
        self.notification_repository = notification_repository
        self.uow = uow

    async def handle(self, command: ProcessMaturedPositionsCommand) -> dict:
        today = command.target_date
        renewed = 0
        liquidated = 0
        held = 0
        errors = 0

        previews = await self.position_repository.get_due_for_maturity(today)

        async with self.uow:
            for preview in previews:
                try:
                    # Orden de bloqueo consistente con los comandos de
                    # movimientos: cuenta -> apartado.
                    account = await self.account_repository.get_by_id(
                        account_id=preview.account_id, for_update=True
                    )
                    if not account:
                        errors += 1
                        continue

                    position = await self.position_repository.get_by_id(
                        position_id=cast(int, preview.id), for_update=True
                    )
                    if not position or not position.is_due_for_maturity(today):
                        continue

                    if position.on_maturity == MaturityAction.AUTO_RENEW:
                        position.renew(today)
                        await self.position_repository.update(position)

                        notification = Notification.create_new(
                            user_id=account.user_id,
                            title=f"Apartado {position.name} renovado",
                            message=(
                                f"Tu apartado {position.name} venció y se reinvirtió "
                                f"automáticamente por {position.term_days} días con un "
                                f"nuevo capital de {position.balance.amount}."
                            ),
                            type=NotificationType.PUSH,
                            is_read=False,
                        )
                        renewed += 1

                    elif position.on_maturity == MaturityAction.LIQUIDATE:
                        payout = position.liquidate(today)
                        account.update_balance(account.current_balance.add(payout))

                        movement = Transaction.create_new(
                            user_id=account.user_id,
                            account_id=cast(int, account.id),
                            category_id=None,
                            transaction_type=TransactionType.TRANSFER,
                            amount=payout,
                            transaction_date=today,
                            description=f"Vencimiento del apartado {position.name}",
                        )
                        movement.position_id = position.id

                        await self.account_repository.update(account)
                        await self.position_repository.update(position)
                        await self.transaction_repository.create(movement)

                        notification = Notification.create_new(
                            user_id=account.user_id,
                            title=f"Apartado {position.name} liquidado",
                            message=(
                                f"Tu apartado {position.name} venció y {payout.amount} "
                                f"se depositaron en el saldo disponible de {account.name}."
                            ),
                            type=NotificationType.PUSH,
                            is_read=False,
                        )
                        liquidated += 1

                    else:  # MaturityAction.HOLD
                        position.mark_matured()
                        await self.position_repository.update(position)

                        notification = Notification.create_new(
                            user_id=account.user_id,
                            title=f"Apartado {position.name} venció",
                            message=(
                                f"Tu apartado {position.name} llegó a su vencimiento "
                                f"con {position.total_value.amount}. Ya no genera "
                                f"rendimientos: decide si renovarlo o liquidarlo."
                            ),
                            type=NotificationType.PUSH,
                            is_read=False,
                        )
                        held += 1

                    await self.notification_repository.create(notification)
                    logger.info(
                        f"processed maturity for position {position.id} "
                        f"({position.on_maturity.value})"
                    )

                except Exception as e:
                    errors += 1
                    logger.error(
                        f"failed to process maturity for position {preview.id}: {e}",
                        exc_info=True,
                    )

            await self.uow.commit()

        return {
            "renewed": renewed,
            "liquidated": liquidated,
            "held": held,
            "errors": errors,
        }

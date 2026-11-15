"""Edita una operación: reemplaza sus datos (el tipo, la cuenta y el valor no cambian),
ajusta el disponible por la diferencia y recalcula la tenencia. Si el cambio deja una venta
posterior sin títulos, se rechaza y no se guarda nada."""

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import cast

from application.securities.dto import HoldingDTO, TradeDTO, TradeResultDTO
from application.securities.services.trade_bookkeeper import TradeBookkeeper
from domain.repositories.unit_of_work import AbstractUnitOfWork
from shared.exceptions.domain import SecurityTradeNotFoundError


@dataclass
class UpdateTradeCommand:
    user_id: int
    trade_uuid: str
    trade_date: date
    quantity: Decimal | None = None
    price: Decimal | None = None
    fees: Decimal | None = None
    tax_withheld: Decimal | None = None
    gross_amount: Decimal | None = None
    split_from: int | None = None
    split_to: int | None = None
    notes: str | None = None


class UpdateTradeHandler:
    def __init__(
        self,
        *,
        bookkeeper: TradeBookkeeper,
        uow: AbstractUnitOfWork,
        today: Callable[[], date] = lambda: datetime.now(UTC).date(),
    ) -> None:
        self._books = bookkeeper
        self._uow = uow
        self._today = today

    async def handle(self, command: UpdateTradeCommand) -> TradeResultDTO:
        books = self._books
        async with self._uow:
            # Con bloqueo: ver `TradeBookkeeper`.
            old = await books.trades.get_by_uuid_and_user_id(
                command.trade_uuid, command.user_id, for_update=True
            )
            if old is None:
                raise SecurityTradeNotFoundError(command.trade_uuid)
            context = await books.lock(
                account_id=old.account_id,
                user_id=command.user_id,
                instrument_id=old.instrument_id,
            )

            trade = replace(old)
            trade.change(
                trade_date=command.trade_date,
                quantity=command.quantity,
                price=command.price,
                fees=command.fees,
                tax_withheld=command.tax_withheld,
                gross_amount=command.gross_amount,
                split_from=command.split_from,
                split_to=command.split_to,
                notes=command.notes,
            )
            books.check_date(trade, self._today())

            trade.transaction_id = await books.move_money(context, old=old, new=trade)
            trade = await books.trades.update(trade)
            holding = await books.recompute(context)
            await books.instruments.track_since(old.instrument_id, trade.trade_date)
            await self._uow.commit()

        account_uuid = cast(str, context.account.uuid)
        return TradeResultDTO(
            trade=TradeDTO.build(
                trade, account_uuid=account_uuid, instrument=context.instrument
            ),
            holding=(
                HoldingDTO.build(
                    holding,
                    account_uuid=account_uuid,
                    account_name=context.account.name,
                    instrument=context.instrument,
                )
                if holding
                else None
            ),
            account_available_balance=context.account.current_balance.amount,
        )

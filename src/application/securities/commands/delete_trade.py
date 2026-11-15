"""Borra una operación: revierte su movimiento de dinero y recalcula la tenencia. Si sin ella
una venta posterior se queda sin títulos, se rechaza."""

from dataclasses import dataclass
from typing import cast

from application.securities.dto import HoldingDTO, TradeResultDTO
from application.securities.services.trade_bookkeeper import TradeBookkeeper
from domain.repositories.unit_of_work import AbstractUnitOfWork
from shared.exceptions.domain import SecurityTradeNotFoundError


@dataclass
class DeleteTradeCommand:
    user_id: int
    trade_uuid: str


class DeleteTradeHandler:
    def __init__(self, *, bookkeeper: TradeBookkeeper, uow: AbstractUnitOfWork) -> None:
        self._books = bookkeeper
        self._uow = uow

    async def handle(self, command: DeleteTradeCommand) -> TradeResultDTO:
        books = self._books
        async with self._uow:
            # Con bloqueo: ver `TradeBookkeeper`.
            trade = await books.trades.get_by_uuid_and_user_id(
                command.trade_uuid, command.user_id, for_update=True
            )
            if trade is None:
                raise SecurityTradeNotFoundError(command.trade_uuid)
            context = await books.lock(
                account_id=trade.account_id,
                user_id=command.user_id,
                instrument_id=trade.instrument_id,
            )
            await books.move_money(context, old=trade, new=None)
            await books.trades.delete(cast(int, trade.id))
            holding = await books.recompute(context)
            await self._uow.commit()

        return TradeResultDTO(
            trade=None,
            holding=(
                HoldingDTO.build(
                    holding,
                    account_uuid=cast(str, context.account.uuid),
                    account_name=context.account.name,
                    instrument=context.instrument,
                )
                if holding
                else None
            ),
            account_available_balance=context.account.current_balance.amount,
        )

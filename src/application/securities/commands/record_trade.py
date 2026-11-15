"""Registra una operación: mueve el dinero, recalcula la tenencia y pone el valor en
seguimiento desde la fecha de la operación (el backfill corre después, en segundo plano)."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import cast

from application.securities.dto import HoldingDTO, TradeDTO, TradeResultDTO
from application.securities.services.trade_bookkeeper import TradeBookkeeper
from domain.entities.securities.security_trade import SecurityTrade
from domain.objects.enums import TradeType
from domain.repositories.unit_of_work import AbstractUnitOfWork
from shared.exceptions.domain import AccountNotFoundError, InstrumentNotFoundError


@dataclass
class RecordTradeCommand:
    user_id: int
    account_uuid: str
    instrument_uuid: str
    trade_type: TradeType
    trade_date: date
    quantity: Decimal | None = None
    price: Decimal | None = None
    fees: Decimal | None = None
    tax_withheld: Decimal | None = None
    gross_amount: Decimal | None = None
    split_from: int | None = None
    split_to: int | None = None
    notes: str | None = None


class RecordTradeHandler:
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

    async def handle(self, command: RecordTradeCommand) -> TradeResultDTO:
        books = self._books
        async with self._uow:
            # Con bloqueo: ver `TradeBookkeeper`.
            preview = await books.accounts.get_by_uuid_and_user_id(
                command.account_uuid, command.user_id, for_update=True
            )
            if preview is None:
                raise AccountNotFoundError(command.account_uuid)
            instrument = await books.instruments.get_by_uuid(command.instrument_uuid)
            if instrument is None:
                raise InstrumentNotFoundError(command.instrument_uuid)
            context = await books.lock(
                account_id=cast(int, preview.id),
                user_id=command.user_id,
                instrument_id=cast(int, instrument.id),
            )

            trade = SecurityTrade.create(
                user_id=command.user_id,
                account_id=cast(int, context.account.id),
                instrument_id=cast(int, context.instrument.id),
                trade_type=command.trade_type,
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

            trade = await books.trades.create(trade)
            trade.transaction_id = await books.move_money(context, old=None, new=trade)
            trade = await books.trades.update(trade)
            holding = await books.recompute(context, changed_from=trade.trade_date)
            await books.instruments.track_since(
                cast(int, context.instrument.id), trade.trade_date
            )
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

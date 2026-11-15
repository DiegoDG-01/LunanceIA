from dataclasses import dataclass
from typing import cast

from application.securities.dto import TradeDTO
from domain.repositories.accounts.account_repository import AccountRepository
from domain.repositories.securities.instrument_repository import InstrumentRepository
from domain.repositories.securities.trade_repository import SecurityTradeRepository
from shared.exceptions.domain import AccountNotFoundError, InstrumentNotFoundError


@dataclass
class ListTradesQuery:
    user_id: int
    account_uuid: str | None = None
    instrument_uuid: str | None = None
    limit: int = 100
    offset: int = 0


class ListTradesHandler:
    def __init__(
        self,
        *,
        account_repository: AccountRepository,
        instrument_repository: InstrumentRepository,
        trade_repository: SecurityTradeRepository,
    ) -> None:
        self._accounts = account_repository
        self._instruments = instrument_repository
        self._trades = trade_repository

    async def handle(self, query: ListTradesQuery) -> list[TradeDTO]:
        account_id = instrument_id = None
        if query.account_uuid:
            account = await self._accounts.get_by_uuid_and_user_id(
                query.account_uuid, query.user_id
            )
            if account is None:
                raise AccountNotFoundError(query.account_uuid)
            account_id = account.id
        if query.instrument_uuid:
            instrument = await self._instruments.get_by_uuid(query.instrument_uuid)
            if instrument is None:
                raise InstrumentNotFoundError(query.instrument_uuid)
            instrument_id = instrument.id

        trades = await self._trades.list_for_user(
            query.user_id,
            account_id=account_id,
            instrument_id=instrument_id,
            limit=query.limit,
            offset=query.offset,
        )
        accounts = {
            a.id: a
            for a in await self._accounts.get_bulk_by_ids(
                list({t.account_id for t in trades})
            )
        }
        instruments = await self._instruments.get_by_ids(
            [t.instrument_id for t in trades]
        )
        return [
            TradeDTO.build(
                t,
                account_uuid=cast(str, accounts[t.account_id].uuid),
                instrument=instruments[t.instrument_id],
            )
            for t in trades
        ]

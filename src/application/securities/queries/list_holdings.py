"""Tenencias del usuario con su valor al último cierre guardado."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import cast

from application.securities.dto import HoldingDTO, TradeDTO
from application.securities.services.valuation import HoldingValuer
from domain.entities.securities.security_holding import SecurityHolding
from domain.repositories.accounts.account_repository import AccountRepository
from domain.repositories.securities.instrument_repository import InstrumentRepository
from domain.repositories.securities.trade_repository import (
    SecurityHoldingRepository,
    SecurityTradeRepository,
)
from shared.exceptions.domain import AccountNotFoundError, SecurityHoldingNotFoundError


@dataclass
class ListHoldingsQuery:
    user_id: int
    account_uuid: str | None = None
    include_closed: bool = False


@dataclass
class GetHoldingQuery:
    user_id: int
    holding_uuid: str


@dataclass(frozen=True, slots=True)
class HoldingDetail:
    holding: HoldingDTO
    trades: list[TradeDTO]


class HoldingQueries:
    def __init__(
        self,
        *,
        account_repository: AccountRepository,
        instrument_repository: InstrumentRepository,
        holding_repository: SecurityHoldingRepository,
        trade_repository: SecurityTradeRepository,
        valuer: HoldingValuer,
        today: Callable[[], date] = lambda: datetime.now(UTC).date(),
    ) -> None:
        self._accounts = account_repository
        self._instruments = instrument_repository
        self._holdings = holding_repository
        self._trades = trade_repository
        self._valuer = valuer
        self._today = today

    async def list_holdings(self, query: ListHoldingsQuery) -> list[HoldingDTO]:
        account_id = None
        if query.account_uuid:
            account = await self._accounts.get_by_uuid_and_user_id(
                query.account_uuid, query.user_id
            )
            if account is None:
                raise AccountNotFoundError(query.account_uuid)
            account_id = account.id
        holdings = await self._holdings.list_for_user(
            query.user_id, account_id=account_id, include_closed=query.include_closed
        )
        return await self._build(holdings)

    async def get_holding(self, query: GetHoldingQuery) -> HoldingDetail:
        holding = await self._holdings.get_by_uuid_and_user_id(
            query.holding_uuid, query.user_id
        )
        if holding is None:
            raise SecurityHoldingNotFoundError(query.holding_uuid)
        [dto] = await self._build([holding])
        trades = await self._trades.list_for_holding(
            holding.account_id, holding.instrument_id
        )
        return HoldingDetail(
            holding=dto,
            trades=[
                TradeDTO.build(
                    t, account_uuid=dto.account_uuid, instrument=dto.instrument
                )
                for t in reversed(trades)
            ],
        )

    async def _build(self, holdings: list[SecurityHolding]) -> list[HoldingDTO]:
        if not holdings:
            return []
        accounts = {
            a.id: a
            for a in await self._accounts.get_bulk_by_ids(
                list({h.account_id for h in holdings})
            )
        }
        instruments = await self._instruments.get_by_ids(
            [h.instrument_id for h in holdings]
        )
        valuations = await self._valuer.value(holdings, instruments, self._today())
        return [
            HoldingDTO.build(
                h,
                account_uuid=cast(str, accounts[h.account_id].uuid),
                account_name=accounts[h.account_id].name,
                instrument=instruments[h.instrument_id],
                valuation=valuations.get(cast(int, h.id)),
            )
            for h in holdings
        ]

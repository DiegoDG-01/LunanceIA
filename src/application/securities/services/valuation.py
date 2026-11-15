"""Valúa tenencias con el último cierre guardado y, si no son en pesos, con el FIX."""

from collections.abc import Sequence
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import cast

from domain.entities.securities.instrument import Instrument
from domain.entities.securities.security_holding import SecurityHolding
from domain.repositories.securities.price_repository import (
    ExchangeRateRepository,
    InstrumentPriceRepository,
)

CENT = Decimal("0.01")
BASE_CURRENCY = "MXN"


def _money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


class HoldingValuer:
    def __init__(
        self,
        *,
        price_repository: InstrumentPriceRepository,
        fx_repository: ExchangeRateRepository,
    ) -> None:
        self._prices = price_repository
        self._fx = fx_repository

    async def value(
        self,
        holdings: Sequence[SecurityHolding],
        instruments: dict[int, Instrument],
        as_of: date,
    ) -> dict[int, dict]:
        """Por id de tenencia, los campos de valuación de `HoldingDTO`."""
        latest = await self._prices.latest_on_or_before(
            [h.instrument_id for h in holdings], as_of
        )
        rates: dict[str, Decimal | None] = {BASE_CURRENCY: Decimal(1)}
        result: dict[int, dict] = {}
        for holding in holdings:
            price = latest.get(holding.instrument_id)
            if price is None:
                continue
            currency = instruments[holding.instrument_id].currency
            if currency not in rates:
                rate = await self._fx.latest_on_or_before(
                    currency, BASE_CURRENCY, as_of
                )
                rates[currency] = rate.rate if rate else None
            fx_rate = rates[currency]
            market_value = _money(holding.quantity * price.close)
            unrealized = market_value - holding.cost_basis
            result[cast(int, holding.id)] = {
                "last_price": price.close,
                "last_price_date": price.price_date,
                "market_value": market_value,
                "unrealized_pnl": unrealized,
                "unrealized_pnl_pct": (
                    (unrealized * 100 / holding.cost_basis).quantize(
                        CENT, rounding=ROUND_HALF_UP
                    )
                    if holding.cost_basis > 0
                    else None
                ),
                "fx_rate": fx_rate if currency != BASE_CURRENCY else None,
                "market_value_mxn": (
                    _money(market_value * fx_rate) if fx_rate is not None else None
                ),
            }
        return result

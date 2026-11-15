"""Fotos diarias de una tenencia a partir de sus operaciones, cierres y tipos de cambio.

Un día de calendario por foto. El estado del día incluye las operaciones de ese día. Los días
sin cierre usan el último conocido (`price_date` dice de cuándo es); antes del primer cierre
no hay valuación. Lo mismo con el tipo de cambio para valores que no son en pesos.
"""

from collections.abc import Sequence
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from domain.entities.securities.holding_snapshot import HoldingSnapshot
from domain.entities.securities.security_trade import SecurityTrade
from domain.services.holding_ledger import HoldingState, apply_trade, trade_order

CENT = Decimal("0.01")


def _money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


class _Carry:
    """El último punto (fecha, valor) hasta un día, recorriendo una serie ordenada."""

    def __init__(self, points: Sequence[tuple[date, Decimal]]) -> None:
        self._points = sorted(points)
        self._next = 0
        self.current: tuple[date, Decimal] | None = None

    def until(self, day: date) -> tuple[date, Decimal] | None:
        while self._next < len(self._points) and self._points[self._next][0] <= day:
            self.current = self._points[self._next]
            self._next += 1
        return self.current


def daily_snapshots(
    *,
    holding_id: int,
    trades: Sequence[SecurityTrade],
    start: date,
    end: date,
    closes: Sequence[tuple[date, Decimal]],
    fx_rates: Sequence[tuple[date, Decimal]] | None = None,
    symbol: str = "",
) -> list[HoldingSnapshot]:
    """Fotos de `start` a `end` (incluidos). `closes` y `fx_rates` deben traer también el
    último punto anterior a `start` para arrastrarlo. `fx_rates` None: el valor es en pesos."""
    ordered = sorted(trades, key=trade_order)
    state = HoldingState()
    index = 0
    while index < len(ordered) and ordered[index].trade_date < start:
        apply_trade(state, ordered[index], symbol=symbol)
        index += 1

    prices = _Carry(closes)
    rates = _Carry(fx_rates or [])
    snapshots: list[HoldingSnapshot] = []
    day = start
    while day <= end:
        while index < len(ordered) and ordered[index].trade_date == day:
            apply_trade(state, ordered[index], symbol=symbol)
            index += 1
        snapshot = HoldingSnapshot(
            holding_id=holding_id,
            snapshot_date=day,
            quantity=state.quantity,
            cost_basis=state.cost_basis,
            realized_pnl=state.realized,
            dividends=state.dividends,
        )
        price = prices.until(day)
        if price is not None:
            snapshot.price_date, snapshot.close = price
            snapshot.market_value = _money(state.quantity * price[1])
            snapshot.unrealized_pnl = snapshot.market_value - snapshot.cost_basis
            if fx_rates is None:
                snapshot.market_value_mxn = snapshot.market_value
            elif (rate := rates.until(day)) is not None:
                snapshot.fx_rate = rate[1]
                snapshot.market_value_mxn = _money(snapshot.market_value * rate[1])
        snapshots.append(snapshot)
        day += timedelta(days=1)
    return snapshots

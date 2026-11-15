"""Recalcula una tenencia a partir de sus operaciones, en orden, con costo promedio.

- Compra: suma títulos y costo (precio × cantidad + comisión).
- Venta: resta títulos y la parte proporcional del costo; la ganancia realizada es lo
  vendido menos la comisión menos ese costo (antes de impuestos).
- Dividendo: suma el neto recibido a `dividends`.
- Split: multiplica los títulos por `split_to / split_from`; el costo total no cambia.

Si en algún día una venta o un split piden más títulos de los que hay, lanza
`InsufficientSharesError`: así se rechaza también editar o borrar una operación pasada que
deje en negativo una venta posterior.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from domain.entities.securities.security_trade import SecurityTrade
from domain.objects.enums import HoldingStatus, TradeType
from shared.exceptions.domain import InsufficientSharesError, InvalidSecurityTradeError

ZERO = Decimal(0)
QUANTITY_STEP = Decimal("0.00000001")
PRICE_STEP = Decimal("0.000001")
CENT = Decimal("0.01")


@dataclass
class HoldingState:
    quantity: Decimal = ZERO
    # Sin redondear mientras se recorre; se redondea al guardar.
    cost: Decimal = ZERO
    realized_pnl: Decimal = ZERO
    dividends: Decimal = ZERO
    opened_at: date | None = None
    closed_at: date | None = None
    trades: int = 0

    @property
    def status(self) -> HoldingStatus:
        return HoldingStatus.OPEN if self.quantity > 0 else HoldingStatus.CLOSED

    @property
    def avg_cost(self) -> Decimal:
        if self.quantity <= 0:
            return ZERO
        return (self.cost / self.quantity).quantize(PRICE_STEP, rounding=ROUND_HALF_UP)

    @property
    def cost_basis(self) -> Decimal:
        return self.cost.quantize(CENT, rounding=ROUND_HALF_UP)

    @property
    def realized(self) -> Decimal:
        return self.realized_pnl.quantize(CENT, rounding=ROUND_HALF_UP)


def trade_order(trade: SecurityTrade) -> tuple:
    """Por fecha; el mismo día, en el orden en que se registraron (las nuevas al final)."""
    return (trade.trade_date, trade.id is None, trade.id or 0)


def replay(trades: Iterable[SecurityTrade], *, symbol: str = "") -> HoldingState:
    state = HoldingState()
    for trade in sorted(trades, key=trade_order):
        apply_trade(state, trade, symbol=symbol)
    return state


def apply_trade(state: HoldingState, trade: SecurityTrade, *, symbol: str = "") -> None:
    """Aplica una operación a `state` (en orden: ver `trade_order`)."""
    state.trades += 1
    if trade.trade_type is TradeType.BUY:
        if state.quantity.is_zero():
            state.opened_at = trade.trade_date
            state.closed_at = None
        state.quantity += trade.quantity
        state.cost += trade.quantity * trade.price + trade.fees
    elif trade.trade_type is TradeType.SELL:
        if trade.quantity > state.quantity:
            raise InsufficientSharesError(
                symbol,
                trade.trade_date.isoformat(),
                f"{state.quantity.normalize():f}",
                f"{trade.quantity.normalize():f}",
            )
        removed = state.cost * trade.quantity / state.quantity
        state.realized_pnl += trade.quantity * trade.price - trade.fees - removed
        state.quantity -= trade.quantity
        state.cost -= removed
        if state.quantity.is_zero():
            state.cost = ZERO
            state.closed_at = trade.trade_date
    elif trade.trade_type is TradeType.DIVIDEND:
        if state.opened_at is None:
            raise InvalidSecurityTradeError(
                f"no hay compras de {symbol} antes del dividendo del "
                f"{trade.trade_date.isoformat()}"
            )
        state.dividends += trade.cash_amount
    else:
        if state.quantity.is_zero():
            raise InsufficientSharesError(
                symbol, trade.trade_date.isoformat(), "0", "títulos para el split"
            )
        ratio = Decimal(trade.split_to or 1) / Decimal(trade.split_from or 1)
        state.quantity = (state.quantity * ratio).quantize(
            QUANTITY_STEP, rounding=ROUND_HALF_UP
        )

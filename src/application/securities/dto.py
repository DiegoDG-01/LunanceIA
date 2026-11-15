from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from domain.entities.securities.instrument import Instrument
from domain.entities.securities.security_holding import SecurityHolding
from domain.entities.securities.security_trade import SecurityTrade
from domain.objects.enums import HoldingStatus, TradeType


@dataclass(frozen=True, slots=True)
class TradeDTO:
    uuid: str
    account_uuid: str
    instrument: Instrument
    trade_type: TradeType
    trade_date: date
    quantity: Decimal
    price: Decimal
    fees: Decimal
    tax_withheld: Decimal
    gross_amount: Decimal | None
    cash_amount: Decimal
    split_from: int | None
    split_to: int | None
    notes: str | None
    created_at: datetime | None

    @classmethod
    def build(
        cls, trade: SecurityTrade, *, account_uuid: str, instrument: Instrument
    ) -> "TradeDTO":
        return cls(
            uuid=str(trade.uuid),
            account_uuid=account_uuid,
            instrument=instrument,
            trade_type=trade.trade_type,
            trade_date=trade.trade_date,
            quantity=trade.quantity,
            price=trade.price,
            fees=trade.fees,
            tax_withheld=trade.tax_withheld,
            gross_amount=trade.gross_amount,
            cash_amount=trade.cash_amount,
            split_from=trade.split_from,
            split_to=trade.split_to,
            notes=trade.notes,
            created_at=trade.created_at,
        )


@dataclass(frozen=True, slots=True)
class HoldingDTO:
    uuid: str
    account_uuid: str
    account_name: str
    instrument: Instrument
    quantity: Decimal
    avg_cost: Decimal
    cost_basis: Decimal
    realized_pnl: Decimal
    dividends: Decimal
    status: HoldingStatus
    opened_at: date | None
    closed_at: date | None
    # Valuación con el último cierre guardado (None si todavía no hay precios).
    last_price: Decimal | None = None
    last_price_date: date | None = None
    market_value: Decimal | None = None
    unrealized_pnl: Decimal | None = None
    unrealized_pnl_pct: Decimal | None = None
    # En pesos: el FIX de Banxico para valores en dólares.
    fx_rate: Decimal | None = None
    market_value_mxn: Decimal | None = None

    @classmethod
    def build(
        cls,
        holding: SecurityHolding,
        *,
        account_uuid: str,
        account_name: str,
        instrument: Instrument,
        valuation: dict | None = None,
    ) -> "HoldingDTO":
        return cls(
            uuid=str(holding.uuid),
            account_uuid=account_uuid,
            account_name=account_name,
            instrument=instrument,
            quantity=holding.quantity,
            avg_cost=holding.avg_cost,
            cost_basis=holding.cost_basis,
            realized_pnl=holding.realized_pnl,
            dividends=holding.dividends,
            status=holding.status,
            opened_at=holding.opened_at,
            closed_at=holding.closed_at,
            **(valuation or {}),
        )


@dataclass(frozen=True, slots=True)
class TradeResultDTO:
    """Lo que devuelve registrar, editar o borrar una operación."""

    trade: TradeDTO | None
    holding: HoldingDTO | None
    account_available_balance: Decimal

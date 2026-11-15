from dataclasses import asdict
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel

from application.securities.dto import HoldingDTO, TradeDTO, TradeResultDTO
from application.securities.queries.portfolio import PortfolioDay, PortfolioSummary
from domain.entities.securities.holding_snapshot import HoldingSnapshot
from domain.entities.securities.instrument import Instrument
from domain.entities.securities.instrument_price import InstrumentPrice
from domain.objects.enums import HoldingStatus, InstrumentType, Market, TradeType


class InstrumentResponse(BaseModel):
    uuid: str
    market: Market
    symbol: str
    name: str
    instrument_type: InstrumentType
    currency: str
    exchange: str | None
    isin: str | None
    is_active: bool

    @classmethod
    def from_entity(cls, instrument: Instrument) -> "InstrumentResponse":
        return cls(
            uuid=str(instrument.uuid),
            market=instrument.market,
            symbol=instrument.symbol,
            name=instrument.name,
            instrument_type=instrument.instrument_type,
            currency=instrument.currency,
            exchange=instrument.exchange,
            isin=instrument.isin,
            is_active=instrument.is_active,
        )


class InstrumentPriceResponse(BaseModel):
    price_date: date
    close: Decimal
    is_trading_day: bool
    provider: str

    @classmethod
    def from_entity(cls, price: InstrumentPrice) -> "InstrumentPriceResponse":
        return cls(
            price_date=price.price_date,
            close=price.close,
            is_trading_day=price.is_trading_day,
            provider=price.provider,
        )


class InstrumentPricesResponse(BaseModel):
    instrument: InstrumentResponse
    prices: list[InstrumentPriceResponse]


class TradeResponse(BaseModel):
    uuid: str
    account_uuid: str
    instrument: InstrumentResponse
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
    def from_dto(cls, dto: TradeDTO) -> "TradeResponse":
        values = {f: getattr(dto, f) for f in cls.model_fields if f != "instrument"}
        return cls(instrument=InstrumentResponse.from_entity(dto.instrument), **values)


class HoldingResponse(BaseModel):
    uuid: str
    account_uuid: str
    account_name: str
    instrument: InstrumentResponse
    quantity: Decimal
    avg_cost: Decimal
    cost_basis: Decimal
    realized_pnl: Decimal
    dividends: Decimal
    status: HoldingStatus
    opened_at: date | None
    closed_at: date | None
    last_price: Decimal | None
    last_price_date: date | None
    market_value: Decimal | None
    unrealized_pnl: Decimal | None
    unrealized_pnl_pct: Decimal | None
    fx_rate: Decimal | None
    market_value_mxn: Decimal | None

    @classmethod
    def from_dto(cls, dto: HoldingDTO) -> "HoldingResponse":
        values = {f: getattr(dto, f) for f in cls.model_fields if f != "instrument"}
        return cls(instrument=InstrumentResponse.from_entity(dto.instrument), **values)


class HoldingDetailResponse(BaseModel):
    holding: HoldingResponse
    trades: list[TradeResponse]


class TradeResultResponse(BaseModel):
    """`trade` es null al borrar; `holding` es null si el valor ya no tiene operaciones en
    la cuenta. `holding` no trae valuación: para eso, `GET /securities/holdings/`."""

    trade: TradeResponse | None
    holding: HoldingResponse | None
    account_available_balance: Decimal

    @classmethod
    def from_dto(cls, dto: TradeResultDTO) -> "TradeResultResponse":
        return cls(
            trade=TradeResponse.from_dto(dto.trade) if dto.trade else None,
            holding=HoldingResponse.from_dto(dto.holding) if dto.holding else None,
            account_available_balance=dto.account_available_balance,
        )


class HoldingSnapshotResponse(BaseModel):
    """Una foto diaria. `close` es el último cierre conocido hasta ese día (`price_date`);
    sin cierres todavía, la valuación llega en null."""

    snapshot_date: date
    quantity: Decimal
    close: Decimal | None
    price_date: date | None
    market_value: Decimal | None
    fx_rate: Decimal | None
    market_value_mxn: Decimal | None
    cost_basis: Decimal
    unrealized_pnl: Decimal | None
    realized_pnl: Decimal
    dividends: Decimal

    @classmethod
    def from_entity(cls, snapshot: HoldingSnapshot) -> "HoldingSnapshotResponse":
        return cls(**{f: getattr(snapshot, f) for f in cls.model_fields})


class HoldingHistoryResponse(BaseModel):
    holding: HoldingResponse
    snapshots: list[HoldingSnapshotResponse]


class PortfolioSummaryResponse(BaseModel):
    """Patrimonio en pesos al día de hoy."""

    as_of: date
    cash: Decimal
    credit_cards: Decimal
    positions: Decimal
    securities: Decimal
    invested: Decimal
    net_worth: Decimal
    fx_rates: dict[str, Decimal]
    missing: list[str]

    @classmethod
    def from_summary(cls, summary: PortfolioSummary) -> "PortfolioSummaryResponse":
        return cls(**asdict(summary))


class PortfolioDayResponse(BaseModel):
    date: date
    positions: Decimal
    securities: Decimal
    total: Decimal
    complete: bool

    @classmethod
    def from_day(cls, day: PortfolioDay) -> "PortfolioDayResponse":
        return cls(
            date=day.day,
            positions=day.positions,
            securities=day.securities,
            total=day.total,
            complete=day.complete,
        )


class PortfolioHistoryResponse(BaseModel):
    start: date
    end: date
    days: list[PortfolioDayResponse]

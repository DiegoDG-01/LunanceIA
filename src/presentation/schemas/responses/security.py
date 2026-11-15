from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from domain.entities.securities.instrument import Instrument
from domain.entities.securities.instrument_price import InstrumentPrice
from domain.objects.enums import InstrumentType, Market


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

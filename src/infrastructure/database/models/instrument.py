"""Catálogo de valores y sus precios. Tablas globales: no pertenecen a un usuario."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    DECIMAL,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from domain.objects.enums import InstrumentType, Market, ProviderSymbolStatus
from infrastructure.database.connection import Base


class InstrumentModel(Base):
    __tablename__ = "instruments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    uuid: Mapped[str] = mapped_column(
        CHAR(36), unique=True, index=True, default=lambda: str(uuid.uuid4())
    )
    market: Mapped[Market] = mapped_column(Enum(Market))
    symbol: Mapped[str] = mapped_column(String(30))
    name: Mapped[str] = mapped_column(String(255))
    instrument_type: Mapped[InstrumentType] = mapped_column(Enum(InstrumentType))
    currency: Mapped[str] = mapped_column(CHAR(3))
    isin: Mapped[str | None] = mapped_column(String(12), nullable=True)
    exchange: Mapped[str | None] = mapped_column(String(60), nullable=True)
    preferred_provider: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    tracked_since: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("market", "symbol", name="uq_instrument_market_symbol"),
        Index("idx_instrument_name", "name"),
        Index("idx_instrument_tracked_since", "tracked_since"),
    )


class InstrumentProviderSymbolModel(Base):
    __tablename__ = "instrument_provider_symbols"

    instrument_id: Mapped[int] = mapped_column(
        ForeignKey("instruments.id", ondelete="CASCADE"), primary_key=True
    )
    provider: Mapped[str] = mapped_column(String(20), primary_key=True)
    provider_symbol: Mapped[str] = mapped_column(String(40))
    status: Mapped[ProviderSymbolStatus] = mapped_column(Enum(ProviderSymbolStatus))
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class InstrumentPriceModel(Base):
    __tablename__ = "instrument_prices"

    instrument_id: Mapped[int] = mapped_column(
        ForeignKey("instruments.id", ondelete="CASCADE"), primary_key=True
    )
    price_date: Mapped[date] = mapped_column(Date, primary_key=True)
    close: Mapped[Decimal] = mapped_column(DECIMAL(20, 6))
    traded_value: Mapped[Decimal | None] = mapped_column(DECIMAL(20, 2), nullable=True)
    is_trading_day: Mapped[bool] = mapped_column(Boolean, default=True)
    provider: Mapped[str] = mapped_column(String(20))
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ExchangeRateModel(Base):
    __tablename__ = "fx_rates"

    base: Mapped[str] = mapped_column(CHAR(3), primary_key=True)
    quote: Mapped[str] = mapped_column(CHAR(3), primary_key=True)
    rate_date: Mapped[date] = mapped_column(Date, primary_key=True)
    rate: Mapped[Decimal] = mapped_column(DECIMAL(18, 8))
    provider: Mapped[str] = mapped_column(String(20))
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

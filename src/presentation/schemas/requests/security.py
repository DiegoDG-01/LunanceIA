from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

from domain.objects.enums import TradeType


class TradeFieldsRequest(BaseModel):
    """Datos de una operación. Qué campos usa cada tipo:

    - BUY / SELL: `quantity`, `price`, `fees`; en una venta, también `tax_withheld`.
    - DIVIDEND: `gross_amount` y `tax_withheld`.
    - SPLIT: `split_from` y `split_to` (2 → 1 es un split inverso).
    """

    trade_date: date = Field(..., description="Fecha de la operación (no futura)")
    quantity: Decimal | None = Field(
        None, gt=Decimal(0), description="Títulos (hasta 8 decimales)"
    )
    price: Decimal | None = Field(
        None, gt=Decimal(0), description="Precio por título en la moneda del valor"
    )
    fees: Decimal | None = Field(
        None, ge=Decimal(0), description="Comisión con IVA (entra al costo en compras)"
    )
    tax_withheld: Decimal | None = Field(
        None, ge=Decimal(0), description="Retención de ISR (ventas y dividendos)"
    )
    gross_amount: Decimal | None = Field(
        None, gt=Decimal(0), description="Dividendo bruto (solo DIVIDEND)"
    )
    split_from: int | None = Field(None, ge=1, le=1_000_000)
    split_to: int | None = Field(None, ge=1, le=1_000_000)
    notes: str | None = Field(None, max_length=500)


class CreateTradeRequest(TradeFieldsRequest):
    account_uuid: str = Field(..., description="Cuenta donde está el valor")
    instrument_uuid: str = Field(
        ..., description="Valor del catálogo (`GET /securities/search`)"
    )
    trade_type: TradeType


class UpdateTradeRequest(TradeFieldsRequest):
    """Reemplaza todos los datos de la operación. El tipo, la cuenta y el valor no cambian:
    para eso, bórrala y registra otra."""

"""Una operación sobre un valor dentro de una cuenta.

Qué usa cada tipo:
- BUY / SELL: `quantity` títulos a `price` cada uno, más `fees` (comisión con IVA). En una
  venta, `tax_withheld` es la retención de ISR que hizo la casa de bolsa.
- DIVIDEND: `gross_amount` es el dividendo bruto; `tax_withheld`, la retención.
- SPLIT: `split_from` títulos se vuelven `split_to` (2 → 1 es un split inverso).

`cash_amount` es el dinero que entra o sale del disponible: lo que pagas en una compra,
lo que recibes en una venta o dividendo, y 0 en un split.
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal

from domain.objects.enums import TradeType
from shared.exceptions.domain import InvalidSecurityTradeError

CENT = Decimal("0.01")
ZERO = Decimal(0)


def money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def _decimals(value: Decimal) -> int:
    exponent = value.normalize().as_tuple().exponent
    return -exponent if isinstance(exponent, int) and exponent < 0 else 0


@dataclass
class SecurityTrade:
    id: int | None
    uuid: str | None
    user_id: int
    account_id: int
    instrument_id: int
    trade_type: TradeType
    trade_date: date
    quantity: Decimal = ZERO
    price: Decimal = ZERO
    fees: Decimal = ZERO
    tax_withheld: Decimal = ZERO
    gross_amount: Decimal | None = None
    cash_amount: Decimal = ZERO
    split_from: int | None = None
    split_to: int | None = None
    transaction_id: int | None = None
    notes: str | None = None
    created_at: datetime | None = None

    @classmethod
    def create(
        cls,
        *,
        user_id: int,
        account_id: int,
        instrument_id: int,
        trade_type: TradeType,
        trade_date: date,
        quantity: Decimal | None = None,
        price: Decimal | None = None,
        fees: Decimal | None = None,
        tax_withheld: Decimal | None = None,
        gross_amount: Decimal | None = None,
        split_from: int | None = None,
        split_to: int | None = None,
        notes: str | None = None,
    ) -> "SecurityTrade":
        trade = cls(
            id=None,
            uuid=None,
            user_id=user_id,
            account_id=account_id,
            instrument_id=instrument_id,
            trade_type=trade_type,
            trade_date=trade_date,
        )
        trade.change(
            trade_date=trade_date,
            quantity=quantity,
            price=price,
            fees=fees,
            tax_withheld=tax_withheld,
            gross_amount=gross_amount,
            split_from=split_from,
            split_to=split_to,
            notes=notes,
        )
        return trade

    def change(
        self,
        *,
        trade_date: date,
        quantity: Decimal | None = None,
        price: Decimal | None = None,
        fees: Decimal | None = None,
        tax_withheld: Decimal | None = None,
        gross_amount: Decimal | None = None,
        split_from: int | None = None,
        split_to: int | None = None,
        notes: str | None = None,
    ) -> None:
        """Reemplaza los datos de la operación (el tipo, la cuenta y el valor no cambian)."""
        fees = fees if fees is not None else ZERO
        tax = tax_withheld if tax_withheld is not None else ZERO
        if fees < 0 or tax < 0:
            raise InvalidSecurityTradeError(
                "comisión y retención no pueden ser negativas"
            )
        if _decimals(fees) > 2 or _decimals(tax) > 2:
            raise InvalidSecurityTradeError("comisión y retención van en centavos")

        if self.trade_type in (TradeType.BUY, TradeType.SELL):
            if quantity is None or quantity <= 0:
                raise InvalidSecurityTradeError("la cantidad debe ser mayor a cero")
            if price is None or price <= 0:
                raise InvalidSecurityTradeError("el precio debe ser mayor a cero")
            if _decimals(quantity) > 8:
                raise InvalidSecurityTradeError("la cantidad admite hasta 8 decimales")
            if _decimals(price) > 6:
                raise InvalidSecurityTradeError("el precio admite hasta 6 decimales")
            if gross_amount is not None or split_from or split_to:
                raise InvalidSecurityTradeError(
                    "una compra o venta no lleva monto bruto ni split"
                )
            if self.trade_type is TradeType.BUY and tax:
                raise InvalidSecurityTradeError("una compra no lleva retención")
            gross = quantity * price
            cash = (
                money(gross + fees)
                if self.trade_type is TradeType.BUY
                else money(gross - fees - tax)
            )
            if cash <= 0:
                raise InvalidSecurityTradeError(
                    "la comisión y la retención superan el monto de la venta"
                )
            self.quantity, self.price, self.gross_amount = quantity, price, None
            self.split_from = self.split_to = None
        elif self.trade_type is TradeType.DIVIDEND:
            if gross_amount is None or gross_amount <= 0:
                raise InvalidSecurityTradeError(
                    "el dividendo bruto debe ser mayor a cero"
                )
            if _decimals(gross_amount) > 2:
                raise InvalidSecurityTradeError("el dividendo va en centavos")
            if quantity or price or fees or split_from or split_to:
                raise InvalidSecurityTradeError(
                    "un dividendo solo lleva monto bruto y retención"
                )
            if tax >= gross_amount:
                raise InvalidSecurityTradeError("la retención supera el dividendo")
            cash = gross_amount - tax
            self.quantity, self.price, self.gross_amount = ZERO, ZERO, gross_amount
            self.split_from = self.split_to = None
        else:
            if not split_from or not split_to or split_from <= 0 or split_to <= 0:
                raise InvalidSecurityTradeError(
                    "el split necesita títulos antes y después"
                )
            if split_from == split_to:
                raise InvalidSecurityTradeError("el split no cambia la cantidad")
            if quantity or price or fees or tax or gross_amount:
                raise InvalidSecurityTradeError("un split no mueve dinero")
            cash = ZERO
            self.quantity, self.price, self.gross_amount = ZERO, ZERO, None
            self.split_from, self.split_to = split_from, split_to

        self.trade_date = trade_date
        self.fees = fees
        self.tax_withheld = tax
        self.cash_amount = cash
        self.notes = notes.strip()[:500] if notes and notes.strip() else None

    @property
    def moves_money(self) -> bool:
        return self.trade_type is not TradeType.SPLIT

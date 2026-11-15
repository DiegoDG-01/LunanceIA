from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from domain.objects.enums import AccountType, TransactionType


class TransactionResponse(BaseModel):
    uuid: str
    transfer_uuid: str | None
    category: str | None
    transaction_type: TransactionType
    amount: Decimal
    currency: str = Field(..., description="Moneda de la cuenta: MXN, USD o EUR")
    transaction_date: date
    description: str | None
    notes: str | None
    creation_date: datetime
    account_name: str
    account_type: AccountType
    account_uuid: str
    security_trade_uuid: str | None = Field(
        None,
        description=(
            "Operación de acciones que creó este movimiento. Si no es null, el movimiento "
            "no se edita ni se borra aquí: se cambia desde /securities/trades/"
        ),
    )
    security_holding_uuid: str | None = Field(
        None, description="Tenencia de esa operación (GET /securities/holdings/{uuid})"
    )

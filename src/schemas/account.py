from typing import Optional
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field

from utils.enums import AccountType


class BaseAccount(BaseModel):
    name: str
    type: AccountType
    bank: Optional[str] = None
    current_balance: Decimal = Field(default=Decimal("0.00"), decimal_places=2)
    currency: str = "MXN"
    is_active: bool = True


class CreateAccount(BaseAccount):
    pass


class UpdateAccount(BaseModel):
    nombre: Optional[str] = None
    tipo: Optional[AccountType] = None
    banco: Optional[str] = None
    saldo_actual: Optional[Decimal] = None
    moneda: Optional[str] = None
    activa: Optional[bool] = None


class Account(BaseAccount):
    account_id: int
    user_id: int
    creation_date: datetime

    model_config = ConfigDict(from_attributes=True)


class CuentaWithBalance(Account):
    current_month_balance: Decimal = Field(default=Decimal("0.00"), decimal_places=2)
    total_month_income: Decimal = Field(default=Decimal("0.00"), decimal_places=2)
    total_month_expense: Decimal = Field(default=Decimal("0.00"), decimal_places=2)

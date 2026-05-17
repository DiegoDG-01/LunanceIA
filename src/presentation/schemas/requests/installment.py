from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import date
from typing import Optional

from domain.objects.enums import InstallmentType


class CreateInstallmentPurchaseRequest(BaseModel):
    account_uuid: str = Field(..., description="UUID de la cuenta")
    category_id: Optional[int] = Field(None, gt=0, description="ID de la categoría")
    description: str = Field(..., max_length=500, description="Descripción de la compra")
    total_amount: Decimal = Field(..., gt=Decimal("0"), description="Monto total")
    num_installments: int = Field(..., ge=2, le=48, description="Número de meses")
    installment_type: InstallmentType = Field(..., description="Con o sin interés")
    annual_interest_rate: Decimal = Field(Decimal("0"), ge=Decimal("0"), description="Tasa anual (0 si es MSI)")
    purchase_date: date = Field(..., description="Fecha de compra")
    notes: Optional[str] = Field(None, max_length=1000, description="Notas")


class UpdateInstallmentPurchaseRequest(BaseModel):
    description: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = Field(None, max_length=1000)
    category_id: Optional[int] = Field(None, gt=0)


class PayInstallmentChargeRequest(BaseModel):
    payment_date: date = Field(..., description="Fecha de pago")

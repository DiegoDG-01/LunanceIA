from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from domain.objects.enums import CategoryName, Frequency, TransactionType


# This class is generic to use in Subscription or Transaction
class ImageAnalysis(BaseModel):
    is_subscription: bool
    amount: Decimal
    description: str
    category: CategoryName = CategoryName.OTROS_GASTOS
    category_id: int | None = None
    transaction_date: date | None = None
    notes: str | None = None

    # If only is_subscription=False
    transaction_type: TransactionType | None = None

    # If only is_subscription=True
    frequency: Frequency | None = None
    billing_day: int | None = None
    name: str | None = None

from pydantic import BaseModel
from decimal import Decimal
from datetime import date
from typing import Optional
from domain.objects.enums import TransactionType, Frequency
from domain.objects.enums import CategoryName

# This class is generic to use in Subscription or Transaction
class ImageAnalysis(BaseModel):
    is_subscription: bool
    amount: Decimal
    description: str
    category: CategoryName = CategoryName.OTROS_GASTOS
    category_id: Optional[int] = None
    transaction_date: Optional[date] = None
    notes: Optional[str] = None

    # If only is_subscription=False
    transaction_type: Optional[TransactionType] = None

    # If only is_subscription=True
    frequency: Optional[Frequency] = None
    billing_day: Optional[int] = None
    name: Optional[str] = None
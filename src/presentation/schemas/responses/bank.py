from pydantic import BaseModel
from typing import Optional


class BankResponse(BaseModel):
    id: int
    name: str
    code: str
    country: str
    logo_url: Optional[str]
    color: Optional[str]
    is_active: bool


class BankListResponse(BaseModel):
    banks: list[BankResponse]
    total: int

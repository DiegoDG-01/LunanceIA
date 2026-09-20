from pydantic import BaseModel


class BankResponse(BaseModel):
    id: int
    name: str
    code: str
    country: str
    logo_url: str | None
    color: str | None
    is_active: bool


class BankListResponse(BaseModel):
    banks: list[BankResponse]
    total: int

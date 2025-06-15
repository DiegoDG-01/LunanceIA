from typing import Optional
from pydantic import BaseModel, ConfigDict


class BaseTag(BaseModel):
    name: str
    color: Optional[str] = None


class CreateTag(BaseTag):
    pass


class UpdateTag(BaseModel):
    nombre: Optional[str] = None
    color: Optional[str] = None


class Tag(BaseTag):
    tag_id: int
    user_id: int

    model_config = ConfigDict(from_attributes=True)


class TagWithStats(Tag):
    total_transactions: int = 0
    